"""
开盘啦运行报告生成。

报告用于回读执行事实与证据，不承担页面语义裁决职责。

【APP-SPECIFIC 边界】
- 直接 import 开盘啦特有的 build_exploration_result
- build_page_summary 在 exploration mode 下调用 build_exploration_result
- render_run_report 在 exploration mode 下调用 build_exploration_result

【依赖关系】
- report.py 依赖开盘啦特有的 exploration 模块
- 如果其他 app（如开盘红）需要类似 report，应：
  1. 建立独立的 report 模块
  2. import 自己的 exploration 模块
  3. 使用自己的 evidence bundle 构建逻辑

【禁止跨 app 复用的内容】
- 对 build_exploration_result 的直接依赖
- 对 exploration 模块的假设

当前开盘红 adapter 的 report.py 是复用此实现，但：
- 这只是临时方案
- 未来开盘红应建立独立的 report 实现
- 不应长期依赖开盘啦的 exploration 模块

【可复用的部分】
- render_run_report 的骨架结构（Markdown 格式）
- write_run_report 的文件写入逻辑
- 但需要替换 exploration 相关的依赖
"""

from __future__ import annotations

import json
from pathlib import Path

from src.apps.kaipanla.exploration import build_exploration_result
from src.apps.kaipanla.task import RunResult, TaskSpec


def build_page_summary(task: TaskSpec, result: RunResult) -> dict:
    if getattr(task, "mode", "registered") == "exploration":
        exploration = build_exploration_result(task.task_id, result, task.target_hint or task.goal)
        ui_facts = exploration.evidence.get("ui_facts", {}) if isinstance(exploration.evidence, dict) else {}
        request_facts = exploration.evidence.get("request_facts", {}) if isinstance(exploration.evidence, dict) else {}
        structure_facts = exploration.evidence.get("structure_facts", {}) if isinstance(exploration.evidence, dict) else {}
        return {
            "mode": "exploration",
            "page": task.page,
            "status": exploration.evidence_status,
            "bullets": [
                f"探索目标：{task.target_hint or task.goal}",
                f"证据状态：{exploration.evidence_status}",
                f"轮次：{exploration.round_index}/{exploration.max_rounds}",
                f"UI 证据对数：{len(ui_facts.get('pairs', []))}",
                f"UI 是否有变化：{'是' if ui_facts.get('ui_changed') else '否'}",
                f"请求记录数：{request_facts.get('raw_record_count', 0)}",
                f"候选结构数：{len(structure_facts.get('candidate_structures', []))}",
                f"噪声结构数：{len(structure_facts.get('noise_structures', []))}",
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
        action_facts = exploration.evidence.get("action_facts", {}) if isinstance(exploration.evidence, dict) else {}
        ui_facts = exploration.evidence.get("ui_facts", {}) if isinstance(exploration.evidence, dict) else {}
        request_facts = exploration.evidence.get("request_facts", {}) if isinstance(exploration.evidence, dict) else {}
        structure_facts = exploration.evidence.get("structure_facts", {}) if isinstance(exploration.evidence, dict) else {}
        lines.extend([
            "## Exploration Probe Report",
            f"- 证据状态: {exploration.evidence_status}",
            f"- 轮次: {exploration.round_index}/{exploration.max_rounds}",
            f"- 动作事实数: {len(action_facts.get('action_rounds', []))}",
            f"- UI 证据对数: {len(ui_facts.get('pairs', []))}",
            f"- UI 是否变化: {'是' if ui_facts.get('ui_changed') else '否'}",
            f"- 请求记录数: {request_facts.get('raw_record_count', 0)}",
            f"- 候选结构数: {len(structure_facts.get('candidate_structures', []))}",
            f"- 噪声结构数: {len(structure_facts.get('noise_structures', []))}",
            "",
            "## 当前不确定性",
            "- 本报告只陈述动作、UI、请求、结构与产物事实。",
            "- 不能据此直接宣称已进入目标主块或已稳定抓到目标数据。",
            "- 是否继续、停止、ask-human，应由 AI 基于证据判断。",
            "",
            "## Evidence Bundle v2",
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
