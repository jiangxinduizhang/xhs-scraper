"""
开盘啦运行结果校验。

只检查产物和落库事实，不重新执行抓取。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from src.storage.db import Database
from src.apps.kaipanla.exploration import build_exploration_result
from src.apps.kaipanla.pages import get_page_spec
from src.apps.kaipanla.task import RunResult, TaskSpec


@dataclass(slots=True)
class VerificationResult:
    task_id: str
    status: str
    checks: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    selected_snapshot: dict = field(default_factory=dict)
    flags: dict = field(default_factory=dict)


def _find_latest_record_with_keys(raw_paths: list[str] | None, expected_keys: list[str] | None) -> tuple[dict, dict]:
    expected = list(expected_keys or [])
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
            if expected and not any(key in data for key in expected):
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
    selected_snapshot = {
        "raw_ts": str(best_rec.get("ts") or "") if isinstance(best_rec, dict) else "",
        "day": str(best_data.get("Day") or "") if isinstance(best_data, dict) else "",
        "time": str(best_data.get("Time") or "") if isinstance(best_data, dict) else "",
        "phb_title": str(best_data.get("PHBTitle") or best_data.get("PHBtitle") or "") if isinstance(best_data, dict) else "",
        "reason": "latest_valid_record_by_expected_keys_then_time_then_raw_ts",
        "source": ",".join(expected) if expected else "generic",
    } if best_data else {}
    return best_data, selected_snapshot


def _find_latest_daban_snapshot(raw_paths: list[str] | None) -> tuple[dict, dict]:
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
                best_rec = rec
    selected_snapshot = {
        "raw_ts": str(best_rec.get("ts") or "") if isinstance(best_rec, dict) else "",
        "day": str(best_data.get("Day") or "") if isinstance(best_data, dict) else "",
        "time": str(best_data.get("Time") or "") if isinstance(best_data, dict) else "",
        "phb_title": str(best_data.get("PHBTitle") or best_data.get("PHBtitle") or "") if isinstance(best_data, dict) else "",
        "reason": "latest_valid_daban_snapshot_by_time_then_raw_ts",
        "source": "DaBanList",
    } if best_data else {}
    return best_data, selected_snapshot


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
    if getattr(task, "mode", "registered") == "exploration":
        exploration = build_exploration_result(task.task_id or result.task_id, result, task.target_hint or task.goal)
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

        details.append(f"exploration.status={exploration.status}")
        details.append(f"candidate_keys={', '.join(exploration.candidate_keys) or '无'}")
        details.append(f"matched_records={exploration.matched_records}")
        details.append(f"navigation_reached={', '.join(exploration.navigation_reached) or '无'}")
        details.append(f"recommendation={exploration.recommendation}")

        status = "verified" if ok and exploration.status in {"candidate_found", "ready_to_promote"} else "needs_attention"
        return VerificationResult(
            task_id=result.task_id or task.task_id,
            status=status,
            checks=checks,
            details=details,
            selected_snapshot={
                "target_hint": task.target_hint,
                "candidate_keys": exploration.candidate_keys,
                "recommended_page_name": exploration.recommended_page_name,
            },
            flags={
                "exploration_mode": True,
                "candidate_found": bool(exploration.candidate_keys),
                "ready_to_promote": exploration.status == "ready_to_promote",
                "run_succeeded": result.status in ("success", "partial"),
            },
        )

    page_spec = get_page_spec(task.page)

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

    latest_snapshot, selected_snapshot = _find_latest_record_with_keys(result.raw_paths, page_spec.expected_keys)
    missing_main_fields: list[str] = []
    if task.page == "market_emotion":
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
    else:
        if not latest_snapshot:
            ok = False
            details.append(f"未找到页面关键字段: {', '.join(page_spec.expected_keys)}")
        else:
            details.append(f"页面关键字段命中: {', '.join([key for key in page_spec.expected_keys if key in latest_snapshot])}")

    if selected_snapshot:
        details.append(
            "selected_snapshot: "
            f"raw_ts={selected_snapshot.get('raw_ts', '')} "
            f"day={selected_snapshot.get('day', '')} "
            f"time={selected_snapshot.get('time', '')} "
            f"phb_title={selected_snapshot.get('phb_title', '')} "
            f"reason={selected_snapshot.get('reason', '')}"
        )

    required_events = set(page_spec.required_events)
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
        selected_snapshot=selected_snapshot,
        flags={
            "selected_snapshot_is_latest": bool(selected_snapshot),
            "required_main_fields_complete": not missing_main_fields,
            "run_succeeded": result.status in ("success", "partial"),
        },
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
