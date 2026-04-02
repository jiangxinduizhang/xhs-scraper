"""
开盘啦运行报告生成。

报告用于回读执行事实与证据，不承担页面语义裁决职责。
"""

from __future__ import annotations

import json
from pathlib import Path

from src.apps.kaipanla.exploration import build_exploration_result
from src.apps.kaipanla.task import RunResult, TaskSpec


def build_page_summary(task: TaskSpec, result: RunResult) -> dict:
    if getattr(task, "mode", "registered") == "exploration":
        exploration = build_exploration_result(task.task_id, result, task.target_hint or task.goal)
        return {
            "mode": "exploration",
            "page": task.page,
            "status": exploration.evidence_status,
            "bullets": [
                f"探索目标：{task.target_hint or task.goal}",
                f"证据状态：{exploration.evidence_status}",
                f"观测到的 key：{', '.join(exploration.observed_keys[:12]) or '无'}",
                f"观测到的 path：{', '.join(exploration.observed_paths) or '无'}",
                f"导航事件：{', '.join(exploration.navigation_events) or '无'}",
                f"raw 记录数：{exploration.raw_record_count}",
            ],
            "exploration": exploration.to_dict(),
        }

    latest_keys = []
    latest_day = ""
    latest_time = ""
    for raw_path in result.raw_paths or []:
        path = Path(raw_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            continue
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            continue
        try:
            rec = json.loads(lines[-1])
        except json.JSONDecodeError:
            continue
        data = rec.get("data")
        if isinstance(data, dict):
            latest_keys = list(data.keys())[:20]
            latest_day = str(data.get("Day") or "")
            latest_time = str(data.get("Time") or "")

    return {
        "mode": "registered",
        "page": task.page,
        "status": result.status,
        "bullets": [
            f"任务目标：{task.goal or '无'}",
            f"执行状态：{result.status}",
            f"原始请求数：{result.captured_count}",
            f"解析记录数：{result.parsed_count}",
            f"最新 raw 日期：{latest_day or '无'}",
            f"最新 raw 时间：{latest_time or '无'}",
            f"最新 raw key 预览：{', '.join(latest_keys) or '无'}",
        ],
    }


def render_run_report(task: TaskSpec, result: RunResult) -> str:
    lines = [
        f"# {task.task_id}",
        "",
        "## 概览",
        f"- 应用: {task.app}",
        f"- 页面: {task.page}",
        f"- 目标: {task.goal or task.target_hint or '无'}",
        f"- 状态: {result.status}",
        f"- 开始: {result.started_at}",
        f"- 结束: {result.finished_at or '进行中'}",
        f"- 耗时: {result.duration_sec:.1f}s",
        "",
        "## 产物",
        f"- 原始请求: {result.captured_count}",
        f"- 解析记录: {result.parsed_count}",
        f"- 数据库: {result.db_path or task.db_path}",
        f"- 原始样本: {', '.join(result.raw_paths) or '无'}",
        f"- report_path: {result.report_path or '无'}",
        "",
    ]

    if getattr(task, "mode", "registered") == "exploration":
        exploration = build_exploration_result(task.task_id or result.task_id, result, task.target_hint or task.goal)
        lines.extend([
            "## Exploration Evidence",
            f"- 证据状态: {exploration.evidence_status}",
            f"- 导航事件: {', '.join(exploration.navigation_events) or '无'}",
            f"- 观测到的 key: {', '.join(exploration.observed_keys[:12]) or '无'}",
            f"- 观测到的 path: {', '.join(exploration.observed_paths) or '无'}",
            f"- raw 记录数: {exploration.raw_record_count}",
            "",
            "## 说明",
            "- 这是事实证据包，不代表 bridge 已确认目标页面语义或主块。",
            "- 下一步解释、继续、停止、ask-human，应由 AI 决定。",
            "",
            "## Evidence Bundle",
            "```json",
            json.dumps(exploration.to_dict(), ensure_ascii=False, indent=2),
            "```",
            "",
        ])
    else:
        summary = build_page_summary(task, result)
        lines.extend([
            "## 执行摘要",
            *[f"- {line}" for line in summary.get("bullets", [])],
            "",
            "## 说明",
            "- 本报告展示的是执行与产物事实。",
            "- 是否足以证明已到目标页主块或已稳定抓到目标数据，应由 AI 结合证据判断。",
            "",
        ])

    lines.extend([
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
