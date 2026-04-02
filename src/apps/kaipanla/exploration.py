"""
开盘啦探索模式支持。

用于 assistant-directed exploration：
- 不要求先有正式注册页面
- 重点是产生候选页面证据、候选关键字段和沉淀建议
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


NOISE_KEYS = {
    "Ad_1", "Ad_2", "Ad_4", "Ad_5", "IndexAd", "List", "errcode", "t", "time"
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


def _target_words(target_hint: str) -> list[str]:
    text = (target_hint or "").strip().lower()
    mapping = {
        "龙虎榜": ["longhubang", "dragon", "longhu", "龙虎", "席位", "上榜", "买入", "卖出"],
        "盘中雷达": ["dongxiang", "雷达", "异动", "动向"],
        "精选": ["topic", "theme", "精选", "题材", "主题"],
        "情绪": ["daban", "zhqd", "情绪", "涨停", "炸板"],
    }
    for key, words in mapping.items():
        if key in target_hint:
            return words
    return [part for part in text.replace("_", " ").split() if part]


def build_exploration_result(task_id: str, run: RunResult, target_hint: str) -> ExplorationResult:
    key_counter: Counter[str] = Counter()
    signal_counter: Counter[str] = Counter()
    matched_records = 0
    target_words = _target_words(target_hint)
    matched_examples: list[dict] = []

    for rec, data in _iter_raw_records(run.raw_paths):
        keys = list(data.keys())
        key_counter.update(keys)

        matched = []
        for key in keys:
            lowered = key.lower()
            if any(word and word in lowered for word in target_words):
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
                    }
                )

    candidate_keys = [key for key, _ in signal_counter.most_common(8)]
    if not candidate_keys:
        candidate_keys = [key for key, _ in key_counter.most_common(12) if key not in NOISE_KEYS][:8]

    likely_noise_keys = [key for key, _ in key_counter.most_common(12) if key in NOISE_KEYS][:6]
    navigation_reached = [
        event.get("name", "")
        for event in (run.step_events or [])
        if event.get("name", "").endswith("_reached")
    ]

    if matched_records >= 1 and candidate_keys:
        status = "ready_to_promote"
        recommendation = "已找到候选页面证据，可进入沉淀评估。"
    elif candidate_keys:
        status = "candidate_found"
        recommendation = "已找到部分候选字段，建议继续补导航或缩小目标范围。"
    else:
        status = "request_not_found"
        recommendation = "尚未识别到明显候选字段，建议复查页面入口或抓包范围。"

    recommended_page_name = ""
    if "龙虎榜" in target_hint:
        recommended_page_name = "dragon_tiger"
    elif "雷达" in target_hint:
        recommended_page_name = "market_radar"
    elif "精选" in target_hint:
        recommended_page_name = "market_featured"

    return ExplorationResult(
        task_id=task_id,
        target_hint=target_hint,
        status=status,
        candidate_keys=candidate_keys,
        matched_records=matched_records,
        navigation_reached=navigation_reached,
        likely_noise_keys=likely_noise_keys,
        recommendation=recommendation,
        recommended_page_name=recommended_page_name,
        evidence={
            "matched_examples": matched_examples,
            "top_keys": key_counter.most_common(20),
            "signal_keys": signal_counter.most_common(20),
            "captured_count": run.captured_count,
            "parsed_count": run.parsed_count,
        },
    )
