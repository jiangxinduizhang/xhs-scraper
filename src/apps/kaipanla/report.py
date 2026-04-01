"""
开盘啦运行报告生成。
"""

from __future__ import annotations

from pathlib import Path

from src.apps.kaipanla.task import RunResult, TaskSpec


def _count(result: RunResult, key: str) -> int:
    return int((result.note_type_counts or {}).get(key, 0) or 0)


def build_market_summary(task: TaskSpec, result: RunResult) -> dict:
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

    active_modules = sum(1 for value in [msg_top, fkyd, baceface, jjxt, phb, zqfk, zlsc] if value > 0)
    if active_modules >= 5:
        completeness = "high"
        completeness_text = "市场情绪页主要模块都有数据，页面信息完整度较高，不像是空页或半残抓取。"
    elif active_modules >= 3:
        completeness = "medium"
        completeness_text = "市场情绪页拿到了多类模块数据，能做基础观察，但完整度还不是最强。"
    else:
        completeness = "low"
        completeness_text = "当前抓到的模块较少，更适合当作抓取校验，不适合下重结论。"

    if msg_top >= 8:
        signal_focus = "concentrated"
        signal_focus_text = "顶部/主展示类信息较活跃，说明页面重点信号输出比较集中，适合先看主叙事和强势方向。"
    elif msg_top >= 4:
        signal_focus = "balanced"
        signal_focus_text = "顶部主信息有一定活跃度，但还看不出特别极端的一致性。"
    else:
        signal_focus = "scattered"
        signal_focus_text = "顶部强提示信息不多，情绪信号可能偏分散。"

    modules: list[str] = []
    if fkyd > 0:
        modules.append("风口异动")
    if jjxt > 0:
        modules.append("资金/节奏类信号")
    if phb > 0:
        modules.append("排行类信号")
    if zqfk > 0:
        modules.append("赚钱效应反馈")
    if zlsc > 0:
        modules.append("主力市场/资金观察")
    if baceface > 0:
        modules.append("情绪面板")

    if unknown >= 10:
        parser_confidence = "medium"
        parser_confidence_text = "仍有一部分数据暂时落在 unknown，说明 parser 还有继续细分的空间；当前摘要可用，但不是最终形态。"
    elif unknown > 0:
        parser_confidence = "medium_high"
        parser_confidence_text = "有少量未归类数据，不影响总体回读，但后续还可以继续细化解析规则。"
    else:
        parser_confidence = "high"
        parser_confidence_text = "当前抓取结果已基本完成归类，适合进一步做更稳定的自动摘要。"

    weather_present = any(x > 0 for x in [weather_sz, weather_xd, summary])
    comment_present = plz > 0

    bullets: list[str] = []
    if result.status not in {"success", "partial"}:
        bullets.append("本次抓取未形成可稳定解读的市场摘要，请先检查抓取状态和错误信息。")
    else:
        bullets.append(completeness_text)
        bullets.append(signal_focus_text)
        if modules:
            bullets.append(f"这次可回读的重点模块包括：{'、'.join(modules)}。说明今天不只是单点行情，而是有横向观察维度。")
        if weather_present:
            bullets.append("页面里带有情绪总览/市场天气类信息，适合进一步升级成可直接阅读的人话日报。")
        if comment_present:
            bullets.append("还有舆情/评论区类补充信号，但目前占比不高，更适合作为辅助观察。")
        bullets.append(parser_confidence_text)
        bullets.append("就这次结果看，更适合下的结论是：页面抓取稳定、模块覆盖正常、具备继续做盘面摘要的基础；但要判断‘主线/分歧/修复强弱’，还需要把字段内容进一步翻译成人话。")

    return {
        "page": task.page,
        "status": result.status,
        "completeness": completeness,
        "signal_focus": signal_focus,
        "parser_confidence": parser_confidence,
        "weather_present": weather_present,
        "comment_present": comment_present,
        "active_modules": modules,
        "counts": {
            "captured_count": result.captured_count,
            "parsed_count": result.parsed_count,
            "msg_top": msg_top,
            "market_fkyd": fkyd,
            "market_baceface": baceface,
            "market_jjxt": jjxt,
            "market_phb": phb,
            "market_zqfk": zqfk,
            "market_zlsc": zlsc,
            "market_emotion_summary": summary,
            "market_plz": plz,
            "market_weather_sz": weather_sz,
            "market_weather_xd": weather_xd,
            "unknown": unknown,
        },
        "bullets": bullets,
    }


def _render_human_summary(task: TaskSpec, result: RunResult) -> list[str]:
    return [f"- {line}" for line in build_market_summary(task, result)["bullets"]]


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
