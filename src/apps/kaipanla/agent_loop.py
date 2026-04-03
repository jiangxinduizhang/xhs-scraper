"""AI-facing minimal exploration loop helpers.

这一层不替代 OpenClaw 本体，也不让 runtime 自己做业务判断。
它只提供一个最小、可测试的“自然语言目标 -> exploration round plan -> round decision”封装，
用于支撑 Round2 的最小可试用闭环。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from src.apps.kaipanla.exploration import ExplorationResult
from src.apps.kaipanla.judgers import JudgementBundle, judge_exploration
from src.apps.kaipanla.pages import normalize_page_name


@dataclass(slots=True)
class LoopPlan:
    mode: str
    target_hint: str
    preset: str
    reason: str
    round_index: int
    max_rounds: int
    navigation_hint: str
    action_plan: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LoopDecision:
    decision: str
    reason: str
    next_round_index: int | None = None
    next_navigation_hint: str = ""
    next_action_plan: list[dict[str, Any]] | None = None
    user_message: str = ""
    judgement: dict[str, Any] | None = None
    judgement_source: str = ""
    confidence: str = ""
    missing_capability: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


TARGET_PAGE_HINTS = {
    "龙虎榜": "dragon_tiger",
    "龙虎": "dragon_tiger",
    "情绪": "market_emotion",
    "盘中雷达": "market_radar",
    "精选": "market_featured",
}


def infer_exploration_preset(user_text: str) -> tuple[str, str]:
    text = (user_text or "").strip()
    for needle, preset in TARGET_PAGE_HINTS.items():
        if needle in text:
            return preset, needle
    return normalize_page_name("market_emotion"), text or "市场情绪"


def build_round1_plan(user_text: str, *, max_rounds: int = 2) -> LoopPlan:
    preset, target_hint = infer_exploration_preset(user_text)
    return LoopPlan(
        mode="exploration",
        target_hint=target_hint,
        preset=preset,
        reason="用户意图包含未知/待验证页面目标，先走 exploration 收集证据",
        round_index=1,
        max_rounds=max(1, int(max_rounds or 2)),
        navigation_hint="优先验证目标入口点击后是否出现新的 UI/请求证据",
        action_plan=[],
    )


def decide_next_step(result: ExplorationResult) -> LoopDecision:
    evidence = result.evidence or {}
    ui_facts = evidence.get("ui_facts") or {}
    request_facts = evidence.get("request_facts") or {}
    structure_facts = evidence.get("structure_facts") or {}

    ui_changed = bool(ui_facts.get("ui_changed"))
    raw_record_count = int(request_facts.get("raw_record_count") or 0)
    candidate_count = len(structure_facts.get("candidate_structures") or [])
    noise_count = len(structure_facts.get("noise_structures") or [])
    current_round = max(1, int(getattr(result, "round_index", 1) or 1))
    max_rounds = max(1, int(getattr(result, "max_rounds", 1) or 1))
    judgement_bundle: JudgementBundle = judge_exploration(result)
    primary = judgement_bundle.primary
    judgement_dict = judgement_bundle.to_dict()
    all_signals: set[str] = set()
    for item in judgement_bundle.all:
        all_signals.update(item.matched_signals or [])
    has_bottom_anchor = "bottom_nav龙虎榜" in all_signals
    has_top_anchor = "top_title龙虎榜" in all_signals

    if result.evidence_status == "evidence_insufficient":
        return LoopDecision(
            decision="ask_human",
            reason="当前证据不足，继续探索容易变成碰运气",
            user_message="这轮拿到的证据太弱，继续下去更像碰运气。你是要严格确认龙虎榜主块，还是先接受相关候选证据？",
            judgement=judgement_dict,
            judgement_source=primary.source,
            confidence=primary.confidence,
            missing_capability=primary.missing_capability,
        )

    if primary.label in {"dragon_tiger_page_reached", "market_emotion_page_reached"}:
        return LoopDecision(
            decision="stop",
            reason="已验证进入目标页面，当前可停止并对外返回页面级结果",
            user_message=primary.user_summary or "已成功进入目标页面，并拿到页面级数据。",
            judgement=judgement_dict,
            judgement_source=primary.source,
            confidence=primary.confidence,
            missing_capability=primary.missing_capability,
        )

    if current_round >= max_rounds:
        return LoopDecision(
            decision="stop",
            reason="已到当前轮次上限，必须停止并对外解释当前证据强度",
            user_message=primary.user_summary or "我已经按当前上限完成探索。动作执行和证据已收集，但还不能仅凭这些确认目标主块已经命中。",
            judgement=judgement_dict,
            judgement_source=primary.source,
            confidence=primary.confidence,
            missing_capability=primary.missing_capability,
        )

    if primary.label in {"dragon_tiger_related_surface", "home_feed_dominant"} and (not has_bottom_anchor or not has_top_anchor):
        return LoopDecision(
            decision="continue",
            reason="当前仍缺少龙虎榜顶部标题/底部锚点中的至少一个，先做一轮最小补充取证来确认页面是否真正切换。",
            next_round_index=current_round + 1,
            next_navigation_hint="优先确认底部龙虎榜入口是否处于激活态，并验证顶部是否出现龙虎榜标题",
            next_action_plan=[
                {"action": "sleep", "seconds": 2},
                {"action": "tap_text", "target": "龙虎榜"},
                {"action": "sleep", "seconds": 2},
            ],
            judgement=judgement_dict,
            judgement_source=primary.source,
            confidence=primary.confidence,
            missing_capability=primary.missing_capability,
        )

    if primary.label in {"market_emotion_related_surface", "home_feed_dominant"} and "市场情绪" in (getattr(result, "target_hint", "") or ""):
        return LoopDecision(
            decision="continue",
            reason="当前需要直接验证首页顶部‘市场情绪’入口是否能切到市场情绪页。",
            next_round_index=current_round + 1,
            next_navigation_hint="优先点击首页顶部市场情绪入口，并确认是否出现量能/涨跌家数/涨跌停等市场情绪页指标",
            next_action_plan=[
                {"action": "sleep", "seconds": 2},
                {"action": "tap_text", "target": "市场情绪"},
                {"action": "sleep", "seconds": 2},
            ],
            judgement=judgement_dict,
            judgement_source=primary.source,
            confidence=primary.confidence,
            missing_capability=primary.missing_capability,
        )

    if primary.label in {"institution_data_candidate", "broker_data_candidate", "dragon_tiger_data_candidate", "dragon_tiger_related_surface", "home_feed_dominant"} and ui_changed and raw_record_count > 0 and candidate_count > max(0, noise_count):
        return LoopDecision(
            decision="continue",
            reason=f"当前代码级判定结果为 {primary.label}，且本轮存在一定增信，可以继续一轮最小动作缩小不确定性",
            next_round_index=current_round + 1,
            next_navigation_hint="基于上一轮证据，优先验证目标入口后的主块是否真正刷新",
            next_action_plan=[
                {"action": "sleep", "seconds": 2},
                {"action": "swipe_up", "times": 1},
            ],
            judgement=judgement_dict,
            judgement_source=primary.source,
            confidence=primary.confidence,
            missing_capability=primary.missing_capability,
        )

    return LoopDecision(
        decision="ask_human",
        reason="当前没有足够增信理由进入下一轮自动探索",
        user_message=primary.user_summary or "我已经拿到一轮证据，但增信还不够，下一轮如果继续会更依赖猜测。你要我继续做一次最小补充探索，还是先按当前证据给你结论？",
        judgement=judgement_dict,
        judgement_source=primary.source,
        confidence=primary.confidence,
        missing_capability=primary.missing_capability,
    )
