"""
开盘啦运行结果校验。

只检查产物和落库事实，不重新执行抓取。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from src.storage.db import Database
from src.apps.kaipanla.task import RunResult, TaskSpec


@dataclass(slots=True)
class VerificationResult:
    task_id: str
    status: str
    checks: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)


def _find_latest_daban_snapshot(raw_paths: list[str] | None) -> dict:
    best_data: dict = {}
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
            if not isinstance(data, dict) or not isinstance(data.get("DaBanList"), dict):
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
    return best_data


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

    db_path = Path(result.db_path or task.db_path)
    if db_path.exists():
        checks.append("数据库文件存在")
        db = Database(str(db_path))
        total_notes = db.conn.execute(
            "SELECT count(*) FROM notes WHERE source=?",
            ("market_sentiment",),
        ).fetchone()[0]
        details.append(f"market_sentiment 记录数: {total_notes}")
        if total_notes <= 0:
            ok = False
    else:
        checks.append("数据库文件不存在")
        ok = False

    error_code = None
    error_stage = None
    if isinstance(result.source_counts, dict):
        error_code = result.source_counts.get("error_code")
        error_stage = result.source_counts.get("error_stage")

    if result.status not in ("success", "partial"):
        ok = False
        details.append(f"run.status={result.status}")
        if error_code:
            details.append(f"error_code={error_code}")
        if error_stage:
            details.append(f"error_stage={error_stage}")

    latest_snapshot = _find_latest_daban_snapshot(result.raw_paths)
    latest_daban = latest_snapshot.get("DaBanList") if isinstance(latest_snapshot, dict) else {}
    required_main_fields = ["ZHQD", "SZJS", "XDJS", "PPJS", "tZhangTing", "tDieTing", "tFengBan", "qscln"]
    missing_main_fields = [field for field in required_main_fields if not latest_daban or latest_daban.get(field) in (None, "")]
    if missing_main_fields:
        ok = False
        details.append(f"主值字段缺失: {', '.join(missing_main_fields)}")
    else:
        details.append(
            "最新主值快照: "
            f"ZHQD={latest_daban.get('ZHQD')} "
            f"SZJS={latest_daban.get('SZJS')} "
            f"XDJS={latest_daban.get('XDJS')} "
            f"PPJS={latest_daban.get('PPJS')} "
            f"tZhangTing={latest_daban.get('tZhangTing')} "
            f"tDieTing={latest_daban.get('tDieTing')} "
            f"tFengBan={latest_daban.get('tFengBan')} "
            f"qscln={latest_daban.get('qscln')}"
        )

    required_events = {"launch_app", "home_reached", "market_reached", "emotion_reached", "request_captured", "report_written", "run_written"}
    seen_events = {event.get("name", "") for event in getattr(result, "step_events", []) or []}
    missing_events = sorted(required_events - seen_events)
    if missing_events:
        ok = False
        details.append(f"缺少步骤: {', '.join(missing_events)}")
    else:
        details.append("步骤时间线完整")

    return VerificationResult(
        task_id=result.task_id or task.task_id,
        status="verified" if ok else "needs_attention",
        checks=checks,
        details=details,
    )


def render_verification_summary(verification: VerificationResult) -> str:
    lines = [
        f"任务: {verification.task_id}",
        f"状态: {verification.status}",
        "",
        "检查项:",
    ]
    lines.extend([f"- {check}" for check in verification.checks] or ["- 无"])
    if verification.details:
        lines.extend(["", "细节:"])
        lines.extend([f"- {item}" for item in verification.details])
    return "\n".join(lines).rstrip() + "\n"
