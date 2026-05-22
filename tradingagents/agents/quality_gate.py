# TradingAgents/agents/quality_gate.py
# Data quality gate: hard checks + LLM review before debate phase

from typing import Annotated

from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")

REPORT_FIELDS = {
    "market": "market_report",
    "social": "sentiment_report",
    "news": "news_report",
    "fundamentals": "fundamentals_report",
    "policy": "policy_report",
    "hot_money": "hot_money_report",
    "lockup": "lockup_report",
}

ANALYST_NAMES = {
    "market": "技术分析师",
    "social": "情绪分析师",
    "news": "新闻分析师",
    "fundamentals": "基本面分析师",
    "policy": "政策分析师",
    "hot_money": "游资追踪师",
    "lockup": "解禁监控师",
}

MIN_REPORT_LENGTH = 200

FAILURE_MARKERS = [
    "无法获取",
    "I cannot retrieve",
    "I don't have access",
    "unable to fetch",
    "工具调用失败",
]

# 仅A股市场运行的分析师 — 非A股场景下报告为空是正常的，不应扣分
A_STOCK_ONLY_ANALYSTS = {"policy", "hot_money", "lockup"}


def _is_report_applicable(analyst_type: str, reports: dict) -> bool:
    """Check whether a report is expected to have content.

    A-stock-only analysts (policy, hot_money, lockup) may legitimately produce
    empty reports when analyzing non-A-share markets. We detect this by checking
    if ALL A-stock-exclusive reports are empty — if so, the market is likely
    non-A-share and those empty reports should not be penalized.
    """
    if analyst_type not in A_STOCK_ONLY_ANALYSTS:
        return True
    # If at least one A-stock-only report has content, all three are applicable
    for a_type in A_STOCK_ONLY_ANALYSTS:
        field = REPORT_FIELDS[a_type]
        if reports.get(field, "") and len(reports.get(field, "").strip()) >= MIN_REPORT_LENGTH:
            return True
    return False


def _hard_check_report(analyst_type: str, report: str, reports: dict = None) -> tuple:
    """Run hard checks on a single report. Returns (grade, detail)."""
    if reports is None:
        reports = {}

    # Non-applicable reports (e.g. A-stock-only analysts for US/HK markets) get N/A
    if not _is_report_applicable(analyst_type, reports):
        return ("N/A", "非适用市场，已跳过")

    if not report or not report.strip():
        return ("F", "报告为空")

    length = len(report.strip())
    if length < MIN_REPORT_LENGTH:
        return ("D", f"报告过短 ({length} chars < {MIN_REPORT_LENGTH})")

    failure_count = sum(1 for m in FAILURE_MARKERS if m in report)
    stripped = report
    for m in FAILURE_MARKERS:
        stripped = stripped.replace(m, "")
    if failure_count > 0 and len(stripped.strip()) < MIN_REPORT_LENGTH:
        return ("D", f"报告主要由失败信息构成 ({failure_count} 处)")

    has_table = "|" in report and "---" in report
    missing_count = report.count("[数据缺失")

    issues = []
    if not has_table:
        issues.append("缺少汇总表格")
    if missing_count > 0:
        issues.append(f"{missing_count} 处数据缺失")

    if missing_count >= 3:
        return ("C", "；".join(issues))
    if not has_table or missing_count > 0:
        return ("B", "；".join(issues) if issues else "基本合格")

    return ("A", f"完整 ({length} chars)")


def _build_review_prompt(
    reports: dict, trade_date: str, ticker: str
) -> str:
    """Build the LLM review prompt."""
    report_sections = []
    for analyst_type, field in REPORT_FIELDS.items():
        name = ANALYST_NAMES[analyst_type]
        content = reports.get(field, "（未运行）")
        if not content:
            content = "（报告为空）"
        if len(content) > 3000:
            content = content[:3000] + "\n... (truncated for review)"
        report_sections.append(f"### {name} ({analyst_type})\n{content}")

    all_reports = "\n\n".join(report_sections)

    return f"""你是数据质量审核员。以下是 7 位分析师对 {ticker} 在 {trade_date} 的研究报告。请逐一审核。

{all_reports}

---

请按以下格式输出审核结果（不要输出其他内容）：

## 数据质量审核报告

**标的**: {ticker} | **日期**: {trade_date}

| 分析师 | 评级 | 数据时效 | 缺失项 | 备注 |
|--------|------|----------|--------|------|
| 技术分析师 | A/B/C/D/F | 是否匹配交易日 | 列出缺失的必采项 | 简要说明 |
| 情绪分析师 | ... | ... | ... | ... |
| 新闻分析师 | ... | ... | ... | ... |
| 基本面分析师 | ... | ... | ... | ... |
| 政策分析师 | ... | ... | ... | ... |
| 游资追踪师 | ... | ... | ... | ... |
| 解禁监控师 | ... | ... | ... | ... |

**整体评级**: A/B/C/D/F
**数据可信度**: 高/中/低
**建议**: （如有数据缺失，提醒辩论阶段谨慎使用该报告）

评级标准：
- A: 必采清单全部覆盖，数据时效匹配，有汇总表格
- B: 缺少 1-2 项非关键数据，整体可用
- C: 缺少 3+ 项或有数据时效问题，需谨慎使用
- D: 大量缺失或主要为失败信息，可信度低
- F: 报告为空或完全无效
"""


def create_quality_gate(llm):
    """Factory for the data quality gate node.

    Sits between the last analyst Msg Clear and Bull Researcher.
    Layer 1: hard checks (code). Layer 2: LLM review (one call).
    Writes data_quality_summary to state for downstream consumers.
    """

    def quality_gate_node(state) -> dict:
        trade_date = state["trade_date"]
        ticker = state["company_of_interest"]

        reports = {}
        for analyst_type, field in REPORT_FIELDS.items():
            reports[field] = state.get(field, "")

        hard_results = {}
        for analyst_type, field in REPORT_FIELDS.items():
            grade, detail = _hard_check_report(analyst_type, reports[field], reports)
            hard_results[analyst_type] = (grade, detail)

        hard_summary_lines = []
        for analyst_type, (grade, detail) in hard_results.items():
            name = ANALYST_NAMES[analyst_type]
            hard_summary_lines.append(f"- {name}: [{grade}] {detail}")
        hard_summary = "\n".join(hard_summary_lines)

        # Count applicable (non-N/A) reports for threshold comparison
        applicable_count = sum(
            1 for _, (g, _) in hard_results.items() if g != "N/A"
        )
        fail_count = sum(
            1 for _, (g, _) in hard_results.items() if g in ("F", "D")
        )

        llm_review = ""
        if fail_count < max(4, applicable_count):
            try:
                review_prompt = _build_review_prompt(reports, trade_date, ticker)
                response = llm.invoke(review_prompt)
                llm_review = response.content
            except Exception as e:
                logger.error(f"❌ [质量门控] LLM复审失败: {type(e).__name__}: {e}")
                llm_review = f"（LLM 复审失败: {type(e).__name__}: {e}）"

        summary = (
            f"## 数据质量门控结果\n\n"
            f"**标的**: {ticker} | **交易日**: {trade_date}\n\n"
            f"### 硬检查结果\n{hard_summary}\n\n"
            f"### LLM 复审\n"
            f"{llm_review if llm_review else '（跳过 — 多数报告未通过硬检查）'}\n"
        )

        logger.info(f"✅ [质量门控] 完成，硬检查失败数: {fail_count}, LLM复审: {'已执行' if llm_review else '已跳过'}")
        return {"data_quality_summary": summary}

    return quality_gate_node