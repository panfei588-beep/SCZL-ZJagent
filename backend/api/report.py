"""质量诊断报告 PDF 生成接口"""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

router = APIRouter()


class ReportData(BaseModel):
    """报告数据模型"""
    statistics: Optional[dict] = {}
    root_causes: Optional[list] = []
    solutions: Optional[list] = []
    diagnosis_confidence: Optional[float] = 0
    total_records: Optional[int] = 0
    equipment: Optional[str] = "未指定"


def build_report_html(data: ReportData) -> str:
    """生成报告 HTML（weasyprint 渲染用）"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    stats = data.statistics or {}
    causes = data.root_causes or []
    sols = data.solutions or []

    # 统计数值
    total_records = stats.get("total_records", data.total_records)
    pass_rate = stats.get("pass_rate", "-")
    fail_count = stats.get("fail_count", "-")
    conf = round((data.diagnosis_confidence or 0) * 100, 0)

    # 统计概览
    stats_cards = f"""
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-value">{total_records}</div><div class="stat-label">检测记录总数</div></div>
      <div class="stat-card"><div class="stat-value">{pass_rate}{'%' if pass_rate != '-' else ''}</div><div class="stat-label">合格率</div></div>
      <div class="stat-card"><div class="stat-value">{fail_count}</div><div class="stat-label">不合格数</div></div>
      <div class="stat-card"><div class="stat-value">{conf}%</div><div class="stat-label">诊断置信度</div></div>
    </div>"""

    # 数值统计表格
    numeric_html = ""
    numeric_stats = stats.get("numeric_stats", {})
    if numeric_stats:
        rows = ""
        for col, val in numeric_stats.items():
            rows += f"<tr><td>{col}</td><td>{val['max']}</td><td>{val['min']}</td><td>{val['mean']}</td><td>{val['std']}</td><td>[{val['envelope_lower']}, {val['envelope_upper']}]</td></tr>"
        numeric_html = f"""
        <table>
          <tr><th>指标</th><th>最大值</th><th>最小值</th><th>均值</th><th>标准差</th><th>波动包络</th></tr>
          {rows}
        </table>"""

    # 根因分析
    causes_html = ""
    for c in causes:
        ev = c.get("evidence", [])
        evidence = "；".join(ev) if isinstance(ev, list) else (ev or "")
        impact = c.get("impact", "")
        conf_pct = round((c.get("confidence", 0) or 0) * 100)
        cat = c.get("category", "")
        causes_html += f"""
        <div class="cause-item">
          <div class="rank">NO.{c.get('rank', '-')}</div>
          <div>
            <div class="cause-name">{c.get('cause', '')} <span class="tag">{cat}</span> <span class="tag green">置信度 {conf_pct}%</span></div>
            <div class="meta">{impact}</div>
            <div class="meta">{evidence}</div>
          </div>
        </div>"""
    if not causes_html:
        causes_html = '<p style="color:#94a3b8;padding:12px 0">暂无诊断结果</p>'

    # 改进方案表格
    solutions_html = ""
    if sols:
        sol_rows = ""
        for s in sols:
            dot = "high" if "紧急" in str(s.get("priority", "")) else "medium"
            sol_rows += f"""<tr>
              <td><span class="priority-dot {dot}"></span>{s.get('priority', '')}</td>
              <td>{s.get('action', '')}</td>
              <td>{s.get('responsible', '')}</td>
              <td>{s.get('expected_effect', '')}</td>
              <td>{s.get('implementation_time', '')}</td>
            </tr>"""
        solutions_html = f"""
        <table>
          <tr><th>级别</th><th>改进策略项</th><th>协同部门</th><th>预期产出</th><th>建议周期</th></tr>
          {sol_rows}
        </table>"""
    else:
        solutions_html = '<p style="color:#94a3b8;padding:12px 0">暂无改进方案</p>'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  @page {{
    size: A4;
    margin: 20mm;
    @bottom-center {{
      content: "CorpClaw · 质量诊断报告";
      font-size: 9px;
      color: #94a3b8;
    }}
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: "Noto Sans CJK SC", "Microsoft YaHei", "PingFang SC", sans-serif; color: #1e293b; }}
  .header {{ background: #0f172a; color: #fff; padding: 24px 32px; margin: -20mm -20mm 20mm -20mm; }}
  .header h1 {{ font-size: 22px; margin-bottom: 6px; }}
  .header p {{ color: #94a3b8; font-size: 13px; }}
  .section {{ margin-bottom: 20px; }}
  .section-title {{ font-size: 15px; font-weight: 700; color: #0f172a; margin-bottom: 12px; padding-left: 10px; border-left: 3px solid #3b82f6; }}
  .stats-grid {{ display: flex; gap: 12px; margin-bottom: 16px; }}
  .stat-card {{ flex: 1; background: #f8fafc; border-radius: 4px; padding: 12px; text-align: center; border: 1px solid #e2e8f0; }}
  .stat-value {{ font-size: 20px; font-weight: 800; color: #0f172a; }}
  .stat-label {{ font-size: 11px; color: #64748b; margin-top: 3px; }}
  .cause-item {{ display: flex; gap: 10px; padding: 10px 0; border-bottom: 1px dashed #e2e8f0; }}
  .cause-item:last-child {{ border-bottom: none; }}
  .rank {{ background: #e2e8f0; color: #475569; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: 700; height: max-content; }}
  .cause-name {{ font-weight: 600; margin-bottom: 3px; font-size: 13px; }}
  .meta {{ font-size: 12px; color: #64748b; margin-bottom: 3px; }}
  .tag {{ display: inline-block; padding: 1px 6px; background: #fef2f2; color: #dc2626; border-radius: 3px; font-size: 10px; }}
  .tag.green {{ background: #f0fdf4; color: #16a34a; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 6px; }}
  th, td {{ border: 1px solid #e2e8f0; padding: 8px 10px; text-align: left; font-size: 12px; }}
  th {{ background: #f8fafc; color: #475569; font-weight: 700; }}
  .priority-dot {{ display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }}
  .priority-dot.high {{ background: #ef4444; }}
  .priority-dot.medium {{ background: #f59e0b; }}
  .footer {{ text-align: center; color: #94a3b8; font-size: 11px; margin-top: 30px; padding-top: 16px; border-top: 1px solid #e2e8f0; }}
</style>
</head>
<body>
  <div class="header">
    <h1>质量异常诊断报告</h1>
    <p>生成时间：{now} | 设备：{data.equipment or '未指定'}</p>
  </div>

  <div class="section">
    <div class="section-title">一、数据统计概览</div>
    {stats_cards}
    {numeric_html}
  </div>

  <div class="section">
    <div class="section-title">二、AI 根因诊断分析</div>
    {causes_html}
  </div>

  <div class="section">
    <div class="section-title">三、智能化改进方案</div>
    {solutions_html}
  </div>

  <div class="footer">
    <p>本报告由 AI 质量诊断系统自动生成，仅供参考</p>
    <p>CorpClaw · 航天运载火箭质量异常诊断数字员工</p>
  </div>
</body>
</html>"""
    return html


@router.post("/generate")
async def generate_report(data: ReportData):
    """生成质量诊断报告 PDF"""
    try:
        from weasyprint import HTML

        html_content = build_report_html(data)

        pdf_bytes = HTML(string=html_content).write_pdf()

        from fastapi.responses import Response
        from urllib.parse import quote
        filename = f"质量诊断报告_{datetime.now().strftime('%Y%m%d')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
            },
        )

    except ImportError:
        raise HTTPException(status_code=500, detail="PDF 生成服务未安装 (weasyprint)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 生成失败: {str(e)}")
