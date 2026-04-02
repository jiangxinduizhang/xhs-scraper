"""
开盘啦任务契约。

这一层只定义“要做什么”和“做完以后长什么样”，不包含具体执行逻辑。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
import json

from src.apps.kaipanla.pages import build_task_defaults


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
    def market_emotion_default(cls) -> "TaskSpec":
        return cls.for_preset("market_emotion")

    @classmethod
    def for_preset(cls, preset: str | None) -> "TaskSpec":
        defaults = build_task_defaults(preset)
        defaults.setdefault("mode", "registered")
        defaults.setdefault("success_criteria", ["verify=verified"])
        return cls(**defaults)

    @classmethod
    def for_exploration(
        cls,
        target_hint: str,
        *,
        page: str | None = None,
        preset: str | None = None,
        navigation_hint: str = "",
    ) -> "TaskSpec":
        chosen_page = page or preset or "market_emotion"
        base = build_task_defaults(chosen_page)
        base.update(
            {
                "mode": "exploration",
                "page": chosen_page,
                "preset": preset or chosen_page,
                "goal": f"探索抓取目标：{target_hint}",
                "target_hint": target_hint,
                "success_criteria": [
                    "find_candidate_keys",
                    "produce_exploration_summary",
                ],
                "output": ["run", "report", "exploration_summary"],
                "interpretation_style": "exploration",
                "notes": list(base.get("notes", [])) + [
                    f"探索目标: {target_hint}",
                    f"navigation_hint: {navigation_hint}" if navigation_hint else "navigation_hint: <none>",
                ],
                "next_action_hint": "根据 exploration_summary 判断是否沉淀为 registered page",
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
    step_events: list[dict[str, str]] = field(default_factory=list)
    error: str = ""
    next_action: str = ""
    report_path: str = ""

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
