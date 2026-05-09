"""
质量诊断 Agent 编排器
使用 LangChain 编排三个 Agent：数据采集Agent、诊断专家Agent、决策支持Agent
"""

from typing import Optional
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatTongyi
from core.config import get_settings
from agents.tools import get_all_tools

settings = get_settings()


class QualityDiagnosisOrchestrator:
    def __init__(self):
        self.llm = ChatTongyi(
            model="qwen-max",
            dashscope_api_key=settings.dashscope_api_key,
            temperature=0.3,
        )
        self.tools = get_all_tools()
        self.agent = self._create_agent()

    def _create_agent(self) -> AgentExecutor:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是一位航天运载火箭质量管理专家，负责诊断质量异常问题。

你的工作流程：
1. 使用 analyze_quality_data 工具分析质量检测数据，识别异常趋势
2. 使用 search_similar_cases 工具在知识库中检索相似的历史案例
3. 进行"人机料法环测"6维根因分析：
   - 人（Man）：操作人员技能、经验、疲劳度
   - 机（Machine）：设备状态、磨损、校准
   - 料（Material）：原材料批次、供应商、规格
   - 法（Method）：工艺参数、操作规程
   - 环（Environment）：温度、湿度、振动
   - 测（Measurement）：测量设备精度、校准状态
4. 使用 llm_root_cause_analysis 工具进行深度推理
5. 输出结构化的诊断结果

要求：
- 每个根因必须有置信度评分(0-1)和具体证据
- 按置信度从高到低排序
- 给出明确的影响描述

请以JSON格式返回诊断结果，包含以下字段：
{{
    "quality_trend": {{
        "dates": [...],
        "rates": [...],
        "initial_rate": float,
        "current_rate": float,
        "decline": float
    }},
    "root_causes": [
        {{
            "rank": int,
            "cause": str,
            "category": str,  // 人/机/料/法/环/测
            "confidence": float,
            "evidence": [str, ...],
            "impact": str
        }}
    ],
    "similar_cases": [
        {{
            "case_id": str,
            "title": str,
            "similarity": float,
            "solution": str
        }}
    ]
}}""",
                ),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
        )

        agent = create_openai_tools_agent(
            llm=self.llm, tools=self.tools, prompt=prompt
        )

        return AgentExecutor(
            agent=agent, tools=self.tools, verbose=True, max_iterations=10
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
        context_parts = [
            f"数据文件：{file_path}",
            f"设备：{equipment}",
            f"时间范围：最近{days}天",
        ]
        if operator:
            context_parts.append(f"操作员：{operator}")
        if material:
            context_parts.append(f"物料：{material}")
        if environment:
            context_parts.append(f"环境参数：{environment}")

        input_text = (
            "请对以下质量数据进行完整的异常诊断分析：\n"
            + "\n".join(f"- {p}" for p in context_parts)
            + "\n\n请进行完整的6维根因分析并给出诊断结果。"
        )

        result = await self.agent.ainvoke({"input": input_text})
        return self._parse_result(result)

    async def generate_solutions(
        self, root_causes: list[dict], equipment: Optional[str] = None
    ) -> list[dict]:
        input_text = f"""基于以下根因分析结果，生成改进方案：

根因列表：
{root_causes}

设备：{equipment or '未指定'}

请为每个根因生成具体的改进方案，包含：
- priority: 优先级（P0-紧急/P1-重要/P2-一般）
- action: 具体措施
- responsible: 负责部门
- estimated_cost: 预估成本（元）
- expected_effect: 预期效果
- implementation_time: 实施时间
- roi: 投入产出比描述

请以JSON数组格式返回。"""

        result = await self.agent.ainvoke({"input": input_text})
        return self._parse_solutions(result)

    def _parse_result(self, result: dict) -> dict:
        output = result.get("output", "")
        try:
            import json

            if "```json" in output:
                json_str = output.split("```json")[1].split("```")[0]
            elif "{" in output:
                start = output.index("{")
                end = output.rindex("}") + 1
                json_str = output[start:end]
            else:
                json_str = output
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return {
                "quality_trend": {
                    "dates": [],
                    "rates": [],
                    "initial_rate": 0,
                    "current_rate": 0,
                    "decline": 0,
                },
                "root_causes": [],
                "similar_cases": [],
                "raw_output": output,
            }

    def _parse_solutions(self, result: dict) -> list[dict]:
        output = result.get("output", "")
        try:
            import json

            if "```json" in output:
                json_str = output.split("```json")[1].split("```")[0]
            elif "[" in output:
                start = output.index("[")
                end = output.rindex("]") + 1
                json_str = output[start:end]
            else:
                json_str = output
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return []
