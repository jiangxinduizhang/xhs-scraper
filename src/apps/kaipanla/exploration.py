"""
开盘啦 exploration evidence bundle 构建。

用于 assistant-directed exploration：
- 不要求先有正式注册页面
- 重点是产出可供 AI 判读的事实证据包
- runtime 不做页面语义识别、候选裁决或下一步策略判断
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.apps.kaipanla.task import RunResult


@dataclass(slots=True)
class ExplorationResult:
    task_id: str
    target_hint: str = ""
    round_index: int = 1
    max_rounds: int = 1
    evidence_status: str = "evidence_insufficient"
    observed_keys: list[str] = field(default_factory=list)
    navigation_events: list[str] = field(default_factory=list)
    raw_record_count: int = 0
    observed_paths: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)

    @property
    def status(self) -> str:
        return self.evidence_status

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.evidence_status
        return data


NOISE_KEYS = {
    "Ad_1", "Ad_2", "Ad_4", "Ad_5", "IndexAd", "errcode", "t", "time", "pathId", "publishId", "pathUrl", "revert", "new", "Index", "Mod", "ViewTop"
}


def _iter_raw_records(raw_paths: list[str] | None):
    for raw_path in raw_paths or []:
        path = Path(raw_path)
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
            if isinstance(data, dict):
                yield rec, data


def _value_shape(value) -> dict:
    if isinstance(value, list):
        sample = value[0] if value else None
        sample_type = type(sample).__name__ if sample is not None else "none"
        return {
            "kind": "list",
            "length": len(value),
            "field_count": 0,
            "sample_type": sample_type,
        }
    if isinstance(value, dict):
        return {
            "kind": "dict",
            "length": 0,
            "field_count": len(value),
            "sample_type": "dict",
        }
    return {
        "kind": type(value).__name__,
        "length": 0,
        "field_count": 0,
        "sample_type": type(value).__name__,
    }


def _record_fact(step_event: dict) -> dict:
    return {
        "name": step_event.get("name", ""),
        "detail": step_event.get("detail", ""),
        "timestamp": step_event.get("at", ""),
        "action": step_event.get("action", ""),
        "index": step_event.get("index"),
        "found": step_event.get("found"),
        "executed": step_event.get("executed"),
        "error": step_event.get("error", ""),
    }


def _action_finished_events(step_events: list[dict]) -> list[dict]:
    return [event for event in step_events if event.get("name") == "action_finished"]


def _texts(payload: dict | None) -> list[str]:
    if not isinstance(payload, dict):
        return []
    visible = payload.get("visible_text")
    if isinstance(visible, dict):
        return [str(item) for item in visible.get("texts", []) if str(item).strip()]
    return []


def _request_window_facts(raw_records: list[dict], action_events: list[dict]) -> dict[str, Any]:
    path_counts: Counter[str] = Counter()
    key_counter: Counter[str] = Counter()
    value_shapes: dict[str, dict] = {}
    sample_records: list[dict] = []

    for rec in raw_records:
        data = rec.get("data") if isinstance(rec, dict) else None
        if not isinstance(data, dict):
            continue
        path = str(rec.get("path") or "")
        keys = list(data.keys())
        if path:
            path_counts[path] += 1
        key_counter.update(keys)
        for key in keys:
            if key not in value_shapes:
                value_shapes[key] = _value_shape(data.get(key))
        if len(sample_records) < 8:
            sample_records.append({
                "ts": rec.get("ts", ""),
                "path": path,
                "keys": keys[:20],
                "day": data.get("Day", ""),
                "time": data.get("Time", ""),
            })

    action_windows = []
    for event in action_events:
        before = event.get("before") if isinstance(event.get("before"), dict) else {}
        after = event.get("after") if isinstance(event.get("after"), dict) else {}
        action_windows.append({
            "action_id": before.get("action_id") or after.get("action_id") or event.get("detail", ""),
            "action": event.get("action", ""),
            "before_at": before.get("captured_at", ""),
            "after_at": after.get("captured_at", ""),
        })

    return {
        "raw_record_count": len(raw_records),
        "observed_paths": [path for path, _ in path_counts.most_common(10)],
        "path_counts": dict(path_counts),
        "observed_keys": [key for key, _ in key_counter.most_common(20)],
        "key_counts": dict(key_counter),
        "value_shapes": value_shapes,
        "sample_records": sample_records,
        "action_windows": action_windows,
    }


def build_exploration_result(task_id: str, run: RunResult, target_hint: str) -> ExplorationResult:
    step_events = list(run.step_events or [])
    navigation_events = [event.get("name", "") for event in step_events if event.get("name")]
    action_events = _action_finished_events(step_events)

    raw_records = []
    for rec, data in _iter_raw_records(run.raw_paths):
        item = dict(rec)
        item["data"] = data
        raw_records.append(item)

    request_facts = _request_window_facts(raw_records, action_events)
    observed_keys = list(request_facts.get("observed_keys", []))
    observed_paths = list(request_facts.get("observed_paths", []))
    value_shapes = request_facts.get("value_shapes", {})
    key_counts = request_facts.get("key_counts", {})

    candidate_structures = []
    noise_structures = []
    for key in observed_keys[:16]:
        fact = {
            "name": key,
            "kind": value_shapes.get(key, {}).get("kind", "unknown"),
            "shape": value_shapes.get(key, {}),
            "count": key_counts.get(key, 0),
            "reason": "noise_key_match" if key in NOISE_KEYS else "observed_structure",
        }
        if key in NOISE_KEYS:
            noise_structures.append(fact)
        else:
            candidate_structures.append(fact)

    ui_pairs = []
    ui_changed_count = 0
    for event in action_events:
        before = event.get("before") if isinstance(event.get("before"), dict) else {}
        after = event.get("after") if isinstance(event.get("after"), dict) else {}
        before_texts = _texts(before)
        after_texts = _texts(after)
        added = [text for text in after_texts if text not in before_texts]
        removed = [text for text in before_texts if text not in after_texts]
        ui_changed = bool(added or removed)
        if ui_changed:
            ui_changed_count += 1
        ui_pairs.append({
            "action_id": before.get("action_id") or after.get("action_id") or event.get("detail", ""),
            "action": event.get("action", ""),
            "before": {
                "screenshot": (before.get("screenshot") or {}).get("path", "") if isinstance(before.get("screenshot"), dict) else "",
                "ui_dump": (before.get("ui_dump") or {}).get("path", "") if isinstance(before.get("ui_dump"), dict) else "",
                "visible_text": before_texts,
            },
            "after": {
                "screenshot": (after.get("screenshot") or {}).get("path", "") if isinstance(after.get("screenshot"), dict) else "",
                "ui_dump": (after.get("ui_dump") or {}).get("path", "") if isinstance(after.get("ui_dump"), dict) else "",
                "visible_text": after_texts,
            },
            "visible_text_diff": {
                "added": added[:20],
                "removed": removed[:20],
            },
            "ui_changed": ui_changed,
        })

    artifact_facts = {
        "captured_count": run.captured_count,
        "parsed_count": run.parsed_count,
        "raw_paths": list(run.raw_paths or []),
        "report_path": run.report_path,
        "db_path": run.db_path,
        "action_evidence_count": len((run.artifacts or {}).get("action_evidence", [])) if isinstance(run.artifacts, dict) else 0,
    }

    has_action_facts = bool(action_events)
    has_ui_facts = bool(ui_pairs)
    has_request_facts = request_facts.get("raw_record_count", 0) > 0
    has_structure_facts = bool(candidate_structures or noise_structures)
    has_artifact_facts = bool(artifact_facts.get("raw_paths") or artifact_facts.get("report_path") or artifact_facts.get("db_path"))

    complete_count = sum([has_action_facts, has_ui_facts, has_request_facts, has_structure_facts, has_artifact_facts])
    if complete_count >= 5:
        evidence_status = "evidence_complete"
    elif complete_count >= 3:
        evidence_status = "evidence_partial"
    else:
        evidence_status = "evidence_insufficient"

    return ExplorationResult(
        task_id=task_id,
        target_hint=target_hint,
        round_index=getattr(run, "round_index", 1) or 1,
        max_rounds=getattr(run, "max_rounds", 1) or 1,
        evidence_status=evidence_status,
        observed_keys=observed_keys,
        navigation_events=navigation_events,
        raw_record_count=request_facts.get("raw_record_count", 0),
        observed_paths=observed_paths,
        evidence={
            "action_facts": {
                "steps": [_record_fact(event) for event in step_events],
                "action_rounds": [_record_fact(event) for event in action_events],
                "navigation_events": navigation_events,
                "step_count": len(step_events),
            },
            "ui_facts": {
                "pairs": ui_pairs,
                "ui_changed_count": ui_changed_count,
                "ui_changed": ui_changed_count > 0,
            },
            "request_facts": request_facts,
            "structure_facts": {
                "observed_keys": observed_keys,
                "candidate_structures": candidate_structures,
                "noise_structures": noise_structures,
                "meta_keys": [key for key in observed_keys if key in {"Day", "Time", "code", "ttag"}],
            },
            "artifact_facts": artifact_facts,
        },
    )
