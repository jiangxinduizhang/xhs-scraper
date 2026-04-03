"""
开盘红页面注册表。

当前先维持与开盘啦同构的 page API，作为第二个 app 的独立落点。
注意：这不代表页面路径已验证等同，只代表工程结构已允许 app-specific 分化。

【临时复用说明】
- 当前复用开盘啦的 PAGE_SPECS（同名页面键）
- 这只是工程过渡期的临时方案
- 未来开盘红应：
  1. 建立独立的 PAGE_SPECS（基于开盘红 UI 特征）
  2. 编写独立的 navigation_steps（基于开盘红实际路径）
  3. 总结独立的经验教训（写入 notes）
  4. 不应长期依赖开盘啦的页面定义

【APP-SPECIFIC 边界】
- 即使当前复用开盘啦页面键，也应通过此 adapter 入口调用
- 不应在其他模块直接 import 开盘啦的 pages
- 保持 adapter 边界清晰，为未来独立演化做准备

【禁止的内容】
- 直接复用开盘啦的 navigation_steps（应有开盘红独立路径）
- 直接复用开盘啦的 notes（应有开盘红独立经验教训）
- 假设开盘红 UI 文本与开盘啦完全相同

【特别警告】
- 开盘啦的页面经验是基于开盘啦 UI 总结的
- 如"避免前置 back"是基于开盘啦曾出现"退回 launcher"的问题
- 开盘红 UI 可能不同，不应直接复用这些经验
- 当前复用只是为了让工程结构先跑起来，不代表验证通过
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
