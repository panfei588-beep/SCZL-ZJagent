"""
文件解析服务 - 使用 MinerU 进行文档解析和 OCR 识别
支持: PDF, 图片(JPG/PNG), Word(DOCX), Excel(XLSX/XLS)
"""

import os
import json
import logging
import pandas as pd
from typing import Any


# 质量检测数据必需列（至少包含一个）
REQUIRED_RESULT_COLUMNS = {"判定", "结果", "result"}
# 推荐列（缺失时给警告）
RECOMMENDED_DATE_COLUMNS = {"日期", "时间", "record_date"}


def validate_quality_data(records: list[dict]) -> dict:
    """验证解析后的数据是否包含质量诊断所需的基本列。

    不要求必须有结果列，没有时给 warning 但仍接受。
    """
    if not records:
        return {
            "valid": False,
            "error": "文件中未找到质量检测数据，请确认文件格式正确",
            "warning": None,
            "columns_found": [],
        }

    all_columns: set[str] = set()
    for record in records:
        all_columns.update(record.keys())

    columns_found = sorted(all_columns)
    has_result_col = bool(all_columns & REQUIRED_RESULT_COLUMNS)

    warning = None
    if not has_result_col:
        warning = (
            f"未检测到判定/结果列，无法计算合格率。"
            f"检测到的列: {', '.join(columns_found)}。"
            f"将以原始测量数据模式进行分析。"
        )

    has_date_col = bool(all_columns & RECOMMENDED_DATE_COLUMNS)
    if has_date_col and not warning:
        pass
    elif not has_date_col and not warning:
        warning = (
            f"未检测到日期/时间列，时间趋势分析可能不可用。"
            f"检测到的列: {', '.join(columns_found)}"
        )
    elif not has_date_col and warning:
        warning += f"\n同时缺少日期列。"

    return {
        "valid": True,
        "error": None,
        "warning": warning,
        "columns_found": columns_found,
        "has_result_column": has_result_col,
    }


async def parse_file(file_path: str, ext: str) -> dict[str, Any]:
    ext = ext.lower()

    if ext in (".xlsx", ".xls"):
        return _parse_excel(file_path)
    elif ext in (".pdf", ".jpg", ".jpeg", ".png", ".docx", ".doc"):
        return await _parse_with_mineru(file_path)
    else:
        return {"total_records": 0, "records": []}


def _parse_excel(file_path: str) -> dict[str, Any]:
    import math
    import datetime

    # 尝试用 openpyxl 读取 xlsx，失败则用 xlrd 读取 xls
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
    except Exception:
        try:
            df = pd.read_excel(file_path, engine="xlrd")
        except Exception as e:
            logging.warning(f"Excel 读取失败: {e}")
            return {"total_records": 0, "records": []}

    # 保留原始中文列名，不做标准化（前端依赖中文列名显示）
    raw = df.to_dict("records")

    def _safe(v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        if isinstance(v, (datetime.datetime, datetime.date)):
            return v.isoformat()
        if isinstance(v, datetime.timedelta):
            return str(v)
        if hasattr(v, 'item'):  # numpy scalar
            return v.item()
        return v

    records = [{k: _safe(v) for k, v in row.items()} for row in raw]
    return {"total_records": len(records), "records": records}


async def _parse_with_mineru(file_path: str) -> dict[str, Any]:
    """使用 MinerU 解析 PDF/图片/Word 文件"""
    try:
        from mineru.api import MinerUAPI

        api = MinerUAPI()
        result = api.parse(file_path)

        # MinerU 可能返回 dict 或对象，统一处理
        if isinstance(result, dict):
            content_list = result.get("content_list", [])
            markdown_text = result.get("markdown", "") or result.get("md_content", "")
        else:
            # 对象类型，尝试属性访问
            content_list = getattr(result, "content_list", []) or []
            markdown_text = getattr(result, "markdown", "") or getattr(result, "md_content", "") or ""

        logging.info(f"MinerU 解析结果: content_list items={len(content_list)}, markdown len={len(markdown_text)}")

        # 如果 MinerU 未返回内容，记录所有 key 以便调试
        if not content_list and not markdown_text:
            if isinstance(result, dict):
                logging.warning(f"MinerU 返回空内容，可用 keys: {list(result.keys())}")

        records = _extract_quality_records_from_content(content_list, markdown_text)

        if not records:
            # fallback: 返回纯文本作为一条记录
            if markdown_text:
                records = [{"raw_text": markdown_text[:2000]}]
            elif content_list:
                raw_content = json.dumps(content_list[:5], ensure_ascii=False, default=str)
                records = [{"raw_content": raw_content[:2000]}]

        return {"total_records": len(records), "records": records}

    except ImportError:
        return await _parse_with_mineru_cli(file_path)
    except Exception as e:
        logging.error(f"MinerU 解析异常: {e}")
        # MinerU 完全失败时尝试用 PyPDF2 提取文本
        return await _fallback_text_extraction(file_path)


async def _fallback_text_extraction(file_path: str) -> dict[str, Any]:
    """当 MinerU 完全失败时，用基础库提取文本（PyPDF2/PyMuPDF/纯文本）。"""
    ext = os.path.splitext(file_path)[1].lower()

    # PDF: 优先用 PyMuPDF，再用 PyPDF2
    if ext == ".pdf":
        for lib_name in ("fitz", "PyPDF2"):
            try:
                if lib_name == "fitz":
                    import fitz
                    doc = fitz.open(file_path)
                    text = ""
                    for page in doc:
                        text += page.get_text() or ""
                    doc.close()
                    if text.strip():
                        return {"total_records": 1, "records": [{"raw_text": text.strip()[:2000]}]}
                elif lib_name == "PyPDF2":
                    from PyPDF2 import PdfReader
                    reader = PdfReader(file_path)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() or ""
                    if text.strip():
                        return {"total_records": 1, "records": [{"raw_text": text.strip()[:2000]}]}
            except (ImportError, Exception) as e:
                logging.debug(f"{lib_name} 提取失败: {e}")
                continue

    # DOCX: 尝试 python-docx
    if ext in (".docx", ".doc"):
        try:
            from docx import Document
            doc = Document(file_path)
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            if text.strip():
                return {"total_records": 1, "records": [{"raw_text": text.strip()[:2000]}]}
        except (ImportError, Exception) as e:
            logging.debug(f"python-docx 提取失败: {e}")

    # 图片: 用 PaddleOCR（中文识别精度远优于 pytesseract）
    if ext in (".jpg", ".jpeg", ".png"):
        try:
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
            result = ocr.ocr(file_path, cls=True)
            lines = []
            if result and result[0]:
                for line in result[0]:
                    if line and len(line) >= 2:
                        text_info = line[1]
                        if text_info and text_info[0]:
                            lines.append(text_info[0])
            text = "\n".join(lines)
            if text.strip():
                return {"total_records": 1, "records": [{"raw_text": text.strip()[:2000]}]}
        except (ImportError, Exception) as e:
            logging.debug(f"PaddleOCR 失败: {e}")

    # 最后兜底: 返回文件基本信息
    file_size = os.path.getsize(file_path)
    return {
        "total_records": 1,
        "records": [{"raw_text": f"文件 {os.path.basename(file_path)} ({ext}, {file_size} bytes)，无法提取结构化文本内容。请确认文件包含可读数据。"}],
    }


async def _parse_with_mineru_cli(file_path: str) -> dict[str, Any]:
    """通过 MinerU CLI 解析文件（备选方案）"""
    import asyncio

    output_dir = os.path.join(os.path.dirname(file_path), "mineru_output")
    os.makedirs(output_dir, exist_ok=True)

    cmd = f"mineru --input '{file_path}' --output '{output_dir}' --backend pipeline"
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        # CLI 执行失败 → 回退到基础文本提取
        error_text = stderr.decode("utf-8", errors="ignore")
        logging.warning(f"MinerU CLI 执行失败: {error_text[:200]}")
        return await _fallback_text_extraction(file_path)

    md_files = [f for f in os.listdir(output_dir) if f.endswith(".md")]
    if md_files:
        md_path = os.path.join(output_dir, md_files[0])
        with open(md_path, "r", encoding="utf-8") as f:
            markdown_text = f.read()

        records = _extract_quality_records_from_markdown(markdown_text)
        if not records:
            # 未提取到表格 → 返回原始文本
            records = [{"raw_text": markdown_text[:2000]}]
        return {"total_records": len(records), "records": records}

    json_files = [f for f in os.listdir(output_dir) if f.endswith(".json")]
    if json_files:
        json_path = os.path.join(output_dir, json_files[0])
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = _extract_quality_records_from_json(data)
        if not records:
            # JSON 中没有结构化记录 → 返回原始 JSON 文本
            records = [{"raw_content": json.dumps(data, ensure_ascii=False, default=str)[:2000]}]
        return {"total_records": len(records), "records": records}

    # MinerU 执行成功但无输出文件 → 返回原始文件内容
    with open(file_path, "rb") as f:
        raw_bytes = f.read(2000)
    return {
        "total_records": 1,
        "records": [{"raw_content": f"[非结构化文件，原始内容 {len(raw_bytes)} bytes]"}],
    }


def _extract_quality_records_from_content(
    content_list: list, markdown_text: str
) -> list[dict]:
    """从 MinerU 解析结果中提取质量检测记录"""
    records = []

    # 先尝试从表格提取
    tables = [item for item in content_list if item.get("type") == "table"]
    if tables:
        for table in tables:
            table_data = table.get("data", [])
            if table_data and len(table_data) > 1:
                headers = table_data[0]
                for row in table_data[1:]:
                    record = {}
                    for i, header in enumerate(headers):
                        if i < len(row):
                            record[_normalize_header(header)] = row[i]
                    if record:
                        records.append(record)

    # 表格未提取到则从 markdown 提取
    if not records:
        records = _extract_quality_records_from_markdown(markdown_text)

    return records


def _extract_quality_records_from_markdown(markdown_text: str) -> list[dict]:
    """从 Markdown 文本中提取表格数据"""
    records = []
    lines = markdown_text.strip().split("\n")

    # 查找 markdown 表格
    for i, line in enumerate(lines):
        if "|" in line and line.strip().startswith("|"):
            headers = [
                h.strip() for h in line.split("|")
                if h.strip() and not h.strip().startswith("---")
            ]
            if not headers:
                continue
            # 跳过分隔行
            j = i + 1
            if j < len(lines) and "---" in lines[j]:
                j += 1
            while j < len(lines):
                row_line = lines[j]
                if not row_line.strip().startswith("|"):
                    break
                cells = [c.strip() for c in row_line.split("|") if c.strip()]
                if len(cells) >= len(headers):
                    record = {}
                    for k, header in enumerate(headers):
                        record[_normalize_header(header)] = cells[k]
                    if record:
                        records.append(record)
                j += 1
            if records:
                break

    return records


def _extract_quality_records_from_json(data: Any) -> list[dict]:
    """从 JSON 结构中提取质量记录"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("records", "data", "items", "rows"):
            if key in data and isinstance(data[key], list):
                return data[key]
    return []


def _normalize_header(header: str) -> str:
    """标准化表头名称"""
    mapping = {
        "日期": "record_date",
        "时间": "record_date",
        "产品号": "product_no",
        "产品编号": "product_no",
        "零件号": "product_no",
        "检测项": "inspection_item",
        "检测项目": "inspection_item",
        "测量项": "inspection_item",
        "标准值": "standard_value",
        "标准": "standard_value",
        "规格": "standard_value",
        "实测值": "measured_value",
        "测量值": "measured_value",
        "实际值": "measured_value",
        "判定": "result",
        "结果": "result",
        "合格": "result",
        "设备": "equipment",
        "机床": "equipment",
        "操作员": "operator",
        "操作人": "operator",
    }
    header_clean = header.strip()
    return mapping.get(header_clean, header_clean)
