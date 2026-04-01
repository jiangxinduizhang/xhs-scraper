"""
开盘啦运行报告生成。
"""

from __future__ import annotations

from pathlib import Path

from src.apps.kaipanla.task import RunResult, TaskSpec


def _count(result: RunResult, key: str) -> int:
    return int((result.note_type_counts or {}).get(key, 0) or 0)


def _render_human_summary(task: TaskSpec, result: RunResult) -> list[str]:
    if result.status not in {"success", "partial"}:
        return ["- 本次抓取未形成可稳定解读的市场摘要，请先检查抓取状态和错误信息。"]

    msg_top = _count(result, "msg_top")
    fkyd = _count(result, "market_fkyd")
    baceface = _count(result, "market_baceface")
    jjxt = _count(result, "market_jjxt")
    phb = _count(result, "market_phb")
    zqfk = _count(result, "market_zqfk")
    zlsc = _count(result, "market_zlsc")
    weather_sz = _count(result, "market_weather_sz")
    weather_xd = _count(result, "market_weather_xd")
    summary = _count(result, "market_emotion_summary")
    plz = _count(result, "market_plz")
    unknown = int((result.source_counts or {}).get("unknown", 0) or 0)

    lines: list[str] = []

    active_modules = sum(1 for value in [msg_top, fkyd, baceface, jjxt, phb, zqfk, zlsc] if value > 0)
    if active_modules >= 5:
        lines.append("- 市场情绪页主要模块都有数据，页面信息完整度较高，不像是空页或半残抓取。")
    elif active_modules >= 3:
        lines.append("- 市场情绪页拿到了多类模块数据，能做基础观察，但完整度还不是最强。")
    else:
        lines.append("- 当前抓到的模块较少，更适合当作抓取校验，不适合下重结论。")

    if msg_top >= 8:
        lines.append("- 顶部/主展示类信息较活跃，说明页面重点信号输出比较集中，适合先看主叙事和强势方向。")
    elif msg_top >= 4:
        lines.append("- 顶部主信息有一定活跃度，但还看不出特别极端的一致性。")
    else:
        lines.append("- 顶部强提示信息不多，情绪信号可能偏分散。")

    style_modules = []
    if fkyd > 0:
        style_modules.append("风口异动")
    if jjxt > 0:
        style_modules.append("资金/节奏类信号")
    if phb > 0:
        style_modules.append("排行类信号")
    if zqfk > 0:
        style_modules.append("赚钱效应反馈")
    if zlsc > 0:
        style_modules.append("主力市场/资金观察")
    if baceface > 0:
        style_modules.append("情绪面板")
    if style_modules:
        lines.append(f"- 这次可回读的重点模块包括：{'、'.join(style_modules)}。说明今天不只是单点行情，而是有横向观察维度。")

    if weather_sz > 0 or weather_xd > 0 or summary > 0:
        lines.append("- 页面里带有情绪总览/市场天气类信息，适合进一步升级成可直接阅读的人话日报。")

    if plz > 0:
        lines.append("- 还有舆情/评论区类补充信号，但目前占比不高，更适合作为辅助观察。")

    if unknown >= 10:
        lines.append("- 仍有一部分数据暂时落在 unknown，说明 parser 还有继续细分的空间；当前摘要可用，但不是最终形态。")
    elif unknown > 0:
        lines.append("- 有少量未归类数据，不影响总体回读，但后续还可以继续细化解析规则。")

    lines.append("- 就这次结果看，更适合下的结论是：页面抓取稳定、模块覆盖正常、具备继续做盘面摘要的基础；但要判断‘主线/分歧/修复强弱’，还需要把字段内容进一步翻译成人话。")
    return lines


def render_run_report(task: TaskSpec, result: RunResult) -> str:
    lines: list[str] = [
        f"# {task.task_id}",
        "",
        "## 概览",
        f"- 应用: {task.app}",
        f"- 页面: {task.page}",
        f"- 目标: {task.goal or '无'}",
        f"- 状态: {result.status}",
        f"- 开始: {result.started_at}",
        f"- 结束: {result.finished_at or '进行中'}",
        f"- 耗时: {result.duration_sec:.1f}s",
        "",
        "## 结果",
        f"- 原始请求: {result.captured_count}",
        f"- 解析记录: {result.parsed_count}",
        f"- 数据库: {result.db_path or task.db_path}",
        f"- 原始样本: {', '.join(result.raw_paths) or '无'}",
        f"- 下一步: {result.next_action or task.next_action_hint or '无'}",
        "",
        "## 人话总结",
    ]

    lines.extend(_render_human_summary(task, result))

    lines.extend([
        "",
        "## 来源统计",
    ])

    if result.source_counts:
        for source, count in sorted(result.source_counts.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {source}: {count}")
    else:
        lines.append("- 无")

    lines.extend([
        "",
        "## 类型统计",
    ])
    if result.note_type_counts:
        for note_type, count in sorted(result.note_type_counts.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {note_type}: {count}")
    else:
        lines.append("- 无")

    lines.extend([
        "",
        "## 步骤时间线",
    ])
    step_events = getattr(result, "step_events", []) or []
    if step_events:
        for event in step_events:
            detail = f" | {event.get('detail', '')}" if event.get("detail") else ""
            lines.append(f"- {event.get('at', '')} {event.get('name', '')}{detail}")
    else:
        lines.append("- 无")

    if result.error:
        lines.extend([
            "",
            "## 错误",
            result.error,
        ])

    if task.notes:
        lines.extend([
            "",
            "## 任务备注",
        ])
        lines.extend([f"- {note}" for note in task.notes])

    return "\n".join(lines).rstrip() + "\n"


def write_run_report(task: TaskSpec, result: RunResult, path: str | Path) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    report = render_run_report(task, result)
    path.write_text(report, encoding="utf-8")
    result.report_path = str(path)
    return report
