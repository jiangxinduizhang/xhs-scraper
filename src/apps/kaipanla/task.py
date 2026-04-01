"""
开盘啦任务契约。

这一层只定义“要做什么”和“做完以后长什么样”，不包含具体执行逻辑。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
import json


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass(slots=True)
class TaskSpec:
    schema_version: int = 1
    task_id: str = ""
    app: str = "kaipanla"
    page: str = "market_emotion"
    goal: str = ""
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
        task_id = f"kpl-market-emotion-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        return cls(
            task_id=task_id,
            goal="验证市场情绪页可稳定抓取并落库",
            next_action_hint="继续抓行情页其他标签",
            notes=[
                "先保持最小闭环，不扩展多页面任务。",
                "若抓取成功，优先输出可回读产物，再决定下一步。",
            ],
        )


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
