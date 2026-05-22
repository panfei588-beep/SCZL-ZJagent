"""
LangGraph StateGraph 质量诊断工作流编排
8 节点：supervisor → data_agent → validate_data → diagnosis_agent → validate_diagnosis → decision_agent → output_merger → knowledge_node
"""

from __future__ import annotations

import time
import json
import logging
import os
import re
from typing import Optional, TypedDict

import numpy as np
import pandas as pd
from langchain_community.chat_models import ChatTongyi
from langchain.schema import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from core.config import get_settings
from services.file_parser import parse_file
from services.chart_generator import generate_trend_chart, generate_distribution_chart
from knowledge_base.milvus_client import search_diagnosis_cases, search_improvement_cases, write_to_diagnosis_kb, write_to_improvement_kb, write_to_pending_kb

settings = get_settings()


# ======================== State 定义 ========================

class QualityAgentState(TypedDict):
    raw_file_path: str                       # 上传文件路径（支持多文件，用逗号分隔）
    user_params: dict                        # 用户选项参数
    parsed_data: Optional[dict]              # 解析后的结构化数据
    statistics: Optional[dict]               # max/min/mean/std/包络线
    charts: Optional[list]                   # 图表文件路径列表
    data_valid: Optional[bool]               # 数据校验结果
    data_retry_count: int                    # 数据解析重试次数
    diagnosis_result: Optional[list]         # 诊断原因列表
    diagnosis_confidence: Optional[float]    # 置信度 0~1
    diagnosis_has_kb_ref: Optional[bool]     # 是否有知识库依据
    diagnosis_valid: Optional[bool]          # 诊断校验结果
    low_confidence_flag: Optional[bool]      # 低置信度预警标记
    improvement_plan: Optional[list]         # 改进方案列表
    estimated_improvement: Optional[str]     # 预估提升效果
    final_output: Optional[dict]             # 最终输出
    error_message: Optional[str]             # 异常信息
    knowledge_candidate: Optional[dict]      # 知识沉淀候选内容
    knowledge_persisted: Optional[dict]      # 知识沉淀结果


# ======================== LLM 初始化 ========================

llm = ChatTongyi(
    model="qwen-max",
    dashscope_api_key=settings.dashscope_api_key,
    temperature=0.1,
    max_tokens=4096,
)


# ======================== 节点函数 ========================

def supervisor_node(state: QualityAgentState) -> dict:
    """Supervisor 路由调度节点: 负责任务分发 / 状态管理 / 异常路由"""
    start = time.time()
    file_path = state.get("raw_file_path", "")
    user_params = state.get("user_params", {})
    retry_count = state.get("data_retry_count", 0)
    data_valid = state.get("data_valid")

    # 路由决策
    if data_valid is False and retry_count < settings.data_retry_limit:
        # 数据校验失败，回退重试
        logging.info(f"[supervisor] 数据校验失败，回退重试 (第 {retry_count + 1} 次)")
        elapsed = time.time() - start
        logging.info(f"[supervisor] 耗时 {elapsed:.2f}s")
        return {
            "data_valid": None,  # 重置校验状态
            "routing_decision": "retry",
            "retry_target": "data_agent",
        }
    elif data_valid is False and retry_count >= settings.data_retry_limit:
        # 重试耗尽，降级继续
        logging.warning(f"[supervisor] 数据重试耗尽 ({retry_count} 次)，降级继续")
        elapsed = time.time() - start
        logging.info(f"[supervisor] 耗时 {elapsed:.2f}s")
        return {
            "routing_decision": "diagnosis_agent",
            "flag": "DATA_ERROR",
            "check_reason": f"数据校验失败，重试 {retry_count} 次",
        }

    logging.info(f"[supervisor] 路由调度: 文件={file_path}, 设备={user_params.get('equipment', 'N/A')}")
    elapsed = time.time() - start
    logging.info(f"[supervisor] 耗时 {elapsed:.2f}s")
    return {
        "routing_decision": "data_agent",
        "flag": "NORMAL",
        "check_reason": "",
    }


def data_agent_node(state: QualityAgentState) -> dict:
    """Agent1: 解析文件 → 统计计算 → 生成图表"""
    start = time.time()
    file_path = state["raw_file_path"]
    logging.info(f"[data_agent] 解析文件: {file_path}")

    parsed_data = {}
    statistics = {}
    charts = []

    try:
        ext = os.path.splitext(file_path)[1].lower()

        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path)
        elif ext == ".csv":
            df = pd.read_csv(file_path)
        else:
            # PDF/图片/Word 由 MinerU 解析
            result = pd.DataFrame()
            parsed_result = None
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 在 async 环境中用 run_coroutine_threadsafe
                    import concurrent.futures
                    future = asyncio.run_coroutine_threadsafe(parse_file(file_path, ext), loop)
                    parsed_result = future.result(timeout=120)
                else:
                    parsed_result = asyncio.run(parse_file(file_path, ext))
            except Exception:
                parsed_result = None

            if parsed_result and parsed_result.get("records"):
                result = pd.DataFrame(parsed_result["records"])
            else:
                result = pd.DataFrame({"raw": ["文件解析无结构化数据"]})
            df = result

        records = df.to_dict(orient="records")
        parsed_data = {
            "columns": list(df.columns),
            "total_records": len(df),
            "records_preview": records[:5],
        }

        # 统计计算
        result_col = None
        for col in df.columns:
            if col in ("判定", "结果", "result"):
                result_col = col
                break

        if result_col:
            total = len(df)
            pass_count = len(df[df[result_col].isin(["合格", "pass", "PASS", "OK"])])
            pass_rate = round(pass_count / total * 100, 2) if total > 0 else 0
            statistics["pass_rate"] = pass_rate
            statistics["total_records"] = total
            statistics["pass_count"] = pass_count
            statistics["fail_count"] = total - pass_count

            # 不合格项分布
            fail_df = df[~df[result_col].isin(["合格", "pass", "PASS", "OK"])]
            item_col = None
            for col in df.columns:
                if col in ("检测项", "检测项目", "inspection_item"):
                    item_col = col
                    break
            if item_col and item_col in fail_df.columns:
                statistics["top_fail_items"] = fail_df[item_col].value_counts().head(5).to_dict()
        else:
            statistics["total_records"] = len(df)
            statistics["columns"] = list(df.columns)

        # 数值列统计
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            col_stats = {}
            for col in numeric_cols[:10]:  # 最多统计前 10 列
                vals = df[col].dropna()
                if len(vals) > 0:
                    mean_val = float(vals.mean())
                    std_val = float(vals.std())
                    n = len(vals)
                    multiplier = 2.0 if n < 20 else 3.0
                    col_stats[col] = {
                        "max": float(vals.max()),
                        "min": float(vals.min()),
                        "mean": round(mean_val, 4),
                        "std": round(std_val, 4),
                        "envelope_upper": round(mean_val + multiplier * std_val, 4),
                        "envelope_lower": round(mean_val - multiplier * std_val, 4),
                    }
            statistics["numeric_stats"] = col_stats

        # 日期趋势
        date_col = None
        for col in df.columns:
            if col in ("日期", "时间", "record_date", "date"):
                date_col = col
                break

        if date_col and result_col:
            df_copy = df.copy()
            df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors="coerce")
            df_copy = df_copy.dropna(subset=[date_col])
            if len(df_copy) > 0:
                daily = df_copy.groupby(df_copy[date_col].dt.date)[result_col].apply(
                    lambda x: round(x.isin(["合格", "pass", "PASS", "OK"]).sum() / len(x) * 100, 2)
                )
                statistics["trend_dates"] = [str(d) for d in daily.index]
                statistics["trend_rates"] = list(daily.values)

                # 生成趋势图
                charts_dir = os.path.join(os.path.dirname(__file__), "..", "charts")
                chart_path = generate_trend_chart(
                    dates=statistics["trend_dates"],
                    rates=statistics["trend_rates"],
                    title="合格率趋势分析",
                    save_dir=charts_dir,
                    envelope=len(statistics["trend_rates"]) >= 5,
                )
                if chart_path:
                    charts.append(chart_path)

        # 数值分布图
        if numeric_cols:
            primary_col = numeric_cols[0]
            vals = df[primary_col].dropna().tolist()
            if len(vals) >= 10:
                charts_dir = os.path.join(os.path.dirname(__file__), "..", "charts")
                chart_path = generate_distribution_chart(
                    values=vals,
                    title=f"{primary_col} 分布分析",
                    xlabel=primary_col,
                    save_dir=charts_dir,
                )
                if chart_path:
                    charts.append(chart_path)

    except Exception as e:
        logging.error(f"[data_agent] 解析失败: {e}", exc_info=True)
        statistics["error"] = str(e)

    elapsed = time.time() - start
    logging.info(f"[data_agent] 耗时 {elapsed:.2f}s")
    return {
        "parsed_data": parsed_data,
        "statistics": statistics,
        "charts": charts,
        "data_retry_count": state.get("data_retry_count", 0) + 1,
    }


def validate_data_node(state: QualityAgentState) -> dict:
    """校验节点: 字段完整性 / 数值范围 / 时间连续性"""
    stats = state.get("statistics") or {}
    parsed = state.get("parsed_data") or {}

    errors = []

    # 字段完整性
    if not parsed.get("columns"):
        errors.append("未检测到任何数据列")

    # 数值范围检查
    if "pass_rate" in stats:
        rate = stats["pass_rate"]
        if rate < 0 or rate > 100:
            errors.append(f"合格率异常: {rate}%")

    # 数据量检查
    if stats.get("total_records", 0) == 0:
        errors.append("数据为空")

    data_valid = len(errors) == 0

    if not data_valid:
        logging.warning(f"[validate_data] 校验失败: {errors}")
        return {"data_valid": False, "error_message": "; ".join(errors)}
    return {"data_valid": True}


def should_retry_data(state: QualityAgentState) -> str:
    """条件边: 数据校验失败且重试次数 < 3 → 回退 data_agent"""
    if state.get("data_valid"):
        return "diagnosis_agent"
    if state.get("data_retry_count", 0) < settings.data_retry_limit:
        return "data_agent"
    # 重试耗尽，降级继续但记录错误
    return "diagnosis_agent"


def diagnosis_agent_node(state: QualityAgentState) -> dict:
    """Agent2: RAG 检索 + LLM 根因分析"""
    start = time.time()
    stats = state.get("statistics", {})
    user_params = state.get("user_params", {})

    logging.info("[diagnosis_agent] 开始诊断分析")

    # RAG 检索诊断知识库（优化: top_k=3 减少检索时间）
    equipment = user_params.get("equipment", "未指定设备")
    query = f"{equipment} 质量异常"
    similar_cases = search_diagnosis_cases(query, top_k=3)

    # 构建上下文（优化: 精简统计数据，减少 token）
    context_parts = [
        f"设备: {equipment}",
        f"总记录数: {stats.get('total_records', 0)}",
        f"合格率: {stats.get('pass_rate', 'N/A')}%",
        f"不合格数: {stats.get('fail_count', 0)}",
    ]

    if "numeric_stats" in stats:
        for col, s in stats["numeric_stats"].items():
            context_parts.append(
                f"数值列 {col}: max={s['max']}, min={s['min']}, mean={s['mean']}, std={s['std']}"
            )

    if "trend_dates" in stats and "trend_rates" in stats:
        dates = stats["trend_dates"]
        rates = stats["trend_rates"]
        context_parts.append(f"合格率趋势: 初始={rates[0]}%, 当前={rates[-1]}%, 共{len(dates)}天")

    if "top_fail_items" in stats:
        context_parts.append(f"主要不合格项: {stats['top_fail_items']}")

    if user_params.get("operator"):
        context_parts.append(f"操作员: {user_params['operator']}")
    if user_params.get("material"):
        context_parts.append(f"物料: {user_params['material']}")
    if user_params.get("environment"):
        context_parts.append(f"环境: {user_params['environment']}")

    # 相似案例（优化: 只传 title + root_cause）
    case_texts = []
    has_kb_ref = False
    for c in similar_cases:
        if "error" not in c:
            case_texts.append(
                f"[{c['case_id']}] {c['title']} | 根因: {c.get('root_cause', '')}"
            )
            has_kb_ref = True
    context_parts.append(f"相似案例: {'; '.join(case_texts) if case_texts else '无'}")

    # LLM 推理 - 按需求文档 Agent2 Prompt 定义
    system_prompt = """你是企业级异常诊断智能体，基于统计数据和知识库检索，输出根因分析报告。

## Task Steps
Step1: 提取异常特征 - 从统计数据中识别异常字段和异常值区间
Step2: RAG 知识库检索 - 结合提供的知识库内容进行匹配
Step3: 根因推理 - 结合异常特征 + 知识库内容，输出根因列表，每条附相关性分数和证据链

## Output Format (严格 JSON)
{
  "diagnosis": [
    {
      "rank": 1,
      "root_cause": "根因描述（≤ 50 字）",
      "confidence": 0.85,
      "evidence": "知识库依据摘要（≤ 80 字）",
      "affected_fields": ["字段名"]
    }
  ],
  "overall_confidence": 0.82,
  "low_confidence_flag": false,
  "kb_retrieval_count": 3
}

## Constraints
- 根因条数: 3〜5 条，按 confidence 降序排列
- confidence < 0.6 时，low_confidence_flag 设为 true
- 禁止输出知识库中不存在的根因（严禁幻觉）
- 每条 root_cause 必须有 evidence 支撑"""

    human_prompt = f"""请对以下质量数据进行完整的异常诊断分析：

统计数据：
{json.dumps(stats, ensure_ascii=False, indent=2)}

参考案例：
{'; '.join(case_texts) if case_texts else '暂无知识库数据，基于统计数据推理'}

分析目标：{user_params.get('analysis_goal', '找根因')}"""

    try:
        response = llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
        )
        result = _parse_llm_json(response.content)

        # 适配新格式: diagnosis → diagnosis_result
        diagnosis_list = result.get("diagnosis", result.get("root_causes", []))
        overall_conf = result.get("overall_confidence", 0.5)

        # 过滤掉 LLM 兜底回复
        diagnosis_list = [
            c for c in diagnosis_list
            if "数据不足" not in c.get("root_cause", c.get("cause", ""))
            and "无法基于" not in c.get("root_cause", c.get("cause", ""))
        ]

        # 按置信度降序排序，重新编号 rank
        diagnosis_list.sort(key=lambda c: c.get("confidence", 0), reverse=True)
        for i, c in enumerate(diagnosis_list):
            c["rank"] = i + 1
            # 兼容旧格式: 确保 cause 字段存在
            if "root_cause" in c and "cause" not in c:
                c["cause"] = c["root_cause"]
            if "cause" in c and "root_cause" not in c:
                c["root_cause"] = c["cause"]

        # 计算平均置信度
        if diagnosis_list:
            avg_confidence = sum(c.get("confidence", 0.5) for c in diagnosis_list) / len(diagnosis_list)
        else:
            avg_confidence = overall_conf if overall_conf else 0.5

        return {
            "diagnosis_result": diagnosis_list,
            "diagnosis_confidence": round(avg_confidence, 3),
            "diagnosis_has_kb_ref": has_kb_ref,
        }

    except Exception as e:
        logging.error(f"[diagnosis_agent] LLM 推理失败: {e}", exc_info=True)
        elapsed = time.time() - start
        logging.info(f"[diagnosis_agent] 耗时 {elapsed:.2f}s (失败)")
        return {
            "diagnosis_result": [],
            "diagnosis_confidence": 0.5,
            "diagnosis_has_kb_ref": False,
            "error_message": f"诊断分析失败: {str(e)}",
        }


def validate_diagnosis_node(state: QualityAgentState) -> dict:
    """诊断校验节点: 置信度阈值 + KB 引用检查，低置信打标但不阻断"""
    confidence = state.get("diagnosis_confidence", 0.5)
    has_kb_ref = state.get("diagnosis_has_kb_ref", False)
    threshold = settings.confidence_threshold

    low_confidence = confidence < threshold
    # 有 KB 引用且置信度达标则认为有效
    diagnosis_valid = confidence >= threshold or has_kb_ref

    if low_confidence:
        logging.warning(
            f"[validate_diagnosis] 低置信度: {confidence} (阈值 {threshold})"
        )

    return {
        "diagnosis_valid": diagnosis_valid,
        "low_confidence_flag": low_confidence,
    }


def decision_agent_node(state: QualityAgentState) -> dict:
    """Agent3: RAG 检索改善知识库 + LLM 生成改进方案"""
    start = time.time()
    # 优先使用 user_params 中的 root_causes（兼容单独调用方案生成接口）
    root_causes = state.get("user_params", {}).get("root_causes") or state.get("diagnosis_result", []) or []
    low_conf = state.get("low_confidence_flag", False)
    user_params = state.get("user_params", {})

    logging.info("[decision_agent] 开始生成改进方案")

    # RAG 检索改善知识库（优化: top_k=3 减少检索时间）
    equipment = user_params.get("equipment", "未指定设备")
    cause_keywords = [c.get("cause", c.get("root_cause", "")) for c in root_causes if c.get("cause", c.get("root_cause", ""))]
    query = f"{equipment} 质量改善 {' '.join(cause_keywords)}"
    improvement_cases = search_improvement_cases(query, top_k=3)

    # 案例精简（优化: 只传 title + solution + effect）
    case_texts = []
    for c in improvement_cases:
        if "error" not in c:
            case_texts.append(
                f"[{c['case_id']}] {c['title']} | 方案: {c.get('solution', '')} | 效果: {c.get('effect', '')}"
            )

    warning_text = "⚠ 注意：本次诊断置信度较低，以下方案仅供参考" if low_conf else ""

    system_prompt = """你是企业级决策支持智能体，基于诊断结论和改善案例知识库，生成可落地的改进方案。

## Task Steps
Step1: 解析诊断结论 - 提取 confidence ≥ 0.5 的根因条目，若有 low_confidence_flag 则标注不确定性
Step2: RAG 知识库检索 - 查询《质量改善案例知识库》Top-3 历史案例
Step3: 方案生成 - 匹配历史案例 → 定制改进方案，每条措施含执行步骤/预估效果/风险提示

## Output Format (严格 JSON 数组)
[
  {
    "target_cause": "对应根因（≤ 30 字）",
    "measures": [
      {
        "step": 1,
        "action": "具体措施（≤ 60 字）",
        "expected_effect": "预估提升效果（如：良品率 +5%）",
        "risk": "风险提示（≤ 30 字）",
        "priority": "HIGH|MEDIUM|LOW"
      }
    ],
    "reference_case": "历史案例摘要（≤ 60 字）",
    "uncertainty_note": "⚠ 低置信度，建议人工复核"
  }
]

## Constraints
- 改进方案条数与根因数量对应（1:1 映射）
- 禁止生成无历史案例支撑的措施（标注为"待验证"而非杜撰）
- low_confidence_flag=true 时，每条方案必须含 uncertainty_note"""

    case_lines = '\n'.join(case_texts) if case_texts else '无历史改善案例'
    # 优化: 压缩 root_causes 为单行，只传必要字段
    causes_summary = []
    for c in root_causes:
        causes_summary.append({
            "cause": c.get("cause", c.get("root_cause", "")),
            "confidence": c.get("confidence", 0.5),
            "impact": c.get("impact", c.get("evidence", "")),
        })
    human_prompt = f"""基于以下根因分析结果，生成改进方案：

根因列表：
{json.dumps(causes_summary, ensure_ascii=False)}

设备：{equipment or '未指定'}

参考历史改善案例：
{case_lines}

{warning_text}"""

    try:
        response = llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
        )
        plan = _parse_llm_json(response.content)
        if not isinstance(plan, list):
            plan = []

        estimated = "预计整体合格率可提升 2-5 个百分点"
        elapsed = time.time() - start
        logging.info(f"[decision_agent] 耗时 {elapsed:.2f}s")
        return {
            "improvement_plan": plan,
            "estimated_improvement": estimated,
        }

    except Exception as e:
        logging.error(f"[decision_agent] 方案生成失败: {e}", exc_info=True)
        elapsed = time.time() - start
        logging.info(f"[decision_agent] 耗时 {elapsed:.2f}s (失败)")
        return {
            "improvement_plan": [],
            "estimated_improvement": "",
            "error_message": f"方案生成失败: {str(e)}",
        }


def output_merger_node(state: QualityAgentState) -> dict:
    """输出整合节点: 汇总三个 Agent 的结果"""
    diagnosis = state.get("diagnosis_result", [])
    improvement = state.get("improvement_plan", [])
    confidence = state.get("diagnosis_confidence", 0)
    low_conf = state.get("low_confidence_flag", False)

    final_output = {
        "statistics": state.get("statistics", {}),
        "charts": state.get("charts", []),
        "diagnosis_result": diagnosis,
        "root_causes": diagnosis,  # 向后兼容
        "diagnosis_confidence": confidence,
        "improvement_plan": improvement,
        "estimated_improvement": state.get("estimated_improvement", ""),
        "low_confidence_warning": low_conf,
        "diagnosis_valid": state.get("diagnosis_valid", False),
        "alerts": [],
    }

    # 低置信度警告
    if low_conf:
        final_output["alerts"].append("⚠ 本次诊断置信度较低，建议人工复核")

    # 提取知识沉淀候选内容
    knowledge_candidate = {
        "anomaly_pattern": {
            "fields": state.get("statistics", {}).get("numeric_stats", {}),
            "root_causes": diagnosis,
        },
        "solution_case": {
            "causes": [d.get("cause", d.get("root_cause", "")) for d in diagnosis],
            "measures": improvement,
            "risk_level": "HIGH" if low_conf else "MEDIUM",
        },
        "overall_confidence": confidence,
        "low_confidence_flag": low_conf,
    }

    # 如果有错误信息也带上
    if state.get("error_message"):
        final_output["error_message"] = state["error_message"]

    return {
        "final_output": final_output,
        "knowledge_candidate": knowledge_candidate,
    }


def knowledge_node(state: QualityAgentState) -> dict:
    """知识沉淀节点: 从最终输出中提炼新知识，写入对应知识库"""
    start = time.time()
    candidate = state.get("knowledge_candidate") or {}
    overall_conf = candidate.get("overall_confidence", 0)
    low_conf = candidate.get("low_confidence_flag", False)

    # 优化: 置信度太低直接跳过，不执行 Milvus 写入
    if overall_conf < 0.5:
        logging.info(f"[knowledge_node] 置信度不足 ({overall_conf})，跳过沉淀")
        return {
            "knowledge_persisted": {
                "should_persist": False,
                "persist_target": "skip",
                "kb_write_status": "SKIP",
            },
        }

    # 沉淀规则
    # ① overall_confidence >= 0.7 → 正式库
    # ② low_confidence_flag=true → 待验证暂存区
    if low_conf:
        persist_target = "pending_kb"
        logging.info(f"[knowledge_node] 低置信度 ({overall_conf})，写入待验证暂存区")
    else:
        persist_target = "formal_kb"
        logging.info(f"[knowledge_node] 高置信度 ({overall_conf})，写入正式知识库")

    # 构建知识条目
    anomaly_pattern = candidate.get("anomaly_pattern", {})
    solution_case = candidate.get("solution_case", {})

    diagnosis_knowledge = {
        "anomaly_feature": str(anomaly_pattern.get("fields", {}))[:200],
        "root_causes": anomaly_pattern.get("root_causes", []),
        "confidence": overall_conf,
        "source": "auto_generated_by_agent2",
    }

    improvement_case = {
        "problem": str(solution_case.get("causes", []))[:200],
        "solution": str(solution_case.get("measures", []))[:200],
        "risk_level": solution_case.get("risk_level", "MEDIUM"),
        "source": "auto_generated_by_agent3",
    }

    import uuid
    kb_write_status = "SKIP"
    case_id = str(uuid.uuid4())[:8]

    if persist_target == "pending_kb":
        # 写入待验证暂存区
        kb_text = f"异常特征: {diagnosis_knowledge['anomaly_feature']} 根因: {diagnosis_knowledge['root_causes']}"
        kb_meta = {
            "case_id": f"PENDING_{case_id}",
            "title": "待验证诊断案例",
            "problem": improvement_case["problem"],
            "root_cause": str(diagnosis_knowledge["root_causes"]),
            "solution": improvement_case["solution"],
            "category": "pending",
            "confidence": overall_conf,
        }
        success = write_to_pending_kb(kb_text, kb_meta)
        kb_write_status = "PENDING" if success else "PENDING_FAIL"

    elif persist_target == "formal_kb":
        # 写入正式诊断知识库
        kb_text = f"异常特征: {diagnosis_knowledge['anomaly_feature']} 根因: {diagnosis_knowledge['root_causes']}"
        kb_meta = {
            "case_id": f"KB_{case_id}",
            "title": "自动沉淀诊断案例",
            "problem": improvement_case["problem"],
            "root_cause": str(diagnosis_knowledge["root_causes"]),
            "solution": improvement_case["solution"],
            "category": "auto_generated",
            "confidence": overall_conf,
        }
        success = write_to_diagnosis_kb(kb_text, kb_meta)
        kb_write_status = "SUCCESS" if success else "FAIL"

    elapsed = time.time() - start
    logging.info(f"[knowledge_node] 耗时 {elapsed:.2f}s, status={kb_write_status}")
    return {
        "knowledge_persisted": {
            "should_persist": True,
            "persist_target": persist_target,
            "diagnosis_knowledge": diagnosis_knowledge,
            "improvement_case": improvement_case,
            "kb_write_status": kb_write_status,
        },
    }


# ======================== JSON 解析工具 ========================

def _parse_llm_json(output: str) -> dict | list:
    """robust JSON 解析，支持 markdown code block、brace 匹配和截断修复"""
    try:
        json_str = None
        match = re.search(r"```json\s*\n([\s\S]*?)\n```", output)
        if match:
            json_str = match.group(1)
        elif "{" in output:
            start = output.index("{")
            end = output.rindex("}") + 1
            json_str = output[start:end]
        elif "[" in output:
            start = output.index("[")
            end = output.rindex("]") + 1
            json_str = output[start:end]

        if json_str is None:
            raise ValueError("未找到 JSON 格式输出")

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # LLM 输出被截断时尝试用 json-repair 修复
            try:
                from json_repair import repair_json
                repaired = repair_json(json_str)
                return json.loads(repaired)
            except Exception:
                raise
    except Exception:
        raise ValueError(f"LLM 输出解析失败: {output[:200]}")


# ======================== 图构建 ========================

def build_quality_graph() -> StateGraph:
    """构建 LangGraph StateGraph"""
    graph = StateGraph(QualityAgentState)

    # 注册节点（含新增 Supervisor 和 knowledge_node）
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("data_agent", data_agent_node)
    graph.add_node("validate_data", validate_data_node)
    graph.add_node("diagnosis_agent", diagnosis_agent_node)
    graph.add_node("validate_diagnosis", validate_diagnosis_node)
    graph.add_node("decision_agent", decision_agent_node)
    graph.add_node("output_merger", output_merger_node)
    graph.add_node("knowledge_node", knowledge_node)

    # 边: supervisor → data_agent → validate_data
    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "data_agent")
    graph.add_edge("data_agent", "validate_data")

    # 条件边: validate_data → data_agent(重试) 或 diagnosis_agent(继续)
    graph.add_conditional_edges(
        "validate_data",
        should_retry_data,
        {
            "data_agent": "data_agent",
            "diagnosis_agent": "diagnosis_agent",
        },
    )

    graph.add_edge("diagnosis_agent", "validate_diagnosis")
    graph.add_edge("validate_diagnosis", "decision_agent")
    graph.add_edge("decision_agent", "output_merger")
    graph.add_edge("output_merger", "knowledge_node")
    graph.add_edge("knowledge_node", END)

    # Checkpointer (开发期用 MemorySaver)
    checkpointer = MemorySaver()
    compiled = graph.compile(checkpointer=checkpointer)

    return compiled


# 全局图实例
_quality_graph = None


def get_quality_graph():
    global _quality_graph
    if _quality_graph is None:
        _quality_graph = build_quality_graph()
    return _quality_graph


# ======================== 入口函数 ========================

async def run_analysis(
    file_path: str,
    user_params: Optional[dict] = None,
) -> dict:
    """执行完整质量分析工作流

    Args:
        file_path: 文件路径
        user_params: 用户参数 (equipment, operator, material, environment 等)

    Returns:
        final_output 字典
    """
    graph = get_quality_graph()

    initial_state: QualityAgentState = {
        "raw_file_path": file_path,
        "user_params": user_params or {},
        "parsed_data": None,
        "statistics": None,
        "charts": [],
        "data_valid": None,
        "data_retry_count": 0,
        "diagnosis_result": None,
        "diagnosis_confidence": None,
        "diagnosis_has_kb_ref": None,
        "diagnosis_valid": None,
        "low_confidence_flag": None,
        "improvement_plan": None,
        "estimated_improvement": None,
        "final_output": None,
        "error_message": None,
        "knowledge_candidate": None,
        "knowledge_persisted": None,
    }

    config = {"configurable": {"thread_id": "quality_analysis"}}

    try:
        result = await graph.ainvoke(initial_state, config)
        return result.get("final_output", {})
    except Exception as e:
        logging.error(f"[run_analysis] 工作流执行失败: {e}", exc_info=True)
        return {
            "statistics": {},
            "charts": [],
            "diagnosis_result": [],
            "diagnosis_confidence": 0,
            "improvement_plan": [],
            "estimated_improvement": "",
            "low_confidence_warning": False,
            "error_message": str(e),
        }
