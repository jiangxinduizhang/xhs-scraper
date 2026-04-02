"""
开盘啦页面注册表。

把“页面定义 / 导航步骤 / 验真关键字段”从 runner 和 verify 中拆出来，
支持任意已注册真实页面走统一任务框架。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class PageSpec:
    name: str
    goal: str
    modules: list[str] = field(default_factory=list)
    output: list[str] = field(default_factory=list)
    compare: str = "none"
    interpretation_style: str = "human_summary"
    next_action_hint: str = ""
    notes: list[str] = field(default_factory=list)
    navigation_steps: list[dict] = field(default_factory=list)
    expected_keys: list[str] = field(default_factory=list)
    required_events: list[str] = field(default_factory=list)


def _task_id(prefix: str) -> str:
    return f"kpl-{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


PAGE_SPECS: dict[str, PageSpec] = {
    "market_emotion": PageSpec(
        name="market_emotion",
        goal="验证市场情绪页可稳定抓取并落库",
        modules=["emotion", "ranking", "money_flow", "themes"],
        output=["run", "report", "market_summary", "day_compare"],
        compare="previous_trading_day",
        interpretation_style="trader_recap",
        next_action_hint="继续抓行情页其他标签",
        notes=[
            "当前默认预设任务是 market_emotion。",
            "先保持最小闭环，不扩展多页面任务。",
            "若抓取成功，优先输出可回读产物，再决定下一步。",
        ],
        navigation_steps=[
            {"action": "back", "times": 3, "sleep": 0.8},
            {"action": "tap_text_or_fallback", "text": "首页", "timeout": 2},
            {"action": "record", "name": "home_reached", "detail": "首页"},
            {"action": "sleep", "seconds": 1.0},
            {"action": "tap_text", "text": "行情", "timeout": 3},
            {"action": "record", "name": "market_reached", "detail": "行情"},
            {"action": "sleep", "seconds": 2.0},
            {"action": "tap_text", "text": "情绪", "timeout": 3},
            {"action": "record", "name": "emotion_reached", "detail": "情绪"},
            {"action": "sleep", "seconds": 2.0},
            {"action": "swipe_up", "times": 2, "sleep": 1.0},
        ],
        expected_keys=["DaBanList", "BaceFaceList", "PHBList", "JJXTList", "ZQFKList"],
        required_events=["launch_app", "home_reached", "market_reached", "emotion_reached", "request_captured", "report_written", "run_written"],
    ),
    "market_radar": PageSpec(
        name="market_radar",
        goal="抓取行情 tab 页面盘中雷达数据并落盘",
        modules=["radar", "dongxiang"],
        output=["run", "report", "page_summary"],
        compare="none",
        interpretation_style="human_summary",
        next_action_hint="继续观察盘中雷达是否有新增信号",
        notes=[
            "盘中雷达页以 DongXiang 类字段作为主要验真锚点。",
            "若页面存在滚动加载，可适当增加 swipe。",
        ],
        navigation_steps=[
            {"action": "back", "times": 3, "sleep": 0.8},
            {"action": "tap_text_or_fallback", "text": "首页", "timeout": 2},
            {"action": "record", "name": "home_reached", "detail": "首页"},
            {"action": "sleep", "seconds": 1.0},
            {"action": "tap_text", "text": "行情", "timeout": 3},
            {"action": "record", "name": "market_reached", "detail": "行情"},
            {"action": "sleep", "seconds": 2.0},
            {"action": "tap_text", "text": "盘中雷达", "timeout": 3},
            {"action": "record", "name": "radar_reached", "detail": "盘中雷达"},
            {"action": "sleep", "seconds": 2.0},
            {"action": "swipe_up", "times": 2, "sleep": 1.0},
        ],
        expected_keys=["DongXiang"],
        required_events=["launch_app", "home_reached", "market_reached", "radar_reached", "request_captured", "report_written", "run_written"],
    ),
    "market_featured": PageSpec(
        name="market_featured",
        goal="抓取行情 tab 页面精选数据并落盘",
        modules=["featured", "topic", "theme"],
        output=["run", "report", "page_summary"],
        compare="none",
        interpretation_style="human_summary",
        next_action_hint="继续观察精选主题是否切换",
        notes=[
            "精选页以 Topic / Theme / List 类字段作为主要验真锚点。",
            "如果页面分模块切换明显，后续可继续细拆为子页面。",
        ],
        navigation_steps=[
            {"action": "back", "times": 3, "sleep": 0.8},
            {"action": "tap_text_or_fallback", "text": "首页", "timeout": 2},
            {"action": "record", "name": "home_reached", "detail": "首页"},
            {"action": "sleep", "seconds": 1.0},
            {"action": "tap_text", "text": "行情", "timeout": 3},
            {"action": "record", "name": "market_reached", "detail": "行情"},
            {"action": "sleep", "seconds": 2.0},
            {"action": "tap_text", "text": "精选", "timeout": 3},
            {"action": "record", "name": "featured_reached", "detail": "精选"},
            {"action": "sleep", "seconds": 2.0},
            {"action": "swipe_up", "times": 2, "sleep": 1.0},
        ],
        expected_keys=["Topic", "Theme", "List"],
        required_events=["launch_app", "home_reached", "market_reached", "featured_reached", "request_captured", "report_written", "run_written"],
    ),
}


ALIASES = {
    "default": "market_emotion",
    "latest_market": "market_emotion",
    "emotion": "market_emotion",
    "market": "market_emotion",
    "radar": "market_radar",
    "market_radar": "market_radar",
    "盘中雷达": "market_radar",
    "featured": "market_featured",
    "market_featured": "market_featured",
    "精选": "market_featured",
}


def normalize_page_name(name: str | None) -> str:
    value = (name or "market_emotion").strip()
    return ALIASES.get(value, ALIASES.get(value.lower(), value.lower()))


def get_page_spec(name: str | None) -> PageSpec:
    normalized = normalize_page_name(name)
    if normalized not in PAGE_SPECS:
        raise ValueError(f"unsupported page/preset: {name}")
    return PAGE_SPECS[normalized]


def list_pages() -> list[str]:
    return sorted(PAGE_SPECS.keys())


def build_task_defaults(name: str | None) -> dict:
    spec = get_page_spec(name)
    return {
        "task_id": _task_id(spec.name.replace('_', '-')),
        "page": spec.name,
        "preset": spec.name,
        "goal": spec.goal,
        "modules": list(spec.modules),
        "output": list(spec.output),
        "compare": spec.compare,
        "interpretation_style": spec.interpretation_style,
        "next_action_hint": spec.next_action_hint,
        "notes": list(spec.notes),
    }
