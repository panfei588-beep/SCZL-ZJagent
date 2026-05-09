"""
文件解析服务 - 使用 MinerU 进行文档解析和 OCR 识别
支持: PDF, 图片(JPG/PNG), Word(DOCX), Excel(XLSX)
"""

import os
import json
import pandas as pd
from typing import Any


async def parse_file(file_path: str, ext: str) -> dict[str, Any]:
    ext = ext.lower()

    if ext in (".xlsx", ".xls"):
        return _parse_excel(file_path)
    elif ext in (".pdf", ".jpg", ".jpeg", ".png", ".docx", ".doc"):
        return await _parse_with_mineru(file_path)
    else:
        return {"total_records": 0, "records": []}


def _parse_excel(file_path: str) -> dict[str, Any]:
    df = pd.read_excel(file_path)
    records = df.to_dict("records")
    return {"total_records": len(records), "records": records}


async def _parse_with_mineru(file_path: str) -> dict[str, Any]:
    """使用 MinerU 解析 PDF/图片/Word 文件"""
    try:
        from mineru.api import MinerUAPI

        api = MinerUAPI()
        result = api.parse(file_path)

        content_list = result.get("content_list", [])
        markdown_text = result.get("markdown", "")

        records = _extract_quality_records_from_content(content_list, markdown_text)

        return {"total_records": len(records), "records": records}

    except ImportError:
        return await _parse_with_mineru_cli(file_path)


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
        return {
            "total_records": 0,
            "records": [],
            "raw_text": stderr.decode("utf-8", errors="ignore"),
        }

    md_files = [f for f in os.listdir(output_dir) if f.endswith(".md")]
    if md_files:
        md_path = os.path.join(output_dir, md_files[0])
        with open(md_path, "r", encoding="utf-8") as f:
            markdown_text = f.read()

        records = _extract_quality_records_from_markdown(markdown_text)
        return {"total_records": len(records), "records": records}

    json_files = [f for f in os.listdir(output_dir) if f.endswith(".json")]
    if json_files:
        json_path = os.path.join(output_dir, json_files[0])
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = _extract_quality_records_from_json(data)
        return {"total_records": len(records), "records": records}

    return {"total_records": 0, "records": []}


def _extract_quality_records_from_content(
    content_list: list, markdown_text: str
) -> list[dict]:
    """从 MinerU 解析结果中提取质量检测记录"""
    records = []

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

    if not records:
        records = _extract_quality_records_from_markdown(markdown_text)

    return records


def _extract_quality_records_from_markdown(markdown_text: str) -> list[dict]:
    """从 Markdown 文本中提取表格数据"""
    records = []
    lines = markdown_text.strip().split("\n")

    table_start = -1
    for i, line in enumerate(lines):
        if "|" in line and line.strip().startswith("|"):
            table_start = i
            break

    if table_start < 0:
        return records

    headers = [
        h.strip() for h in lines[table_start].split("|") if h.strip() and h.strip() != "---"
    ]

    for line in lines[table_start + 2 :]:
        if not line.strip().startswith("|"):
            break
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) >= len(headers):
            record = {}
            for j, header in enumerate(headers):
                record[_normalize_header(header)] = cells[j]
            records.append(record)

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
