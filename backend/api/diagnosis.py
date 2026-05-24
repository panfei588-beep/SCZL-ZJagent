from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Any
from agents.orchestrator import run_analysis

router = APIRouter()


class QualityAnalyzeRequest(BaseModel):
    file_paths: Optional[list[str]] = None
    file_path: Optional[str] = None  # backward compat
    equipment: str = "3号精密磨床"
    days: int = 7
    operator: Optional[str] = None
    material: Optional[str] = None
    environment: Optional[dict] = None
    # 新增参数
    focus_metrics: Optional[list[str]] = None
    analysis_goal: Optional[str] = None
    depth: Optional[Any] = None
    time_range: Optional[str] = None


@router.post("/analyze")
async def analyze(request: Request):
    """执行完整质量分析工作流（数据统计 → 诊断 → 方案）"""
    try:
        # 兼容无 body 的请求（前端 fetch 空 POST）
        body = await request.body()
        if body:
            payload = await request.json()
            req = QualityAnalyzeRequest(**payload)
        else:
            req = QualityAnalyzeRequest()
        paths = req.file_paths or ([req.file_path] if req.file_path else [])
        if not paths:
            return {"code": 200, "message": "无文件路径，返回空结果", "data": {
                "statistics": {},
                "charts": [],
                "diagnosis_result": [],
                "diagnosis_confidence": 0,
                "improvement_plan": [],
                "estimated_improvement": "",
                "low_confidence_warning": False,
            }}

        user_params = {
            "equipment": req.equipment,
            "days": req.days,
            "operator": req.operator,
            "material": req.material,
            "environment": req.environment,
            "focus_metrics": req.focus_metrics,
            "analysis_goal": req.analysis_goal,
            "depth": str(req.depth) if req.depth is not None else None,
            "time_range": req.time_range,
        }

        # 对每个文件执行分析，合并结果
        all_statistics = {}
        all_charts = []
        all_diagnosis = []
        all_improvement = []
        low_confidence = False
        last_result = {}

        for fp in paths:
            result = await run_analysis(file_path=fp, user_params=user_params)
            last_result = result
            if result.get("statistics"):
                all_statistics[fp] = result["statistics"]
            if result.get("charts"):
                all_charts.extend(result["charts"])
            if result.get("diagnosis_result"):
                all_diagnosis.extend(result["diagnosis_result"])
            if result.get("improvement_plan"):
                all_improvement.extend(result["improvement_plan"])
            if result.get("low_confidence_warning"):
                low_confidence = True

        # 单文件直接返回结果（修复：之前调用了两次 run_analysis）
        if len(paths) == 1:
            return {"code": 200, "message": "诊断完成", "data": last_result}

        # 多文件合并结果
        avg_confidence = 0
        if all_diagnosis:
            avg_confidence = sum(
                c.get("confidence", 0.5) for c in all_diagnosis
            ) / len(all_diagnosis)

        merged = {
            "statistics": all_statistics,
            "charts": all_charts,
            "diagnosis_result": all_diagnosis,
            "diagnosis_confidence": round(avg_confidence, 3),
            "improvement_plan": all_improvement,
            "estimated_improvement": "预计整体合格率可提升 2-5 个百分点",
            "low_confidence_warning": low_confidence,
        }

        return {"code": 200, "message": "诊断完成", "data": merged}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"诊断失败: {str(e)}")
