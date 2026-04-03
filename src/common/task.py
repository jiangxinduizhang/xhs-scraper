"""
公共任务契约 - 数据结构定义。

这一层只定义通用的数据结构，不包含任何 app-specific 的默认值或工厂方法。

【公共层边界 - 可以被所有 app 复用】
- TaskSpec 和 RunResult 的字段定义（通用化）
- 通用工具方法（save、load、to_dict、from_dict）

【通用化策略】
- 所有 app-specific 的默认值改为通用默认值（空字符串、空列表）
- package_name、launch_activity、db_path 等必须通过工厂方法或显式指定
- 不包含任何 app-specific 的预设或经验

【与 app adapter 的关系】
- app adapter 导入公共数据结构：from src.common.task import TaskSpec, RunResult
- app adapter 添加自己的工厂方法（如 for_preset、for_exploration）
- app adapter 通过 registry 或显式参数填充 app-specific 配置

【禁止的内容】
- 任何 app-specific 的默认值（如 app="kaipanla"、package_name="com.aiyu.kaipanla"）
- 任何 app-specific 的预设名称（如 preset="market_emotion"）
- 任何 app-specific 的工厂方法（如 for_preset、for_exploration）

如果 app adapter 需要添加工厂方法：
1. 在 app adapter 的 task.py 中导入公共数据结构
2. 定义自己的工厂方法，通过 registry 或显式参数填充配置
3. 不要改变公共层的定义
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import json


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass(slots=True)
class TaskSpec:
    """
    任务规格 - 描述"要做什么"。

    字段定义是通用的，可以用于任何 app。
    所有 app-specific 的配置必须通过工厂方法或显式参数填充。
    """

    schema_version: int = 1
    task_id: str = ""  # 必须由工厂方法或显式指定
    app: str = ""  # 必须由工厂方法或显式指定（不再默认为 "kaipanla"）
    mode: str = "registered"  # registered / exploration
    page: str = ""  # 必须由工厂方法或显式指定
    goal: str = ""
    preset: str = ""
    target_hint: str = ""
    success_criteria: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)
    output: list[str] = field(default_factory=list)
    compare: str = ""
    interpretation_style: str = ""
    package_name: str = ""  # 必须由工厂方法或显式指定
    launch_activity: str = ""  # 必须由工厂方法或显式指定
    db_path: str = ""  # 必须由工厂方法或显式指定
    raw_dir: str = "data/raw"  # 通用默认值
    runs_dir: str = "runs"  # 通用默认值
    reports_dir: str = "reports"  # 通用默认值
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


@dataclass(slots=True)
class RunResult:
    """
    执行结果 - 描述"做完以后长什么样"。

    字段定义是通用的，可以用于任何 app。
    所有 app-specific 的结果由具体 runner 填充。
    """

    schema_version: int = 1
    task_id: str = ""  # 必须由 runner 填充
    app: str = ""  # 必须由 runner 填充
    page: str = ""
    goal: str = ""
    status: str = "pending"  # pending / success / partial / failed
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