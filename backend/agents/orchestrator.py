"""
质量诊断编排器
直接调用 LLM + 手动工具执行，绕过 create_openai_tools_agent 与 ChatTongyi 的兼容性问题
"""

from typing import Optional
import json
import re
import logging
from langchain_community.chat_models import ChatTongyi
from langchain.schema import HumanMessage, SystemMessage
from core.config import get_settings
from agents.tools import (
    analyze_quality_data,
    analyze_quality_trend,
    search_similar_cases,
)

settings = get_settings()


class QualityDiagnosisOrchestrator:
    def __init__(self):
        self.llm = ChatTongyi(
            model="qwen-max",
            dashscope_api_key=settings.dashscope_api_key,
            temperature=0.3,
        )

    async def diagnose(
        self,
        file_path: str,
        equipment: str,
        days: int,
        operator: Optional[str] = None,
        material: Optional[str] = None,
        environment: Optional[dict] = None,
    ) -> dict:
        try:
            # Step 1: 分析质量数据
            data_summary = analyze_quality_data.invoke(file_path)
            trend_summary = analyze_quality_trend.invoke(file_path)

            # Step 2: 检索相似案例
            query = f"{equipment} 质量异常 合格率下降"
            similar_cases_raw = search_similar_cases.invoke(query)

            # Step 3: 构建上下文
            context_parts = [
                f"设备：{equipment}",
                f"时间范围：最近{days}天",
                f"数据统计：{data_summary}",
                f"质量趋势：{trend_summary}",
                f"相似案例：{similar_cases_raw}",
            ]
            if operator:
                context_parts.append(f"操作员：{operator}")
            if material:
                context_parts.append(f"物料：{material}")
            if environment:
                context_parts.append(f"环境参数：{environment}")

            # Step 4: LLM 深度分析
            system_prompt = """你是一位航天运载火箭质量管理专家，负责诊断质量异常问题。

请基于提供的数据进行"人机料法环测"6维根因分析：
- 人（Man）：操作人员技能、经验、疲劳度
- 机（Machine）：设备状态、磨损、校准
- 料（Material）：原材料批次、供应商、规格
- 法（Method）：工艺参数、操作规程
- 环（Environment）：温度、湿度、振动
- 测（Measurement）：测量设备精度、校准状态

要求：
- 每个根因必须有置信度评分(0-1)和具体证据
- 按置信度从高到低排序

请严格以JSON格式返回，不要有其他文字：
{
    "quality_trend": {
        "dates": [...],
        "rates": [...],
        "initial_rate": float,
        "current_rate": float,
        "decline": float
    },
    "root_causes": [
        {
            "rank": int,
            "cause": str,
            "category": str,
            "confidence": float,
            "evidence": [str],
            "impact": str
        }
    ],
    "similar_cases": [
        {
            "case_id": str,
            "title": str,
            "similarity": float,
            "solution": str
        }
    ]
}"""

            human_prompt = "请对以下质量数据进行完整的异常诊断分析：\n" + "\n".join(
                f"- {p}" for p in context_parts
            )

            response = await self.llm.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
            )
            return self._parse_result(response.content)

        except Exception as e:
            logging.error(f"Diagnose failed: {e}", exc_info=True)
            return {
                "quality_trend": {
                    "dates": [], "rates": [],
                    "initial_rate": 0, "current_rate": 0, "decline": 0,
                },
                "root_causes": [],
                "similar_cases": [],
                "error": str(e),
            }

    async def generate_solutions(
        self, root_causes: list[dict], equipment: Optional[str] = None
    ) -> list[dict]:
        try:
            system_prompt = """你是质量改进专家。请为每个根因生成具体的改进方案。
严格以JSON数组格式返回，不要有其他文字：
[
  {
    "priority": "P0-紧急|P1-重要|P2-一般",
    "action": str,
    "responsible": str,
    "estimated_cost": int,
    "expected_effect": str,
    "implementation_time": str,
    "roi": str
  }
]"""

            human_prompt = f"""基于以下根因分析结果，生成改进方案：

根因列表：
{json.dumps(root_causes, ensure_ascii=False, indent=2)}

设备：{equipment or '未指定'}"""

            response = await self.llm.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
            )
            return self._parse_solutions(response.content)

        except Exception as e:
            logging.error(f"Generate solutions failed: {e}", exc_info=True)
            return []

    def _parse_result(self, output: str) -> dict:
        try:
            json_str = None
            match = re.search(r"```json\s*\n([\s\S]*?)\n```", output)
            if match:
                json_str = match.group(1)
            elif "{" in output:
                start = output.index("{")
                end = output.rindex("}") + 1
                json_str = output[start:end]

            if json_str is None:
                raise ValueError("未找到 JSON 格式输出")

            data = json.loads(json_str)
            self._validate_result(data)
            return data
        except Exception:
            return {
                "quality_trend": {
                    "dates": [], "rates": [],
                    "initial_rate": 0, "current_rate": 0, "decline": 0,
                },
                "root_causes": [],
                "similar_cases": [],
                "raw_output": output,
            }

    def _validate_result(self, data: dict) -> None:
        for key in ["quality_trend", "root_causes"]:
            if key not in data:
                data[key] = [] if key == "root_causes" else {}
        if "similar_cases" not in data:
            data["similar_cases"] = []

    def _parse_solutions(self, output: str) -> list[dict]:
        try:
            json_str = None
            match = re.search(r"```json\s*\n([\s\S]*?)\n```", output)
            if match:
                json_str = match.group(1)
            elif "[" in output:
                start = output.index("[")
                end = output.rindex("]") + 1
                json_str = output[start:end]

            if json_str is None:
                raise ValueError("未找到 JSON 格式输出")

            data = json.loads(json_str)
            return data if isinstance(data, list) else []
        except Exception:
            return []
