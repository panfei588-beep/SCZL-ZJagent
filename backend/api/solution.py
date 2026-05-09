from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from agents.orchestrator import QualityDiagnosisOrchestrator

router = APIRouter()
orchestrator = QualityDiagnosisOrchestrator()


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
    try:
        solutions = await orchestrator.generate_solutions(
            root_causes=[rc.model_dump() for rc in request.root_causes],
            equipment=request.equipment,
        )
        return {"code": 200, "message": "方案生成成功", "data": {"solutions": solutions}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"方案生成失败: {str(e)}")
