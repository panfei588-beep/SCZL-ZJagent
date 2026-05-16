from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
import logging

from langchain_community.chat_models import ChatTongyi
from langchain.schema import HumanMessage, SystemMessage
from core.config import get_settings
from knowledge_base.milvus_client import search_improvement_cases

router = APIRouter()
settings = get_settings()

# 直接调用 LLM 生成方案，不通过完整工作流
llm = ChatTongyi(
    model="qwen-max",
    dashscope_api_key=settings.dashscope_api_key,
    temperature=0.3,
    max_tokens=4096,
)


class RootCause(BaseModel):
    model_config = {"extra": "allow"}
    rank: int = 0
    cause: str = ""
    root_cause: str = ""
    category: str = ""
    confidence: float = 0.5
    evidence: str | list = []
    impact: str = ""
    affected_fields: str | list = []


class SolutionRequest(BaseModel):
    root_causes: List[RootCause]
    equipment: Optional[str] = None


def _parse_llm_json(output: str) -> dict | list:
    """robust JSON 解析，支持 markdown code block、brace 匹配和截断修复"""
    import re

    def _try_fix_truncated_array(s: str) -> list:
        """尝试修复被截断的 JSON 数组：移除最后一个不完整的对象后补上 ]"""
        # 找到最后一个完整对象的结束位置
        depth = 0
        last_complete_end = -1
        in_string = False
        escape_next = False
        for i, ch in enumerate(s):
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    last_complete_end = i
        if last_complete_end == -1:
            raise ValueError("无法修复截断的 JSON")
        fixed = s[: last_complete_end + 1] + "]"
        return json.loads(fixed)

    try:
        json_str = None
        match = re.search(r"```json\s*\n([\s\S]*?)\n```", output)
        if match:
            json_str = match.group(1)
        elif "[" in output:
            start = output.index("[")
            end = output.rindex("]") + 1 if "]" in output[start:] else len(output)
            json_str = output[start:end]
        elif "{" in output:
            start = output.index("{")
            end = output.rindex("}") + 1 if "}" in output[start:] else len(output)
            json_str = output[start:end]

        if json_str is None:
            raise ValueError("未找到 JSON 格式输出")

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 输出被截断，尝试修复
            if json_str.lstrip().startswith("["):
                return _try_fix_truncated_array(json_str.lstrip())
            raise
    except Exception:
        raise ValueError(f"LLM 输出解析失败: {output[:200]}")


@router.post("/generate")
async def generate_solution(request: SolutionRequest):
    """直接生成改进方案（单次 LLM 调用，跳过完整工作流）"""
    try:
        root_causes = [rc.model_dump() for rc in request.root_causes]
        equipment = request.equipment or "未指定"

        # 根据根因构建检索 query
        cause_keywords = [c.get("cause", "") for c in root_causes if c.get("cause")]
        query = f"{equipment} 质量改善 {' '.join(cause_keywords)}"

        # RAG 检索改善知识库
        improvement_cases = search_improvement_cases(query, top_k=settings.rag_top_k)

        case_texts = []
        for c in improvement_cases:
            if "error" not in c:
                case_texts.append(
                    f"[{c['case_id']}] {c['title']} | 方案: {c.get('solution', '')} "
                    f"| 效果: {c.get('effect', '')} | 相似度: {c.get('similarity', 0)}"
                )

        case_lines = '\n'.join(case_texts) if case_texts else '无历史案例'

        system_prompt = """你是质量改进专家。请为每个根因生成具体的改进方案。

参考历史改善案例，确保方案有依据。

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

设备：{equipment}

参考历史案例：
{case_lines}"""

        response = llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
        )
        plan = _parse_llm_json(response.content)
        if not isinstance(plan, list):
            plan = []

        return {
            "code": 200,
            "message": "方案生成成功",
            "data": {"solutions": plan},
        }

    except Exception as e:
        logging.error(f"[solution/generate] 方案生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"方案生成失败: {str(e)}")
