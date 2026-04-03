"""
开盘红适配包。

当前先提供最小 adapter 落点，避免继续把第二个 app 混进开盘啦专属目录。
执行层暂时复用现有 runner/契约，后续再逐步拆分 app-specific 实现。
"""

from src.apps.kaipanla.manifest import AppManifest
from src.apps.kaipanhong.manifest import build_stub_manifest
from src.apps.kaipanhong.pages import PageSpec, build_task_defaults, get_page_spec, list_pages

__all__ = [
    "AppManifest",
    "PageSpec",
    "build_stub_manifest",
    "build_task_defaults",
    "get_page_spec",
    "list_pages",
]
