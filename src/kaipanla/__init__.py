"""
兼容层。

正式实现已迁移到 `src.apps.kaipanla`。
这里保留旧导入路径，避免已有引用失效。
"""

from src.apps.kaipanla.manifest import AppManifest, build_stub_manifest
from src.apps.kaipanla.checklist import ValidationChecklist, build_first_round_checklist
from src.apps.kaipanla.entry import render_action_plan, render_environment_check
from src.apps.kaipanla.task import RunResult, TaskSpec
from src.apps.kaipanla.runner import KaipanlaRunner, run_task
from src.apps.kaipanla.report import render_run_report
from src.apps.kaipanla.verify import VerificationResult, render_verification_summary, verify_run

__all__ = [
    "AppManifest",
    "ValidationChecklist",
    "TaskSpec",
    "RunResult",
    "VerificationResult",
    "KaipanlaRunner",
    "build_first_round_checklist",
    "render_action_plan",
    "render_environment_check",
    "render_run_report",
    "render_verification_summary",
    "verify_run",
    "run_task",
    "build_stub_manifest",
]
