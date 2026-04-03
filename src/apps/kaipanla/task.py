"""
开盘啦任务契约。

这一层只定义“要做什么”和“做完以后长什么样”，不包含具体执行逻辑。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import json

from src.apps.registry import build_app_task_defaults, get_app_spec


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass(slots=True)
class TaskSpec:
    schema_version: int = 1
    task_id: str = ""
    app: str = "kaipanla"
    mode: str = "registered"
    page: str = "market_emotion"
    goal: str = ""
    preset: str = "market_emotion"
    target_hint: str = ""
    success_criteria: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)
    output: list[str] = field(default_factory=list)
    compare: str = "previous_trading_day"
    interpretation_style: str = "trader_recap"
    package_name: str = "com.aiyu.kaipanla"
    launch_activity: str = ".splash.SplashActivity"
    db_path: str = "data/kaipanla.db"
    raw_dir: str = "data/raw"
    runs_dir: str = "runs"
    reports_dir: str = "reports"
    timeout_sec: int = 1800
    max_attempts: int = 1
    next_action_hint: str = ""
    notes: list[str] = field(default_factory=list)
    round_index: int = 1
    max_rounds: int = 1
    session_id: str = ""
    action_plan: list[dict[str, Any]] = field(default_factory=list)
    capture_options: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "TaskSpec":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "TaskSpec":
        known = {field.name for field in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    @classmethod
    def market_emotion_default(cls, app: str | None = None) -> "TaskSpec":
        return cls.for_preset("market_emotion", app=app)

    @classmethod
    def for_preset(cls, preset: str | None, *, app: str | None = None) -> "TaskSpec":
        app_spec = get_app_spec(app)
        defaults = build_app_task_defaults(app_spec.app_id, preset)
        defaults.setdefault("app", app_spec.app_id)
        defaults.setdefault("package_name", app_spec.package_name)
        defaults.setdefault("launch_activity", app_spec.launch_activity)
        defaults.setdefault("db_path", app_spec.db_path)
        defaults.setdefault("mode", "registered")
        defaults.setdefault("success_criteria", ["artifacts_complete"])
        return cls(**defaults)

    @classmethod
    def for_exploration(
        cls,
        target_hint: str,
        *,
        page: str | None = None,
        preset: str | None = None,
        navigation_hint: str = "",
        app: str | None = None,
    ) -> "TaskSpec":
        app_spec = get_app_spec(app)
        chosen_page = page or preset or "market_emotion"
        base = build_app_task_defaults(app_spec.app_id, chosen_page)
        base.setdefault("app", app_spec.app_id)
        base.setdefault("package_name", app_spec.package_name)
        base.setdefault("launch_activity", app_spec.launch_activity)
        base.setdefault("db_path", app_spec.db_path)
        base.update(
            {
                "mode": "exploration",
                "page": chosen_page,
                "preset": preset or chosen_page,
                "goal": f"探索抓取目标：{target_hint}",
                "target_hint": target_hint,
                "success_criteria": [
                    "collect_evidence_bundle",
                    "persist_exploration_artifacts",
                ],
                "output": ["run", "report", "evidence_bundle"],
                "interpretation_style": "evidence_bundle",
                "round_index": 1,
                "max_rounds": 1,
                "session_id": "",
                "action_plan": [],
                "capture_options": {
                    "screenshot_before_after": True,
                    "ui_dump_before_after": True,
                    "visible_text_before_after": True,
                    "focus_post_action_window": True,
                },
                "notes": list(base.get("notes", [])) + [
                    f"探索目标: {target_hint}",
                    f"navigation_hint: {navigation_hint}" if navigation_hint else "navigation_hint: <none>",
                    "runtime_role: execution_only",
                ],
                "next_action_hint": "由 AI 基于 evidence bundle 决定下一步动作",
            }
        )
        return cls(**base)


@dataclass(slots=True)
class RunResult:
    schema_version: int = 1
    task_id: str = ""
    app: str = "kaipanla"
    page: str = ""
    goal: str = ""
    status: str = "pending"
    started_at: str = field(default_factory=_now_iso)
    finished_at: str = ""
    duration_sec: float = 0.0
    raw_paths: list[str] = field(default_factory=list)
    db_path: str = ""
    captured_count: int = 0
    parsed_count: int = 0
    source_counts: dict[str, int] = field(default_factory=dict)
    note_type_counts: dict[str, int] = field(default_factory=dict)
    step_events: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    next_action: str = ""
    report_path: str = ""
    round_index: int = 1
    max_rounds: int = 1
    session_id: str = ""
    artifacts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "RunResult":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "RunResult":
        known = {field.name for field in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)
