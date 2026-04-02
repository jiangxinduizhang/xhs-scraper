"""
开盘啦运行结果校验。

只检查产物和证据完整性，不做页面语义判断。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from src.storage.db import Database
from src.apps.kaipanla.exploration import build_exploration_result
from src.apps.kaipanla.task import RunResult, TaskSpec


@dataclass(slots=True)
class VerificationResult:
    task_id: str
    status: str
    checks: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    selected_snapshot: dict = field(default_factory=dict)
    flags: dict = field(default_factory=dict)


def _latest_raw_snapshot(raw_paths: list[str] | None) -> dict:
    best_data: dict = {}
    best_rec: dict = {}
    best_time = -1
    best_ts = ""
    for raw in raw_paths or []:
        path = Path(raw)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            data = rec.get("data")
            if not isinstance(data, dict):
                continue
            try:
                current_time = int(data.get("Time") or 0)
            except (TypeError, ValueError):
                current_time = 0
            current_ts = str(rec.get("ts") or "")
            if current_time > best_time or (current_time == best_time and current_ts > best_ts):
                best_time = current_time
                best_ts = current_ts
                best_data = data
                best_rec = rec
    if not best_data:
        return {}
    return {
        "raw_ts": str(best_rec.get("ts") or ""),
        "day": str(best_data.get("Day") or ""),
        "time": str(best_data.get("Time") or ""),
        "keys": list(best_data.keys())[:20],
        "reason": "latest_raw_record_by_time_then_raw_ts",
    }


def verify_run(run_path: str | Path, task_path: str | Path | None = None) -> VerificationResult:
    run_path = Path(run_path)
    if not run_path.exists():
        return VerificationResult(task_id=run_path.stem, status="missing", checks=["run.json 不存在"])

    result = RunResult.load(run_path)
    if task_path:
        task = TaskSpec.load(task_path)
    else:
        auto_task_path = run_path.with_suffix(".task.json")
        task = TaskSpec.load(auto_task_path) if auto_task_path.exists() else TaskSpec.market_emotion_default()

    checks: list[str] = []
    details: list[str] = []
    ok = True

    report_path = Path(result.report_path or Path(task.reports_dir) / f"{task.task_id}.md")
    if report_path.exists():
        checks.append("report.md 已生成")
    else:
        checks.append("report.md 不存在")
        ok = False

    task_file = run_path.with_suffix(".task.json")
    if task_file.exists():
        checks.append("task.json 已生成")
    else:
        checks.append("task.json 不存在")
        ok = False

    raw_ok = any(Path(raw).exists() for raw in result.raw_paths) if result.raw_paths else False
    if raw_ok:
        checks.append("raw 样本已生成")
    else:
        checks.append("raw 样本缺失")
        ok = False

    steps_ok = bool(result.step_events)
    if steps_ok:
        checks.append("step_events 已记录")
    else:
        checks.append("step_events 缺失")
        ok = False

    latest_snapshot = _latest_raw_snapshot(result.raw_paths)
    if latest_snapshot:
        details.append(f"latest_raw.day={latest_snapshot.get('day', '')}")
        details.append(f"latest_raw.time={latest_snapshot.get('time', '')}")
        details.append(f"latest_raw.keys={', '.join(latest_snapshot.get('keys', [])) or '无'}")

    db_path = Path(result.db_path or task.db_path)
    db_exists = db_path.exists()
    if db_exists:
        checks.append("数据库文件存在")
        try:
            db = Database(str(db_path))
            total_notes = db.conn.execute("SELECT count(*) FROM notes").fetchone()[0]
            details.append(f"db.note_count={total_notes}")
        except Exception as exc:
            details.append(f"db.read_error={type(exc).__name__}: {exc}")
    else:
        checks.append("数据库文件不存在")

    if getattr(task, "mode", "registered") == "exploration":
        exploration = build_exploration_result(task.task_id or result.task_id, result, task.target_hint or task.goal)
        details.append(f"exploration.evidence_status={exploration.evidence_status}")
        details.append(f"observed_keys={', '.join(exploration.observed_keys[:12]) or '无'}")
        details.append(f"raw_record_count={exploration.raw_record_count}")
        details.append(f"navigation_events={', '.join(exploration.navigation_events) or '无'}")

        status = "evidence_complete" if ok and exploration.evidence_status == "evidence_complete" else ("evidence_partial" if ok else "evidence_insufficient")
        return VerificationResult(
            task_id=result.task_id or task.task_id,
            status=status,
            checks=checks,
            details=details,
            selected_snapshot={
                "target_hint": task.target_hint,
                "observed_keys": exploration.observed_keys[:12],
                "observed_paths": exploration.observed_paths,
                "navigation_events": exploration.navigation_events,
                "latest_raw": latest_snapshot,
            },
            flags={
                "exploration_mode": True,
                "has_observed_keys": bool(exploration.observed_keys),
                "evidence_complete": exploration.evidence_status == "evidence_complete",
                "run_succeeded": result.status in ("success", "partial"),
            },
        )

    if result.status not in ("success", "partial"):
        ok = False
        details.append(f"run.status={result.status}")

    status = "artifacts_complete" if ok else "artifacts_partial"
    return VerificationResult(
        task_id=result.task_id or task.task_id,
        status=status,
        checks=checks,
        details=details,
        selected_snapshot=latest_snapshot,
        flags={
            "step_events_present": steps_ok,
            "db_exists": db_exists,
            "raw_exists": raw_ok,
            "report_exists": report_path.exists(),
            "run_succeeded": result.status in ("success", "partial"),
        },
    )


def render_verification_summary(v: VerificationResult) -> str:
    lines = [f"# Verification {v.task_id}", "", f"Status: {v.status}", ""]
    if v.checks:
        lines.append("## Checks")
        lines.extend(f"- {item}" for item in v.checks)
        lines.append("")
    if v.details:
        lines.append("## Details")
        lines.extend(f"- {item}" for item in v.details)
        lines.append("")
    if v.selected_snapshot:
        lines.append("## Selected Snapshot")
        lines.append("```json")
        lines.append(json.dumps(v.selected_snapshot, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)
