from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os

from api.upload import router as upload_router
from api.diagnosis import router as diagnosis_router
from api.solution import router as solution_router
from api.report import router as report_router
from core.config import get_settings

# 配置日志：同时输出到 stderr 和文件
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "app.log"), encoding="utf-8"),
    ],
)

settings = get_settings()

app = FastAPI(
    title="航天运载火箭质量异常诊断系统",
    description="基于AI的质量波动根因分析与改进方案生成",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/api/upload", tags=["文件上传"])
app.include_router(diagnosis_router, prefix="/api/diagnosis", tags=["AI诊断"])
app.include_router(solution_router, prefix="/api/solution", tags=["改进方案"])
app.include_router(report_router, prefix="/api/report", tags=["报告生成"])

# 静态文件服务（图表图片）
charts_dir = os.path.join(os.path.dirname(__file__), "charts")
os.makedirs(charts_dir, exist_ok=True)
app.mount("/api/static/charts", StaticFiles(directory=charts_dir), name="charts")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "quality-diagnosis"}
