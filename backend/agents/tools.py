"""
Agent Tools - 质量诊断相关工具集
"""

import json
import pandas as pd
from langchain.tools import tool
from typing import Optional


def get_all_tools():
    return [
        analyze_quality_data,
        search_similar_cases,
        analyze_quality_trend,
        llm_root_cause_analysis,
        generate_improvement_plan,
        calculate_roi,
    ]


@tool
def analyze_quality_data(file_path: str) -> str:
    """解析并分析质量检测数据文件，返回数据统计摘要。
    输入：文件路径（Excel格式）
    输出：数据统计信息，包括总记录数、合格率、不合格项分布等
    """
    try:
        df = pd.read_excel(file_path)
    except Exception:
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            return json.dumps({"error": f"无法读取文件: {str(e)}"}, ensure_ascii=False)

    result_col = None
    for col in df.columns:
        if col in ("判定", "结果", "result"):
            result_col = col
            break

    stats = {
        "total_records": len(df),
        "columns": list(df.columns),
        "date_range": None,
        "pass_rate": None,
        "fail_count": 0,
        "fail_items": [],
    }

    date_col = None
    for col in df.columns:
        if col in ("日期", "时间", "record_date", "date"):
            date_col = col
            break

    if date_col and date_col in df.columns:
        stats["date_range"] = {
            "start": str(df[date_col].min()),
            "end": str(df[date_col].max()),
        }

    if result_col:
        total = len(df)
        pass_count = len(df[df[result_col].isin(["合格", "pass", "PASS", "OK"])])
        stats["pass_rate"] = round(pass_count / total * 100, 2) if total > 0 else 0
        stats["fail_count"] = total - pass_count

        fail_df = df[~df[result_col].isin(["合格", "pass", "PASS", "OK"])]
        item_col = None
        for col in df.columns:
            if col in ("检测项", "检测项目", "inspection_item"):
                item_col = col
                break
        if item_col and item_col in fail_df.columns:
            stats["fail_items"] = (
                fail_df[item_col].value_counts().head(5).to_dict()
            )

    return json.dumps(stats, ensure_ascii=False, default=str)


@tool
def search_similar_cases(query: str) -> str:
    """在Milvus知识库中检索与当前质量问题相似的历史案例。
    输入：质量问题描述文本
    输出：相似案例列表（包含案例标题、根因、解决方案）
    """
    from knowledge_base.milvus_client import search_cases

    try:
        cases = search_cases(query, top_k=3)
        return json.dumps(cases, ensure_ascii=False)
    except Exception as e:
        return json.dumps(
            {
                "error": f"知识库检索失败: {str(e)}",
                "fallback_cases": _get_fallback_cases(query),
            },
            ensure_ascii=False,
        )


@tool
def analyze_quality_trend(file_path: str, date_column: str = "日期", result_column: str = "判定") -> str:
    """分析质量数据的时间趋势，计算每日合格率变化。
    输入：文件路径、日期列名、结果列名
    输出：每日合格率趋势数据
    """
    try:
        df = pd.read_excel(file_path)
    except Exception:
        df = pd.read_csv(file_path)

    if date_column not in df.columns:
        for col in df.columns:
            if col in ("日期", "时间", "record_date", "date"):
                date_column = col
                break

    if result_column not in df.columns:
        for col in df.columns:
            if col in ("判定", "结果", "result"):
                result_column = col
                break

    if date_column not in df.columns or result_column not in df.columns:
        return json.dumps({"error": "未找到日期列或结果列"}, ensure_ascii=False)

    df[date_column] = pd.to_datetime(df[date_column])
    daily = df.groupby(df[date_column].dt.date)[result_column].apply(
        lambda x: round(
            x.isin(["合格", "pass", "PASS", "OK"]).sum() / len(x) * 100, 2
        )
    )

    trend = {
        "dates": [str(d) for d in daily.index],
        "rates": list(daily.values),
        "initial_rate": float(daily.iloc[0]) if len(daily) > 0 else 0,
        "current_rate": float(daily.iloc[-1]) if len(daily) > 0 else 0,
        "decline": round(
            float(daily.iloc[0]) - float(daily.iloc[-1]), 2
        )
        if len(daily) > 1
        else 0,
    }

    return json.dumps(trend, ensure_ascii=False)


@tool
def llm_root_cause_analysis(
    trend_summary: str, similar_cases: str, equipment: str, additional_context: Optional[str] = None
) -> str:
    """基于质量趋势和相似案例，进行人机料法环测6维根因深度分析。
    输入：趋势摘要、相似案例、设备信息、附加上下文
    输出：6维根因分析结果
    """
    analysis_prompt = f"""基于以下信息进行6维根因分析：

质量趋势：{trend_summary}
相似案例：{similar_cases}
设备：{equipment}
附加信息：{additional_context or '无'}

请从人、机、料、法、环、测六个维度分析可能的根因。"""

    return json.dumps(
        {
            "analysis_request": analysis_prompt,
            "note": "此工具触发LLM进行深度推理，结果将由Agent整合到最终诊断中",
        },
        ensure_ascii=False,
    )


@tool
def generate_improvement_plan(root_causes_json: str) -> str:
    """基于根因分析结果生成改进方案。
    输入：根因分析结果（JSON字符串）
    输出：改进方案列表
    """
    try:
        root_causes = json.loads(root_causes_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "根因数据格式错误"}, ensure_ascii=False)

    plans = []
    priority_map = {"机": "P0-紧急", "人": "P1-重要", "料": "P1-重要", "法": "P2-一般", "环": "P2-一般", "测": "P1-重要"}

    for cause in root_causes:
        category = cause.get("category", "")
        priority = priority_map.get(category, "P2-一般")

        plan = {
            "priority": priority,
            "action": f"针对{cause.get('cause', '未知问题')}的改进措施",
            "category": category,
            "responsible": _get_responsible_dept(category),
            "estimated_cost": _estimate_cost(category, cause),
            "expected_effect": f"预计改善合格率{cause.get('confidence', 0.5) * 5:.1f}%",
            "implementation_time": _estimate_time(priority),
            "roi": "",
        }
        plans.append(plan)

    return json.dumps(plans, ensure_ascii=False)


@tool
def calculate_roi(cost: float, daily_loss: float, improvement_rate: float) -> str:
    """计算改进方案的投入产出比(ROI)。
    输入：改进成本、每日损失金额、预期改善率
    输出：ROI分析结果
    """
    daily_saving = daily_loss * improvement_rate
    payback_days = cost / daily_saving if daily_saving > 0 else float("inf")
    monthly_saving = daily_saving * 30
    annual_saving = daily_saving * 365

    return json.dumps(
        {
            "cost": cost,
            "daily_saving": round(daily_saving, 2),
            "monthly_saving": round(monthly_saving, 2),
            "annual_saving": round(annual_saving, 2),
            "payback_days": round(payback_days, 1),
            "roi_ratio": round(annual_saving / cost, 2) if cost > 0 else 0,
            "description": f"投入¥{cost:,.0f}，预计{payback_days:.0f}天回本，年节省¥{annual_saving:,.0f}",
        },
        ensure_ascii=False,
    )


def _get_responsible_dept(category: str) -> str:
    dept_map = {
        "人": "人力资源部+质量部",
        "机": "设备维修组",
        "料": "采购部+质量部",
        "法": "工艺技术部",
        "环": "生产管理部",
        "测": "计量检测中心",
    }
    return dept_map.get(category, "质量部")


def _estimate_cost(category: str, cause: dict) -> int:
    cost_map = {"人": 500, "机": 2000, "料": 3000, "法": 1000, "环": 1500, "测": 800}
    base = cost_map.get(category, 1000)
    confidence = cause.get("confidence", 0.5)
    return int(base * (1 + confidence))


def _estimate_time(priority: str) -> str:
    time_map = {"P0-紧急": "2小时", "P1-重要": "3天", "P2-一般": "1周"}
    return time_map.get(priority, "1周")


def _get_fallback_cases(query: str) -> list[dict]:
    """当Milvus不可用时的备选案例"""
    return [
        {
            "case_id": "CASE-001",
            "title": "砂轮磨损导致尺寸超差",
            "root_cause": "砂轮连续使用超过规定寿命，磨损严重",
            "solution": "更换砂轮，建立砂轮寿命管理制度",
            "category": "机",
        },
        {
            "case_id": "CASE-002",
            "title": "新员工操作不规范导致批量不合格",
            "root_cause": "新员工培训不足，未掌握关键工序要点",
            "solution": "强化岗前培训，实施师带徒制度",
            "category": "人",
        },
        {
            "case_id": "CASE-003",
            "title": "原材料批次差异导致加工尺寸波动",
            "root_cause": "供应商更换原材料配方，硬度偏差大",
            "solution": "加强来料检验，建立供应商质量档案",
            "category": "料",
        },
    ]
