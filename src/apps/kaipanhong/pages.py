"""
开盘红页面注册表。

当前先维持与开盘啦同构的 page API，作为第二个 app 的独立落点。
注意：这不代表页面路径已验证等同，只代表工程结构已允许 app-specific 分化。
"""

from __future__ import annotations

from src.apps.kaipanla.pages import PageSpec, normalize_page_name


# 第一刀先复用同名页面键，后续由开盘红自己维护 app-specific 页面模板。
from src.apps.kaipanla.pages import PAGE_SPECS as KAIPANLA_PAGE_SPECS

PAGE_SPECS: dict[str, PageSpec] = dict(KAIPANLA_PAGE_SPECS)


def get_page_spec(name: str | None) -> PageSpec:
    normalized = normalize_page_name(name)
    if normalized not in PAGE_SPECS:
        raise ValueError(f"unsupported page/preset for kaipanhong: {name}")
    return PAGE_SPECS[normalized]


def list_pages() -> list[str]:
    return sorted(PAGE_SPECS.keys())


def build_task_defaults(name: str | None) -> dict:
    spec = get_page_spec(name)
    task_id = f"kph-{spec.name.replace('_', '-') }"
    from datetime import datetime

    return {
        "task_id": f"{task_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "page": spec.name,
        "preset": spec.name,
        "goal": spec.goal,
        "modules": list(spec.modules),
        "output": list(spec.output),
        "compare": spec.compare,
        "interpretation_style": spec.interpretation_style,
        "notes": list(spec.notes) + ["app_adapter: kaipanhong"],
    }
