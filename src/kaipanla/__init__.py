"""
开盘啦迁移骨架。

这里放的是与小红书实现分离的 App 级元数据、验证清单和后续适配入口。
当前只保留最小占位，不承载具体抓取逻辑。
"""

from src.kaipanla.manifest import AppManifest, build_stub_manifest
from src.kaipanla.checklist import ValidationChecklist, build_first_round_checklist

__all__ = [
    "AppManifest",
    "ValidationChecklist",
    "build_first_round_checklist",
    "build_stub_manifest",
]
