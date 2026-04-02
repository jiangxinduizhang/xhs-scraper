"""
开盘啦探索模式支持。

用于 assistant-directed exploration：
- 不要求先有正式注册页面
- 重点是产生候选页面证据、候选关键字段和探索建议
- 这里做的是“候选证据构建器”，不是最终裁判
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from src.apps.kaipanla.task import RunResult


@dataclass(slots=True)
class ExplorationResult:
    task_id: str
    target_hint: str = ""
    status: str = "pending"
    candidate_keys: list[str] = field(default_factory=list)
    matched_records: int = 0
    navigation_reached: list[str] = field(default_factory=list)
    likely_noise_keys: list[str] = field(default_factory=list)
    recommendation: str = ""
    recommended_page_name: str = ""
    evidence: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


TARGET_SIGNAL_HINTS = {
    "dragon_tiger": {
        "aliases": ["龙虎榜", "龙虎", "dragon_tiger", "dragon tiger"],
        "positive_keys": ["LongHuBang", "DragonTigerList", "DragonTiger", "LongHu", "List"],
        "negative_keys": ["DaBanList", "CWeatherVaneList", "BaceFaceList", "MsgTop", "TCop"],
        "navigation_events": ["dragon_tiger_reached"],
        "recommended_page_name": "dragon_tiger",
    },
    "market_radar": {
        "aliases": ["盘中雷达", "雷达", "market_radar"],
        "positive_keys": ["DongXiang"],
        "negative_keys": ["DaBanList", "BaceFaceList", "MsgTop", "TCop"],
        "navigation_events": ["radar_reached"],
        "recommended_page_name": "market_radar",
    },
    "market_featured": {
        "aliases": ["精选", "market_featured", "featured"],
        "positive_keys": ["Topic", "Theme", "List"],
        "negative_keys": ["DaBanList", "DongXiang", "MsgTop", "TCop"],
        "navigation_events": ["featured_reached"],
        "recommended_page_name": "market_featured",
    },
    "market_emotion": {
        "aliases": ["情绪", "market_emotion", "emotion"],
        "positive_keys": ["DaBanList", "BaceFaceList", "CWeatherVaneList", "PHBList", "JJXTList"],
        "negative_keys": ["LongHuBang", "DragonTigerList", "DongXiang", "MsgTop", "TCop"],
        "navigation_events": ["emotion_reached"],
        "recommended_page_name": "market_emotion",
    },
}

NOISE_KEYS = {
    "Ad_1", "Ad_2", "Ad_4", "Ad_5", "IndexAd", "errcode", "t", "time", "pathId", "publishId", "pathUrl", "revert", "new", "Index", "Mod", "ViewTop"
}


def _iter_raw_records(raw_paths: list[str] | None):
    for raw_path in raw_paths or []:
        path = Path(raw_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            data = rec.get("data")
            if isinstance(data, dict):
                yield rec, data


def _resolve_target_profile(target_hint: str) -> tuple[str, dict]:
    text = (target_hint or "").strip().lower()
    for name, profile in TARGET_SIGNAL_HINTS.items():
        aliases = [alias.lower() for alias in profile.get("aliases", [])]
        if any(alias and alias in text for alias in aliases):
            return name, profile
    return "generic", {
        "aliases": [text],
        "positive_keys": [],
        "negative_keys": [],
        "navigation_events": [],
        "recommended_page_name": "",
    }


def _value_shape(value) -> dict:
    if isinstance(value, list):
        sample = value[0] if value else None
        sample_type = type(sample).__name__ if sample is not None else "none"
        return {
            "kind": "list",
            "length": len(value),
            "field_count": 0,
            "sample_type": sample_type,
        }
    if isinstance(value, dict):
        return {
            "kind": "dict",
            "length": 0,
            "field_count": len(value),
            "sample_type": "dict",
        }
    return {
        "kind": type(value).__name__,
        "length": 0,
        "field_count": 0,
        "sample_type": type(value).__name__,
    }


def _noise_category(key: str, profile: dict) -> str:
    if key in NOISE_KEYS:
        return "meta_or_noise"
    if key in profile.get("negative_keys", []):
        return "known_non_target_block"
    if key in {"MsgTop", "TCop", "IndexAd", "ViewTop"}:
        return "common_or_ad_block"
    if key in {"Day", "Time", "code", "ttag"}:
        return "time_or_context"
    return "weak_related"


def _score_key(
    key: str,
    count: int,
    profile: dict,
    navigation_reached: list[str],
    post_nav_hits: int,
    pre_nav_hits: int,
    value_shapes: dict,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    lowered = key.lower()

    if key in profile.get("positive_keys", []):
        score += 6
        reasons.append("positive_key_exact")
    elif any(token.lower() in lowered for token in profile.get("positive_keys", []) if token):
        score += 4
        reasons.append("positive_key_partial")

    if key in profile.get("negative_keys", []):
        score -= 5
        reasons.append("negative_key")

    if key in NOISE_KEYS:
        score -= 4
        reasons.append("known_noise")

    if count >= 3:
        score += 2
        reasons.append("repeated")
    elif count >= 1:
        score += 1
        reasons.append("seen")

    if key.endswith("List"):
        score += 1
        reasons.append("list_shape")

    if any(event in navigation_reached for event in profile.get("navigation_events", [])):
        score += 2
        reasons.append("target_navigation_reached")

    if post_nav_hits > 0 and pre_nav_hits == 0:
        score += 2
        reasons.append("post_navigation_only")
    elif post_nav_hits > pre_nav_hits:
        score += 1
        reasons.append("post_navigation_dominant")
    elif pre_nav_hits > 0 and post_nav_hits == 0:
        score -= 2
        reasons.append("pre_navigation_only")

    shape = value_shapes.get(key, {})
    if shape.get("kind") == "list" and shape.get("length", 0) >= 1:
        score += 1
        reasons.append("structured_list")
    elif shape.get("kind") == "dict" and shape.get("field_count", 0) >= 2:
        score += 1
        reasons.append("structured_dict")
    elif shape.get("kind") not in {"list", "dict"}:
        score -= 1
        reasons.append("non_structured_value")

    return score, reasons


def build_exploration_result(task_id: str, run: RunResult, target_hint: str) -> ExplorationResult:
    key_counter: Counter[str] = Counter()
    signal_counter: Counter[str] = Counter()
    post_nav_counter: Counter[str] = Counter()
    pre_nav_counter: Counter[str] = Counter()
    matched_records = 0
    matched_examples: list[dict] = []
    navigation_reached = [
        event.get("name", "")
        for event in (run.step_events or [])
        if event.get("name", "").endswith("_reached")
    ]
    target_name, profile = _resolve_target_profile(target_hint)
    target_nav_names = set(profile.get("navigation_events", []))
    target_navigation_hit = any(name in target_nav_names for name in navigation_reached)

    value_shapes: dict[str, dict] = {}
    noise_rationale: dict[str, dict] = {}
    candidate_timing: dict[str, dict] = {}

    for rec, data in _iter_raw_records(run.raw_paths):
        keys = list(data.keys())
        key_counter.update(keys)

        is_post_nav_record = False
        path = str(rec.get("path") or "")
        if target_navigation_hit:
            matched = [key for key in keys if key in profile.get("positive_keys", [])]
            if matched:
                is_post_nav_record = True
            elif any(alias.lower() in path.lower() for alias in profile.get("aliases", []) if alias):
                is_post_nav_record = True

        for key in keys:
            if is_post_nav_record:
                post_nav_counter[key] += 1
            else:
                pre_nav_counter[key] += 1

            if key not in value_shapes:
                value_shapes[key] = _value_shape(data.get(key))

        matched = []
        for key in keys:
            if key in profile.get("positive_keys", []):
                matched.append(key)
        if matched:
            matched_records += 1
            signal_counter.update(matched)
            if len(matched_examples) < 3:
                matched_examples.append(
                    {
                        "ts": rec.get("ts", ""),
                        "matched_keys": matched,
                        "all_keys": keys[:20],
                        "day": data.get("Day", ""),
                        "time": data.get("Time", ""),
                        "path": path,
                    }
                )

    scored_keys: list[tuple[str, int, list[str], int]] = []
    for key, count in key_counter.items():
        score, reasons = _score_key(
            key,
            count,
            profile,
            navigation_reached,
            post_nav_counter.get(key, 0),
            pre_nav_counter.get(key, 0),
            value_shapes,
        )
        scored_keys.append((key, score, reasons, count))
        candidate_timing[key] = {
            "pre_navigation_hits": pre_nav_counter.get(key, 0),
            "post_navigation_hits": post_nav_counter.get(key, 0),
            "post_navigation_only": pre_nav_counter.get(key, 0) == 0 and post_nav_counter.get(key, 0) > 0,
        }
        noise_rationale[key] = {
            "category": _noise_category(key, profile),
            "reasons": reasons,
        }
    scored_keys.sort(key=lambda item: (-item[1], -item[3], item[0]))

    candidate_keys = [key for key, score, _, _ in scored_keys if score > 0][:8]
    likely_noise_keys = [key for key, score, _, _ in scored_keys if score <= -2][:8]

    positive_non_generic_candidates = [
        key for key in candidate_keys
        if key in profile.get("positive_keys", []) and key != "List"
    ]
    generic_list_dominant = bool(candidate_keys) and candidate_keys[0] == "List" and not positive_non_generic_candidates
    common_block_dominant = any(key in candidate_keys[:3] for key in profile.get("negative_keys", [])[:3])

    readiness_score = 0
    readiness_reasons: list[str] = []
    if matched_records >= 1:
        readiness_score += 3
        readiness_reasons.append("matched_positive_records")
    if target_navigation_hit:
        readiness_score += 2
        readiness_reasons.append("target_navigation_reached")
    if len(candidate_keys) >= 2:
        readiness_score += 2
        readiness_reasons.append("multiple_candidate_keys")
    if len(likely_noise_keys) <= max(1, len(candidate_keys) // 2):
        readiness_score += 1
        readiness_reasons.append("noise_under_control")
    if positive_non_generic_candidates:
        readiness_score += 1
        readiness_reasons.append("non_generic_positive_candidates")

    self_proof_blockers: list[str] = []
    if generic_list_dominant:
        self_proof_blockers.append("generic_list_dominant")
    if common_block_dominant:
        self_proof_blockers.append("common_blocks_still_dominant")
    if target_navigation_hit and not positive_non_generic_candidates:
        self_proof_blockers.append("no_non_generic_target_signal")
    if matched_records <= 1 and not positive_non_generic_candidates:
        self_proof_blockers.append("single_weak_match_without_specific_signal")

    if self_proof_blockers:
        if matched_records >= 1 and candidate_keys:
            status = "candidate_found"
            recommendation = "已发现候选块证据，但自证门未通过，暂不能宣称已抓到目标主块。"
        else:
            status = "not_ready"
            recommendation = "尚未形成可靠候选证据，建议复查导航入口或抓包范围。"
    elif readiness_score >= 7 and matched_records >= 1:
        status = "strong_candidate_evidence"
        recommendation = "已形成较强候选证据，建议由 OpenClaw 结合目标语义决定是否沉淀。"
    elif candidate_keys and matched_records >= 1:
        status = "candidate_found"
        recommendation = "已识别到候选块证据，但仍存在噪声或目标证据不足，建议继续观察。"
    else:
        status = "not_ready"
        recommendation = "尚未形成可靠候选证据，建议复查导航入口或抓包范围。"

    top_candidate_evidence = []
    for key in candidate_keys[:6]:
        shape = value_shapes.get(key, {})
        top_candidate_evidence.append(
            {
                "key": key,
                "timing": candidate_timing.get(key, {}),
                "shape": shape,
                "noise_rationale": noise_rationale.get(key, {}),
            }
        )

    return ExplorationResult(
        task_id=task_id,
        target_hint=target_hint,
        status=status,
        candidate_keys=candidate_keys,
        matched_records=matched_records,
        navigation_reached=navigation_reached,
        likely_noise_keys=likely_noise_keys,
        recommendation=recommendation,
        recommended_page_name=profile.get("recommended_page_name", "") if target_name != "generic" else "",
        evidence={
            "matched_examples": matched_examples,
            "top_keys": key_counter.most_common(20),
            "signal_keys": signal_counter.most_common(20),
            "captured_count": run.captured_count,
            "parsed_count": run.parsed_count,
            "target_profile": target_name,
            "readiness_score": readiness_score,
            "readiness_reasons": readiness_reasons,
            "self_proof_blockers": self_proof_blockers,
            "post_navigation_counts": dict(post_nav_counter),
            "pre_navigation_counts": dict(pre_nav_counter),
            "top_candidate_evidence": top_candidate_evidence,
            "scored_keys": [
                {
                    "key": key,
                    "score": score,
                    "reasons": reasons,
                    "count": count,
                    "timing": candidate_timing.get(key, {}),
                    "shape": value_shapes.get(key, {}),
                    "noise_rationale": noise_rationale.get(key, {}),
                }
                for key, score, reasons, count in scored_keys[:12]
            ],
        },
    )
