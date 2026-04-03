"""
开盘红适配包。

当前先提供最小 adapter 落点，避免继续把第二个 app 混进开盘啦专属目录。
执行层暂时复用现有 runner/契约，后续再逐步拆分 app-specific 实现。
"""

from src.apps.kaipanla.manifest import AppManifest
from src.apps.kaipanhong.task import RunResult, TaskSpec
from src.apps.kaipanhong.exploration import ExplorationResult, build_exploration_result
from src.apps.kaipanhong.judgers import Judgement, JudgementBundle, judge_exploration
from src.apps.kaipanhong.manifest import build_stub_manifest
from src.apps.kaipanhong.pages import PageSpec, build_task_defaults, get_page_spec, list_pages
from src.apps.kaipanhong.report import build_page_summary, render_run_report, write_run_report
from src.apps.kaipanhong.verify import VerificationResult, render_verification_summary, verify_run

__all__ = [
    "AppManifest",
    "TaskSpec",
    "RunResult",
    "ExplorationResult",
    "Judgement",
    "JudgementBundle",
    "PageSpec",
    "VerificationResult",
    "build_exploration_result",
    "build_page_summary",
    "build_stub_manifest",
    "build_task_defaults",
    "get_page_spec",
    "judge_exploration",
    "list_pages",
    "render_run_report",
    "render_verification_summary",
    "verify_run",
    "write_run_report",
]
