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
}

DRAGON_TIGER_PAGE_HINTS = {
    "龙虎榜",
    "实时龙虎榜",
    "上榜",
}

INSTITUTION_HINTS = {
    "机构专用",
    "机构买入",
    "机构卖出",
    "净买入",
    "席位",
    "营业部",
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
    pairs = ui_facts.get("evidence_pairs") or []
    texts: list[str] = []
    for pair in pairs:
        for phase in ("before", "after"):
            payload = (pair.get(phase) or {}).get("visible_text") or {}
            values = payload.get("texts") or []
            texts.extend(str(v) for v in values if isinstance(v, (str, int, float)))
    return texts


def _contains_any(texts: list[str], needles: set[str]) -> list[str]:
    joined = "\n".join(texts)
    return sorted([needle for needle in needles if needle in joined])


def judge_exploration(result: ExplorationResult) -> JudgementBundle:
    texts = _collect_visible_texts(result)
    evidence = result.evidence or {}
    request_facts = evidence.get("request_facts") or {}
    structure_facts = evidence.get("structure_facts") or {}
    raw_record_count = int(request_facts.get("raw_record_count") or 0)
    candidates = structure_facts.get("candidate_structures") or []

    judgements: list[Judgement] = []

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
    if dragon_hits:
        judgements.append(
            Judgement(
                source="code_judger",
                label="dragon_tiger_related_surface",
                confidence="medium",
                reason="证据里出现了龙虎榜相关文本，但这只能说明接近目标区域，不能单独证明已命中核心数据块。",
                matched_signals=dragon_hits[:6],
                user_summary="已经出现龙虎榜相关线索，但还不能只凭这些线索宣称抓到目标主块。",
            )
        )

    institution_hits = _contains_any(texts, INSTITUTION_HINTS)
    if institution_hits:
        judgements.append(
            Judgement(
                source="code_judger",
                label="institution_data_candidate",
                confidence="medium",
                reason="可见文本已出现机构/席位相关词，说明当前证据开始接近机构数据目标。",
                matched_signals=institution_hits[:6],
                user_summary="已经看到一些机构/席位相关线索，可以优先验证是否进入机构数据区域。",
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

    primary = judgements[0]
    priority = {
        "institution_data_candidate": 4,
        "dragon_tiger_related_surface": 3,
        "home_feed_dominant": 2,
        "judger_insufficient": 1,
    }
    primary = max(judgements, key=lambda item: priority.get(item.label, 0))
    return JudgementBundle(primary=primary, all=judgements)
