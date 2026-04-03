"""
开盘啦页面注册表。

这里保存的是执行模板，不是页面语义判断规则。

【APP-SPECIFIC 边界】
- PAGE_SPECS 中每个页面的 navigation_steps 都是开盘啦特有的 UI 操作序列
- notes 中的经验教训（如"避免前置 back"）是基于开盘啦实际失败样本总结的
- ALIASES 映射的是开盘啦特有的页面命名习惯
- 这些内容不应被泛化到其他 app（如开盘红），除非有明确的独立验证

【禁止跨 app 复用的内容】
- navigation_steps: 每个页面的具体 UI 操作路径
- UI 文本锚点: 如"龙虎榜"、"行情"、"情绪"等具体按钮/标签名称
- notes 中的经验教训: 基于 开盘啦 特定 UI 行为总结
- 页面结构假设: 如"首页 -> 行情 -> 情绪"这样的导航链
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
    notes: list[str] = field(default_factory=list)
    navigation_steps: list[dict] = field(default_factory=list)


def _task_id(prefix: str) -> str:
    return f"kpl-{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


PAGE_SPECS: dict[str, PageSpec] = {
    "market_emotion": PageSpec(
        name="market_emotion",
        goal="采集市场情绪页相关产物",
        modules=["emotion", "ranking", "money_flow", "themes"],
        output=["run", "report", "market_summary"],
        compare="previous_trading_day",
        interpretation_style="human_summary",
        notes=[
            "执行模板只负责完成页面动作和产物采集。",
            "页面语义解释与是否足够证明目标，由 AI 负责。",
        ],
        navigation_steps=[
            {"action": "back", "times": 3, "sleep": 0.8},
            {"action": "tap_text_or_fallback", "text": "首页", "timeout": 2},
            {"action": "record", "name": "entered_home_tab", "detail": "首页"},
            {"action": "sleep", "seconds": 1.0},
            {"action": "tap_text", "text": "行情", "timeout": 3},
            {"action": "record", "name": "entered_market_tab", "detail": "行情"},
            {"action": "sleep", "seconds": 2.0},
            {"action": "tap_text", "text": "情绪", "timeout": 3},
            {"action": "record", "name": "tap_emotion_tab", "detail": "情绪"},
            {"action": "sleep", "seconds": 2.0},
            {"action": "swipe_up", "times": 2, "sleep": 1.0},
        ],
    ),
    "market_radar": PageSpec(
        name="market_radar",
        goal="采集盘中雷达页相关产物",
        modules=["radar", "dongxiang"],
        output=["run", "report", "evidence_bundle"],
        compare="none",
        interpretation_style="evidence_bundle",
        notes=[
            "执行模板只负责页面动作与取证。",
            "不要把动作记录直接解释成页面已被语义确认。",
        ],
        navigation_steps=[
            {"action": "back", "times": 3, "sleep": 0.8},
            {"action": "tap_text_or_fallback", "text": "首页", "timeout": 2},
            {"action": "record", "name": "entered_home_tab", "detail": "首页"},
            {"action": "sleep", "seconds": 1.0},
            {"action": "tap_text", "text": "行情", "timeout": 3},
            {"action": "record", "name": "entered_market_tab", "detail": "行情"},
            {"action": "sleep", "seconds": 2.0},
            {"action": "tap_text", "text": "盘中雷达", "timeout": 3},
            {"action": "record", "name": "tap_radar_tab", "detail": "盘中雷达"},
            {"action": "sleep", "seconds": 2.0},
            {"action": "swipe_up", "times": 2, "sleep": 1.0},
        ],
    ),
    "market_featured": PageSpec(
        name="market_featured",
        goal="采集精选页相关产物",
        modules=["featured", "topic", "theme"],
        output=["run", "report", "evidence_bundle"],
        compare="none",
        interpretation_style="evidence_bundle",
        notes=[
            "执行模板只负责页面动作与取证。",
            "不要把动作记录直接解释成页面已被语义确认。",
        ],
        navigation_steps=[
            {"action": "back", "times": 3, "sleep": 0.8},
            {"action": "tap_text_or_fallback", "text": "首页", "timeout": 2},
            {"action": "record", "name": "entered_home_tab", "detail": "首页"},
            {"action": "sleep", "seconds": 1.0},
            {"action": "tap_text", "text": "行情", "timeout": 3},
            {"action": "record", "name": "entered_market_tab", "detail": "行情"},
            {"action": "sleep", "seconds": 2.0},
            {"action": "tap_text", "text": "精选", "timeout": 3},
            {"action": "record", "name": "tap_featured_tab", "detail": "精选"},
            {"action": "sleep", "seconds": 2.0},
            {"action": "swipe_up", "times": 2, "sleep": 1.0},
        ],
    ),
    "dragon_tiger": PageSpec(
        name="dragon_tiger",
        goal="采集龙虎榜页相关产物",
        modules=["dragon_tiger", "ranking"],
        output=["run", "report", "evidence_bundle"],
        compare="none",
        interpretation_style="evidence_bundle",
        notes=[
            "执行模板只负责页面动作与取证。",
            "动作记录不能直接当成已进入龙虎榜主块的证明。",
            "避免在前置导航阶段使用 back；近期失败样本显示 back 可能把应用直接退回 launcher。",
            "优先复用已验证最小路径：在首页稳定态直接点击底部/页面可见的 龙虎榜 入口。",
        ],
        navigation_steps=[
            {"action": "sleep", "seconds": 2.0},
            {"action": "tap_text", "text": "龙虎榜", "timeout": 3},
            {"action": "record", "name": "tap_dragon_tiger_tab", "detail": "龙虎榜"},
            {"action": "sleep", "seconds": 2.0},
        ],
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
    "dragon_tiger": "dragon_tiger",
    "龙虎榜": "dragon_tiger",
    "龙虎": "dragon_tiger",
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
        "notes": list(spec.notes),
    }
