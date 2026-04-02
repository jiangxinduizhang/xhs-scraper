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

from src.apps.kaipanla.task import RunResult


@dataclass(slots=True)
class ExplorationResult:
    task_id: str
    target_hint: str = ""
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
    }


def build_exploration_result(task_id: str, run: RunResult, target_hint: str) -> ExplorationResult:
    key_counter: Counter[str] = Counter()
    path_counter: Counter[str] = Counter()
    pre_nav_counter: Counter[str] = Counter()
    post_nav_counter: Counter[str] = Counter()
    value_shapes: dict[str, dict] = {}
    examples: list[dict] = []

    navigation_events = [
        event.get("name", "")
        for event in (run.step_events or [])
        if event.get("name")
    ]
    reached_index = next(
        (idx for idx, name in enumerate(navigation_events) if name.endswith("_reached")),
        None,
    )

    raw_record_count = 0
    for rec, data in _iter_raw_records(run.raw_paths):
        raw_record_count += 1
        keys = list(data.keys())
        path = str(rec.get("path") or "")
        path_counter[path] += 1
        key_counter.update(keys)

        is_post_nav_record = bool(reached_index is not None and any(name.endswith("_reached") for name in navigation_events))
        for key in keys:
            if is_post_nav_record:
                post_nav_counter[key] += 1
            else:
                pre_nav_counter[key] += 1
            if key not in value_shapes:
                value_shapes[key] = _value_shape(data.get(key))

        if len(examples) < 5:
            examples.append(
                {
                    "ts": rec.get("ts", ""),
                    "path": path,
                    "keys": keys[:20],
                    "day": data.get("Day", ""),
                    "time": data.get("Time", ""),
                }
            )

    observed_keys = [key for key, _ in key_counter.most_common(20)]
    observed_paths = [path for path, _ in path_counter.most_common(10) if path]

    candidate_structures = []
    for key in observed_keys[:12]:
        candidate_structures.append(
            {
                "name": key,
                "kind": value_shapes.get(key, {}).get("kind", "unknown"),
                "shape": value_shapes.get(key, {}),
                "count": key_counter.get(key, 0),
                "pre_navigation_hits": pre_nav_counter.get(key, 0),
                "post_navigation_hits": post_nav_counter.get(key, 0),
                "post_navigation_only": pre_nav_counter.get(key, 0) == 0 and post_nav_counter.get(key, 0) > 0,
            }
        )

    meta_keys = [key for key in observed_keys if key in {"Day", "Time", "code", "ttag"}]
    noise_keys = [key for key in observed_keys if key in NOISE_KEYS]

    raw_ok = raw_record_count > 0
    steps_ok = bool(run.step_events)
    evidence_status = "evidence_complete" if raw_ok and steps_ok else ("evidence_partial" if raw_ok or steps_ok else "evidence_insufficient")

    return ExplorationResult(
        task_id=task_id,
        target_hint=target_hint,
        evidence_status=evidence_status,
        observed_keys=observed_keys,
        navigation_events=navigation_events,
        raw_record_count=raw_record_count,
        observed_paths=observed_paths,
        evidence={
            "action_facts": {
                "steps": [_record_fact(event) for event in (run.step_events or [])],
                "navigation_events": navigation_events,
                "step_count": len(run.step_events or []),
            },
            "ui_facts": {
                "screenshot_before": "",
                "screenshot_after": "",
                "ui_dump_before": "",
                "ui_dump_after": "",
                "ui_changed": False,
                "visible_text_before": [],
                "visible_text_after": [],
            },
            "request_facts": {
                "raw_record_count": raw_record_count,
                "observed_paths": observed_paths,
                "path_counts": dict(path_counter),
                "pre_navigation_counts": dict(pre_nav_counter),
                "post_navigation_counts": dict(post_nav_counter),
                "sample_records": examples,
            },
            "structure_facts": {
                "observed_keys": observed_keys,
                "candidate_structures": candidate_structures,
                "meta_keys": meta_keys,
                "noise_keys": noise_keys,
            },
            "artifact_facts": {
                "captured_count": run.captured_count,
                "parsed_count": run.parsed_count,
                "raw_paths": list(run.raw_paths or []),
                "report_path": run.report_path,
                "db_path": run.db_path,
            },
        },
    )
