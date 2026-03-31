"""
开盘啦适配包。

这是 `开盘啦` 的正式适配落点。
旧的 `src.kaipanla` 仅作为兼容层保留。
"""

from src.apps.kaipanla.manifest import AppManifest, build_stub_manifest
from src.apps.kaipanla.checklist import ValidationChecklist, build_first_round_checklist
from src.apps.kaipanla.entry import build_report

__all__ = [
    "AppManifest",
    "ValidationChecklist",
    "build_first_round_checklist",
    "build_report",
    "build_stub_manifest",
]
