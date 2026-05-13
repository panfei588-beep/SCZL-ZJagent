from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from agents.orchestrator import QualityDiagnosisOrchestrator

router = APIRouter()
orchestrator = QualityDiagnosisOrchestrator()


class DiagnosisRequest(BaseModel):
    file_paths: list[str]
    file_path: Optional[str] = None  # backward compat
    equipment: str = "3号精密磨床"
    days: int = 7
    operator: Optional[str] = None
    material: Optional[str] = None
    environment: Optional[dict] = None


@router.post("/analyze")
async def analyze(request: DiagnosisRequest):
    try:
        paths = request.file_paths or ([request.file_path] if request.file_path else [])
        if not paths:
            raise HTTPException(status_code=400, detail="未提供文件路径")

        result = await orchestrator.diagnose(
            file_paths=paths,
            equipment=request.equipment,
            days=request.days,
            operator=request.operator,
            material=request.material,
            environment=request.environment,
        )
        return {"code": 200, "message": "诊断完成", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"诊断失败: {str(e)}")
