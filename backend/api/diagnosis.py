from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from agents.orchestrator import QualityDiagnosisOrchestrator

router = APIRouter()
orchestrator = QualityDiagnosisOrchestrator()


class DiagnosisRequest(BaseModel):
    file_path: str
    equipment: str = "3号精密磨床"
    days: int = 7
    operator: Optional[str] = None
    material: Optional[str] = None
    environment: Optional[dict] = None


@router.post("/analyze")
async def analyze(request: DiagnosisRequest):
    try:
        result = await orchestrator.diagnose(
            file_path=request.file_path,
            equipment=request.equipment,
            days=request.days,
            operator=request.operator,
            material=request.material,
            environment=request.environment,
        )
        return {"code": 200, "message": "诊断完成", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"诊断失败: {str(e)}")
