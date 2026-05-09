import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from core.config import get_settings
from services.file_parser import parse_file

router = APIRouter()
settings = get_settings()


@router.post("/file")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择文件")

    ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = {".xlsx", ".xls", ".pdf", ".jpg", ".jpeg", ".png", ".docx", ".doc"}
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}，支持: {', '.join(allowed_exts)}",
        )

    os.makedirs(settings.upload_dir, exist_ok=True)
    file_id = str(uuid.uuid4())
    save_path = os.path.join(settings.upload_dir, f"{file_id}{ext}")

    content = await file.read()
    if len(content) > settings.max_upload_size:
        raise HTTPException(status_code=400, detail="文件大小超过限制(50MB)")

    with open(save_path, "wb") as f:
        f.write(content)

    parsed_result = await parse_file(save_path, ext)

    return {
        "code": 200,
        "message": "上传成功",
        "data": {
            "file_id": file_id,
            "filename": file.filename,
            "file_path": save_path,
            "total_records": parsed_result.get("total_records", 0),
            "records": parsed_result.get("records", []),
        },
    }
