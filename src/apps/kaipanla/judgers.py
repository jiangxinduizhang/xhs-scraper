from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.apps.kaipanla.exploration import ExplorationResult


HOME_FEED_HINTS = {
    "推荐文章",
    "首页",
    "复盘啦",
    "题材库",
    "快讯",
    "大盘直播",
    "ETF基金",
    "功能介绍",
    "商品现货",
    "风向标",
    "涨停板复盘",
}

DRAGON_TIGER_PAGE_HINTS = {
    "龙虎榜",
    "实时龙虎榜",
    "上榜",
    "龙虎",
}

DRAGON_TIGER_DATA_HINTS = {
    "买入额",
    "卖出额",
    "净买额",
    "上榜原因",
    "成交额",
    "换手率",
    "振幅",
    "收盘价",
    "代码",
    "股票名称",
}

INSTITUTION_HINTS = {
    "机构专用",
    "机构买入",
    "机构卖出",
    "净买入",
    "席位",
    "营业部",
    "买一",
    "卖一",
}

BROKER_HINTS = {
    "营业部",
    "证券营业部",
    "买入前五",
    "卖出前五",
    "席位",
}

BOTTOM_NAV_HINTS = {
    "首页&#10;Home",
    "行情&#10;Markets",
    "自选股&#10;Portfolio",
    "龙虎榜&#10;Charts",
    "推荐&#10;Recommend",
}

TOP_TITLE_HINTS = {
    "龙虎榜",
    "实时龙虎榜",
}


@dataclass(slots=True)
class Judgement:
    source: str
    label: str
    confidence: str
    reason: str
    matched_signals: list[str]
    missing_capability: str = ""
    user_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class JudgementBundle:
    primary: Judgement
    all: list[Judgement]

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary": self.primary.to_dict(),
            "all": [item.to_dict() for item in self.all],
        }


def _collect_visible_texts(result: ExplorationResult) -> list[str]:
    evidence = result.evidence or {}
    ui_facts = evidence.get("ui_facts") or {}
    pairs = ui_facts.get("pairs") or ui_facts.get("evidence_pairs") or []
    texts: list[str] = []
    for pair in pairs:
        for phase in ("before", "after"):
            payload = pair.get(phase) or {}
            values = payload.get("visible_text") or []
            texts.extend(str(v) for v in values if isinstance(v, (str, int, float)))
    return texts


def _contains_any(texts: list[str], needles: set[str]) -> list[str]:
    joined = "\n".join(texts)
    return sorted([needle for needle in needles if needle in joined])


def _count_hits(texts: list[str], needles: set[str]) -> int:
    return len(_contains_any(texts, needles))


def _has_bottom_nav_anchor(texts: list[str]) -> bool:
    return "龙虎榜&#10;Charts" in "\n".join(texts)


def _has_top_title_anchor(texts: list[str]) -> bool:
    joined = "\n".join(texts)
    home_hits = _contains_any(texts, HOME_FEED_HINTS)
    if home_hits:
        return False
    return "龙虎榜" in joined and ("首页&#10;Home" not in joined)


def judge_exploration(result: ExplorationResult) -> JudgementBundle:
    texts = _collect_visible_texts(result)
    evidence = result.evidence or {}
    request_facts = evidence.get("request_facts") or {}
    structure_facts = evidence.get("structure_facts") or {}
    raw_record_count = int(request_facts.get("raw_record_count") or 0)
    candidates = structure_facts.get("candidate_structures") or []
    observed_keys = [str(x) for x in (structure_facts.get("observed_keys") or [])]
    key_names = {str(item.get("name", "")) for item in candidates if isinstance(item, dict)}

    judgements: list[Judgement] = []

    bottom_nav_anchor = _has_bottom_nav_anchor(texts)
    top_title_anchor = _has_top_title_anchor(texts)
    anchor_signals = [
        signal
        for signal, ok in (
            ("bottom_nav龙虎榜", bottom_nav_anchor),
            ("top_title龙虎榜", top_title_anchor),
        )
        if ok
    ]

    home_hits = _contains_any(texts, HOME_FEED_HINTS)
    if home_hits and raw_record_count > 0:
        judgements.append(
            Judgement(
                source="code_judger",
                label="home_feed_dominant",
                confidence="high",
                reason="当前可见文本仍明显以首页/推荐流内容为主，说明很可能还停留在公共内容流或其邻近区域。",
                matched_signals=home_hits[:6],
                user_summary="当前证据仍更像首页/推荐流，不足以证明已经进入龙虎榜主块。",
            )
        )

    dragon_hits = _contains_any(texts, DRAGON_TIGER_PAGE_HINTS)
    dragon_key_hits = sorted([key for key in observed_keys if "dragon" in key.lower() or "tiger" in key.lower() or "longhu" in key.lower()])
    if dragon_hits or dragon_key_hits or anchor_signals:
        judgements.append(
            Judgement(
                source="code_judger",
                label="dragon_tiger_related_surface",
                confidence="medium",
                reason="证据里出现了龙虎榜相关文本、结构线索或页面锚点，但这只能说明接近目标区域，不能单独证明已命中核心数据块。",
                matched_signals=(anchor_signals + dragon_hits + dragon_key_hits)[:8],
                user_summary="已经出现龙虎榜相关线索，但还不能只凭这些线索宣称抓到目标主块。",
            )
        )

    dragon_data_hits = _contains_any(texts, DRAGON_TIGER_DATA_HINTS)
    dragon_text_hit_count = _count_hits(texts, DRAGON_TIGER_PAGE_HINTS | DRAGON_TIGER_DATA_HINTS)
    stock_key_hits = sorted([key for key in observed_keys if key in {"code", "name", "buy", "sell", "net", "amount"}])
    if bottom_nav_anchor and top_title_anchor and dragon_hits and dragon_data_hits and dragon_text_hit_count >= 3 and not home_hits:
        judgements.append(
            Judgement(
                source="code_judger",
                label="dragon_tiger_data_candidate",
                confidence="medium",
                reason="当前 UI 同时满足底部龙虎榜锚点、顶部标题锚点，以及龙虎榜数据字段词，且首页主流噪音不占主导，因此可以视为龙虎榜数据候选。",
                matched_signals=(anchor_signals + dragon_hits + dragon_data_hits + stock_key_hits)[:10],
                user_summary="当前 UI 已出现更像龙虎榜数据主块的线索，但仍建议再做一轮核实后再对外确认。",
            )
        )

    institution_hits = _contains_any(texts, INSTITUTION_HINTS)
    institution_key_hits = sorted([key for key in key_names if "seat" in key.lower() or "broker" in key.lower() or "institution" in key.lower()])
    if institution_hits and (dragon_hits or dragon_data_hits):
        judgements.append(
            Judgement(
                source="code_judger",
                label="institution_data_candidate",
                confidence="medium",
                reason="可见文本已出现机构/席位相关词，并且与龙虎榜页面/数据词同时出现，说明证据开始接近机构数据目标。",
                matched_signals=(institution_hits + institution_key_hits + dragon_hits)[:8],
                user_summary="已经看到一些更像龙虎榜机构/席位数据的线索，但还不能直接当成已稳定抓到。",
            )
        )

    page_entry_hits = _contains_any(texts, {"今日上榜数", "股票", "机构", "营业部", "股票名称"})
    if bottom_nav_anchor and page_entry_hits and any(text.isdigit() and len(text) == 6 for text in texts):
        judgements.append(
            Judgement(
                source="code_judger",
                label="dragon_tiger_page_reached",
                confidence="high",
                reason="已验证点击后 UI 从首页/推荐流切换为龙虎榜列表页，出现‘今日上榜数’、‘股票/机构/营业部’分栏、股票代码与股票名称等页面级线索。",
                matched_signals=(anchor_signals + page_entry_hits)[:10],
                user_summary="已成功进入龙虎榜页面，并拿到页面级榜单数据。",
            )
        )

    broker_hits = _contains_any(texts, BROKER_HINTS)
    if broker_hits and (dragon_hits or dragon_data_hits):
        judgements.append(
            Judgement(
                source="code_judger",
                label="broker_data_candidate",
                confidence="medium",
                reason="可见文本已出现营业部/席位相关词，并且与龙虎榜页面/数据词同时出现，说明证据开始接近营业部数据目标。",
                matched_signals=(broker_hits + dragon_hits + dragon_data_hits)[:8],
                user_summary="已经看到一些更像龙虎榜营业部/席位数据的线索，但还不能直接当成已稳定抓到。",
            )
        )

    if not judgements:
        judgements.append(
            Judgement(
                source="code_judger",
                label="judger_insufficient",
                confidence="low",
                reason="现有初始化判定器尚不足以稳定解释当前证据，仍需 exploration 继续收集或 ask-human。",
                matched_signals=[f"raw_record_count={raw_record_count}", f"candidate_structures={len(candidates)}"],
                missing_capability="需要通过后续 exploration + 人类确认沉淀新的任务判定器。",
                user_summary="当前还没有足够稳定的代码级判定器来解释这批证据，建议继续探索或由人类确认目标。",
            )
        )

    priority = {
        "dragon_tiger_page_reached": 7,
        "institution_data_candidate": 6,
        "broker_data_candidate": 5,
        "dragon_tiger_data_candidate": 4,
        "dragon_tiger_related_surface": 3,
        "home_feed_dominant": 2,
        "judger_insufficient": 1,
    }
    primary = max(judgements, key=lambda item: priority.get(item.label, 0))
    return JudgementBundle(primary=primary, all=judgements)
