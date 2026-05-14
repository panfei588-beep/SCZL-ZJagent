from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from agents.orchestrator import run_analysis

router = APIRouter()


class RootCause(BaseModel):
    rank: int
    cause: str
    category: str
    confidence: float
    evidence: List[str]
    impact: str


class SolutionRequest(BaseModel):
    root_causes: List[RootCause]
    equipment: Optional[str] = None


@router.post("/generate")
async def generate_solution(request: SolutionRequest):
    """向后兼容：通过新工作流生成改进方案"""
    try:
        # 使用空文件路径触发 decision_agent（仅方案生成）
        result = await run_analysis(
            file_path="",
            user_params={
                "root_causes": [rc.model_dump() for rc in request.root_causes],
                "equipment": request.equipment or "未指定",
            },
        )
        return {
            "code": 200,
            "message": "方案生成成功",
            "data": {"solutions": result.get("improvement_plan", [])},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"方案生成失败: {str(e)}")
