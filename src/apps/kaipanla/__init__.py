"""
开盘啦适配包。

这是 `开盘啦` 的正式适配落点。
旧的 `src.kaipanla` 仅作为兼容层保留。
"""

from src.apps.kaipanla.manifest import AppManifest, build_stub_manifest
from src.apps.kaipanla.checklist import ValidationChecklist, build_first_round_checklist
from src.apps.kaipanla.entry import build_report, render_action_plan, render_environment_check
from src.apps.kaipanla.task import RunResult, TaskSpec
from src.apps.kaipanla.runner import KaipanlaRunner, run_task
from src.apps.kaipanla.report import render_run_report
from src.apps.kaipanla.verify import VerificationResult, render_verification_summary, verify_run
from src.apps.kaipanla.pages import (
    PageSpec,
    get_page_spec,
    list_pages,
    build_task_defaults,
    normalize_page_name,
)

__all__ = [
    "AppManifest",
    "ValidationChecklist",
    "TaskSpec",
    "RunResult",
    "VerificationResult",
    "PageSpec",
    "KaipanlaRunner",
    "build_first_round_checklist",
    "build_report",
    "render_action_plan",
    "render_environment_check",
    "render_run_report",
    "render_verification_summary",
    "verify_run",
    "run_task",
    "build_stub_manifest",
    "get_page_spec",
    "list_pages",
    "build_task_defaults",
    "normalize_page_name",
]