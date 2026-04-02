"""
开盘啦运行报告生成。
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from src.apps.kaipanla.exploration import build_exploration_result
from src.apps.kaipanla.pages import get_page_spec
from src.apps.kaipanla.task import RunResult, TaskSpec


def _count(result: RunResult, key: str) -> int:
    return int((result.note_type_counts or {}).get(key, 0) or 0)


def _score_market_record(data: dict) -> int:
    if not isinstance(data, dict):
        return -1
    score = 0
    keys = [
        "DaBanList",
        "BaceFaceList",
        "CWeatherVaneList",
        "PHBList",
        "JJXTList",
        "ZQFKList",
        "ZLSCList",
        "FKYDSixList",
        "PLZList",
    ]
    for key in keys:
        value = data.get(key)
        if isinstance(value, dict) and value:
            score += 3
        elif isinstance(value, list) and value:
            score += 3
    if data.get("Day"):
        score += 1
    if data.get("Time"):
        score += 1
    return score


def _extract_record_ts(rec: dict, data: dict) -> tuple[str, int]:
    raw_ts = str(rec.get("ts") or "") if isinstance(rec, dict) else ""
    data_time = 0
    if isinstance(data, dict):
        try:
            data_time = int(data.get("Time") or 0)
        except (TypeError, ValueError):
            data_time = 0
    return raw_ts, data_time


def _build_selected_snapshot(rec: dict, data: dict, reason: str) -> dict:
    daban = data.get("DaBanList") if isinstance(data, dict) else {}
    phb_title = ""
    if isinstance(data, dict):
        phb_title = str(data.get("PHBTitle") or data.get("PHBtitle") or "")
    return {
        "raw_ts": str(rec.get("ts") or "") if isinstance(rec, dict) else "",
        "day": str(data.get("Day") or "") if isinstance(data, dict) else "",
        "time": str(data.get("Time") or "") if isinstance(data, dict) else "",
        "phb_title": phb_title,
        "reason": reason,
        "source": "DaBanList",
        "fields": {
            "ZHQD": daban.get("ZHQD") if isinstance(daban, dict) else None,
            "SZJS": daban.get("SZJS") if isinstance(daban, dict) else None,
            "XDJS": daban.get("XDJS") if isinstance(daban, dict) else None,
            "PPJS": daban.get("PPJS") if isinstance(daban, dict) else None,
            "tZhangTing": daban.get("tZhangTing") if isinstance(daban, dict) else None,
            "tDieTing": daban.get("tDieTing") if isinstance(daban, dict) else None,
            "tFengBan": daban.get("tFengBan") if isinstance(daban, dict) else None,
            "qscln": daban.get("qscln") if isinstance(daban, dict) else None,
        },
    }


def _find_latest_raw_record(result: RunResult) -> tuple[dict, dict]:
    best_data: dict = {}
    best_score = -1
    best_raw_ts = ""
    best_data_time = -1
    best_rec: dict = {}
    for raw_path in result.raw_paths or []:
        path = Path(raw_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            continue
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for line in lines:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            data = rec.get("data")
            score = _score_market_record(data) if isinstance(data, dict) else -1
            if score < 0:
                continue
            raw_ts, data_time = _extract_record_ts(rec, data if isinstance(data, dict) else {})
            if (
                score > best_score
                or (score == best_score and data_time > best_data_time)
                or (score == best_score and data_time == best_data_time and raw_ts > best_raw_ts)
            ):
                best_score = score
                best_data = data
                best_raw_ts = raw_ts
                best_data_time = data_time
                best_rec = rec
    selected_snapshot = _build_selected_snapshot(best_rec, best_data, "latest_valid_market_record_by_time_then_raw_ts") if best_data else {}
    return best_data, selected_snapshot


def _find_previous_market_record(result: RunResult, current_day: str | None) -> dict:
    candidate_paths: list[Path] = []
    for raw_path in result.raw_paths or []:
        path = Path(raw_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if path.exists():
            candidate_paths.append(path)
            parent = path.parent
            for other in sorted(parent.glob("*.jsonl"), reverse=True):
                if other not in candidate_paths:
                    candidate_paths.append(other)

    best_data: dict = {}
    best_score = -1
    best_day = ""
    for path in candidate_paths:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for line in lines:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            data = rec.get("data")
            if not isinstance(data, dict):
                continue
            day = str(data.get("Day") or "")
            if not day or (current_day and day >= current_day):
                continue
            score = _score_market_record(data)
            if day > best_day or (day == best_day and score > best_score):
                best_day = day
                best_score = score
                best_data = data
    return best_data


def _topic_list(items, topic_index: int = 0, value_index: int = 1, limit: int = 3) -> list[str]:
    result: list[str] = []
    for item in (items or [])[:limit]:
        if not isinstance(item, list) or len(item) <= max(topic_index, value_index):
            continue
        result.append(f"{item[topic_index]}({item[value_index]})")
    return result


def _stock_triplets(items, name_index: int = 1, move_index: int = 2, theme_index: int = 3, limit: int = 3) -> list[str]:
    rows: list[str] = []
    for item in (items or [])[:limit]:
        if not isinstance(item, list) or len(item) <= max(name_index, move_index, theme_index):
            continue
        rows.append(f"{item[name_index]} {item[move_index]}% {item[theme_index]}")
    return rows


def _money_rows(items, name_index: int = 1, move_index: int = 2, amount_index: int = 3, theme_index: int = 4, limit: int = 3) -> list[str]:
    rows: list[str] = []
    for item in (items or [])[:limit]:
        if not isinstance(item, list) or len(item) <= max(name_index, move_index, amount_index, theme_index):
            continue
        amount = item[amount_index]
        rows.append(f"{item[name_index]} {item[move_index]}% 资金{amount} 题材:{item[theme_index]}")
    return rows


def _safe_num(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _extract_hot_themes(baceface_list, zqfk_list, jjxt_list, limit: int = 6) -> list[str]:
    themes: list[str] = []
    for item in baceface_list or []:
        if isinstance(item, list) and len(item) >= 2:
            themes.append(f"{item[0]}({item[1]})")

    counter: Counter[str] = Counter()
    for rows in (zqfk_list or []), (jjxt_list or []):
        for item in rows:
            if not isinstance(item, list) or len(item) < 5:
                continue
            topic_field = str(item[4] or "")
            for part in topic_field.replace(";", "、").split("、"):
                part = part.strip()
                if part:
                    counter[part] += 1

    for theme, count in counter.most_common(limit):
        if not any(theme in existing for existing in themes):
            themes.append(f"{theme}(关联{count})")

    return themes[:limit]


def _extract_ranking_focus(phb_list, limit: int = 3) -> list[str]:
    rows: list[str] = []
    for item in (phb_list or [])[:limit]:
        if not isinstance(item, list) or len(item) < 7:
            continue
        stock_name = item[1]
        increase = item[2]
        board_count = item[3]
        reason = item[4]
        topic = item[5] or item[6]
        rows.append(f"{stock_name} 涨{increase}% 板数{board_count}，标签:{reason} / {topic}")
    return rows


def _extract_money_flow(jjxt_list, zqfk_list, zlsc_list, limit: int = 3) -> list[str]:
    rows: list[str] = []
    rows.extend(_money_rows(jjxt_list, 1, 2, 3, 4, limit=limit))
    if len(rows) < limit:
        for item in (zqfk_list or [])[:limit]:
            if not isinstance(item, list) or len(item) < 5:
                continue
            rows.append(f"{item[1]} 涨{item[3]}% 反馈资金{item[2]} 题材:{item[4]}")
            if len(rows) >= limit:
                break
    if len(rows) < limit:
        for item in (zlsc_list or [])[:limit]:
            if not isinstance(item, list) or len(item) < 8:
                continue
            rows.append(f"{item[1]} {item[7]}，题材:{item[3]}，当日涨跌:{item[5]}%")
            if len(rows) >= limit:
                break
    return rows[:limit]


def _extract_review_tone(mood: str, blowup_rate: float, hot_themes: list[str], strong_watchlist: list[str], risk_flags: list[str]) -> list[str]:
    lines: list[str] = []
    if mood == "强势":
        lines.append("指数外的情绪面偏强，短线资金愿意做多，强势股和题材股都有表现。")
    elif mood == "偏强":
        lines.append("盘面偏暖，但更像有主攻方向的结构性活跃，不算无差别普涨。")
    elif mood == "震荡分化":
        lines.append("市场更像分化轮动，适合盯主线，不适合把所有方向都当机会。")
    else:
        lines.append("盘面承接偏弱，做多信号不够一致，应该先收缩风险暴露。")

    if blowup_rate >= 50:
        lines.append("不过炸板率明显偏高，说明强势里带着不小分歧，追高容错率一般。")
    elif blowup_rate >= 30:
        lines.append("炸板率不低，说明盘中博弈强，后排跟风需要更谨慎。")

    if hot_themes:
        lines.append(f"主线观察上，先看 {'、'.join(hot_themes[:4])} 是否继续扩散，而不是只看孤立个股冲高。")
    if strong_watchlist:
        lines.append(f"强势锚点可以盯 {'；'.join(strong_watchlist[:2])}。")
    if risk_flags:
        lines.append(f"风险侧先避开 {'；'.join(risk_flags[:2])} 这类明显弱势反馈。")
    return lines


def _build_day_compare(current_data: dict, previous_data: dict) -> dict | None:
    if not current_data or not previous_data:
        return None

    c_db = current_data.get("DaBanList") or {}
    p_db = previous_data.get("DaBanList") or {}
    c_day = str(current_data.get("Day") or "")
    p_day = str(previous_data.get("Day") or "")
    if not c_day or not p_day:
        return None

    c_up = int(_safe_num(c_db.get("SZJS", 0), 0))
    c_down = int(_safe_num(c_db.get("XDJS", 0), 0))
    p_up = int(_safe_num(p_db.get("SZJS", 0), 0))
    p_down = int(_safe_num(p_db.get("XDJS", 0), 0))
    c_zt = int(_safe_num(c_db.get("tZhangTing", 0), 0))
    p_zt = int(_safe_num(p_db.get("tZhangTing", 0), 0))
    c_dt = int(_safe_num(c_db.get("tDieTing", 0), 0))
    p_dt = int(_safe_num(p_db.get("tDieTing", 0), 0))
    c_strength = _safe_num(c_db.get("ZHQD", 0), 0)
    p_strength = _safe_num(p_db.get("ZHQD", 0), 0)
    c_blow = _safe_num(c_db.get("tFengBan", 0), 0)
    p_blow = _safe_num(p_db.get("tFengBan", 0), 0)

    hot_now = [str(x[0]) for x in (current_data.get("BaceFaceList") or []) if isinstance(x, list) and len(x) >= 1]
    hot_prev = [str(x[0]) for x in (previous_data.get("BaceFaceList") or []) if isinstance(x, list) and len(x) >= 1]
    new_hot = [x for x in hot_now if x not in hot_prev][:4]
    faded_hot = [x for x in hot_prev if x not in hot_now][:4]

    summary: list[str] = []
    if c_up > p_up and c_down < p_down:
        summary.append(f"较 {p_day} 明显回暖：上涨家数从 {p_up} 提升到 {c_up}，下跌家数从 {p_down} 收敛到 {c_down}。")
    elif c_up < p_up and c_down > p_down:
        summary.append(f"较 {p_day} 明显转弱：上涨家数从 {p_up} 降到 {c_up}，下跌家数从 {p_down} 扩大到 {c_down}。")
    else:
        summary.append(f"较 {p_day} 结构有所变化，但不是单边切换。")

    if c_strength > p_strength:
        summary.append(f"综合强度从 {p_strength:.0f} 升到 {c_strength:.0f}。")
    elif c_strength < p_strength:
        summary.append(f"综合强度从 {p_strength:.0f} 降到 {c_strength:.0f}。")

    if c_blow < p_blow:
        summary.append(f"炸板率从 {p_blow:.2f}% 回落到 {c_blow:.2f}%，分歧仍在，但比前一日缓和。")
    elif c_blow > p_blow:
        summary.append(f"炸板率从 {p_blow:.2f}% 升到 {c_blow:.2f}%，追高环境变差。")

    if new_hot:
        summary.append(f"新增/强化题材：{'、'.join(new_hot)}。")
    if faded_hot:
        summary.append(f"相对退潮题材：{'、'.join(faded_hot)}。")

    return {
        "current_day": c_day,
        "previous_day": p_day,
        "up_count_delta": c_up - p_up,
        "down_count_delta": c_down - p_down,
        "up_limit_delta": c_zt - p_zt,
        "down_limit_delta": c_dt - p_dt,
        "strength_delta": c_strength - p_strength,
        "blowup_rate_delta": c_blow - p_blow,
        "new_hot_themes": new_hot,
        "faded_hot_themes": faded_hot,
        "summary": summary,
    }


def _find_latest_record_with_keys(result: RunResult, expected_keys: list[str] | None) -> tuple[dict, dict]:
    best_data: dict = {}
    best_rec: dict = {}
    best_raw_ts = ""
    best_data_time = -1
    expected = list(expected_keys or [])
    for raw_path in result.raw_paths or []:
        path = Path(raw_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            continue
        for line in [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            data = rec.get("data")
            if not isinstance(data, dict):
                continue
            if expected and not any(key in data for key in expected):
                continue
            raw_ts, data_time = _extract_record_ts(rec, data)
            if data_time > best_data_time or (data_time == best_data_time and raw_ts > best_raw_ts):
                best_data = data
                best_rec = rec
                best_raw_ts = raw_ts
                best_data_time = data_time
    selected_snapshot = {
        "raw_ts": str(best_rec.get("ts") or "") if isinstance(best_rec, dict) else "",
        "day": str(best_data.get("Day") or "") if isinstance(best_data, dict) else "",
        "time": str(best_data.get("Time") or "") if isinstance(best_data, dict) else "",
        "reason": "latest_valid_record_by_expected_keys_then_time_then_raw_ts",
        "source": ",".join(expected) if expected else "generic",
    } if best_data else {}
    return best_data, selected_snapshot


def _build_generic_page_summary(task: TaskSpec, result: RunResult) -> dict:
    page_spec = get_page_spec(task.page)
    raw, selected_snapshot = _find_latest_record_with_keys(result, page_spec.expected_keys)
    hit_keys = [key for key in page_spec.expected_keys if isinstance(raw, dict) and key in raw]
    bullets: list[str] = []
    if result.status not in {"success", "partial"}:
        bullets.append("本次抓取未形成可稳定解读的页面摘要，请先检查抓取状态和错误信息。")
    else:
        bullets.append(f"页面 {task.page} 已抓取完成，当前命中关键字段：{', '.join(hit_keys) or '无'}。")
        bullets.append(f"本页目标：{task.goal or page_spec.goal}。")
        if isinstance(raw, dict):
            keys_preview = list(raw.keys())[:12]
            bullets.append(f"当前快照字段预览：{', '.join(keys_preview)}。")
        bullets.append(f"原始请求 {result.captured_count} 条，解析记录 {result.parsed_count} 条。")
    return {
        "page": task.page,
        "status": result.status,
        "bullets": bullets,
        "selected_snapshot": selected_snapshot,
        "counts": {
            "captured_count": result.captured_count,
            "parsed_count": result.parsed_count,
            "unknown": int((result.source_counts or {}).get("unknown", 0) or 0),
        },
        "sections": {
            "verification_fields": [
                f"页面: {task.page}",
                f"页面日期: {raw.get('Day', '') if isinstance(raw, dict) else ''}",
                f"页面时间: {raw.get('Time', '') if isinstance(raw, dict) else ''}",
                f"selected raw ts: {selected_snapshot.get('raw_ts', '')}",
                f"selected reason: {selected_snapshot.get('reason', '')}",
                f"关键字段命中: {', '.join(hit_keys) or '无'}",
            ],
            "page_keys": list(raw.keys())[:20] if isinstance(raw, dict) else [],
        },
        "raw_snapshot": raw if isinstance(raw, dict) else {},
    }


def build_market_summary(task: TaskSpec, result: RunResult) -> dict:
    msg_top = _count(result, "msg_top")
    fkyd = _count(result, "market_fkyd")
    baceface = _count(result, "market_baceface")
    jjxt = _count(result, "market_jjxt")
    phb = _count(result, "market_phb")
    zqfk = _count(result, "market_zqfk")
    zlsc = _count(result, "market_zlsc")
    weather_sz = _count(result, "market_weather_sz")
    weather_xd = _count(result, "market_weather_xd")
    summary = _count(result, "market_emotion_summary")
    plz = _count(result, "market_plz")
    unknown = int((result.source_counts or {}).get("unknown", 0) or 0)

    active_modules = sum(1 for value in [msg_top, fkyd, baceface, jjxt, phb, zqfk, zlsc] if value > 0)
    if active_modules >= 5:
        completeness = "high"
        completeness_text = "市场情绪页主要模块都有数据，页面信息完整度较高，不像是空页或半残抓取。"
    elif active_modules >= 3:
        completeness = "medium"
        completeness_text = "市场情绪页拿到了多类模块数据，能做基础观察，但完整度还不是最强。"
    else:
        completeness = "low"
        completeness_text = "当前抓到的模块较少，更适合当作抓取校验，不适合下重结论。"

    if msg_top >= 8:
        signal_focus = "concentrated"
        signal_focus_text = "顶部/主展示类信息较活跃，说明页面重点信号输出比较集中，适合先看主叙事和强势方向。"
    elif msg_top >= 4:
        signal_focus = "balanced"
        signal_focus_text = "顶部主信息有一定活跃度，但还看不出特别极端的一致性。"
    else:
        signal_focus = "scattered"
        signal_focus_text = "顶部强提示信息不多，情绪信号可能偏分散。"

    modules: list[str] = []
    if fkyd > 0:
        modules.append("风口异动")
    if jjxt > 0:
        modules.append("资金/节奏类信号")
    if phb > 0:
        modules.append("排行类信号")
    if zqfk > 0:
        modules.append("赚钱效应反馈")
    if zlsc > 0:
        modules.append("主力市场/资金观察")
    if baceface > 0:
        modules.append("情绪面板")

    if unknown >= 10:
        parser_confidence = "medium"
        parser_confidence_text = "仍有一部分数据暂时落在 unknown，说明 parser 还有继续细分的空间；当前摘要可用，但不是最终形态。"
    elif unknown > 0:
        parser_confidence = "medium_high"
        parser_confidence_text = "有少量未归类数据，不影响总体回读，但后续还可以继续细化解析规则。"
    else:
        parser_confidence = "high"
        parser_confidence_text = "当前抓取结果已基本完成归类，适合进一步做更稳定的自动摘要。"

    weather_present = any(x > 0 for x in [weather_sz, weather_xd, summary])
    comment_present = plz > 0

    raw, selected_snapshot = _find_latest_raw_record(result)
    previous_raw = _find_previous_market_record(result, str(raw.get("Day") or ""))
    da_ban = raw.get("DaBanList") if isinstance(raw, dict) else {}
    baceface_list = raw.get("BaceFaceList") if isinstance(raw, dict) else []
    weather = raw.get("CWeatherVaneList") if isinstance(raw, dict) else {}
    phb_list = raw.get("PHBList") if isinstance(raw, dict) else []
    jjxt_list = raw.get("JJXTList") if isinstance(raw, dict) else []
    zqfk_list = raw.get("ZQFKList") if isinstance(raw, dict) else []
    zlsclist = raw.get("ZLSCList") if isinstance(raw, dict) else []
    fkyd_list = raw.get("FKYDSixList") if isinstance(raw, dict) else []

    up_limit = int(_safe_num(da_ban.get("tZhangTing", 0), 0)) if isinstance(da_ban, dict) else 0
    down_limit = int(_safe_num(da_ban.get("tDieTing", 0), 0)) if isinstance(da_ban, dict) else 0
    up_count = int(_safe_num(da_ban.get("SZJS", 0), 0)) if isinstance(da_ban, dict) else 0
    down_count = int(_safe_num(da_ban.get("XDJS", 0), 0)) if isinstance(da_ban, dict) else 0
    flat_count = int(_safe_num(da_ban.get("PPJS", 0), 0)) if isinstance(da_ban, dict) else 0
    strength_score = _safe_num(da_ban.get("ZHQD", 0), 0) if isinstance(da_ban, dict) else 0.0
    blowup_rate = _safe_num(da_ban.get("tFengBan", 0), 0) if isinstance(da_ban, dict) else 0.0

    breadth_ratio = (up_count / max(down_count, 1)) if down_count else float(up_count or 0)
    if up_count > down_count * 3 and up_limit >= 40:
        mood = "强势"
        mood_reason = "上涨家数明显压制下跌家数，且涨停家数较多，短线情绪偏强。"
    elif up_count > down_count * 1.5 and up_limit >= 20:
        mood = "偏强"
        mood_reason = "上涨家数占优，涨停表现不弱，整体情绪偏暖。"
    elif down_count > up_count:
        mood = "偏弱"
        mood_reason = "下跌家数压过上涨家数，市场承接一般，情绪偏谨慎。"
    else:
        mood = "震荡分化"
        mood_reason = "涨跌分布并非单边，更多像结构性分化行情。"

    hot_themes = _extract_hot_themes(baceface_list, zqfk_list, jjxt_list, limit=6)
    strong_weather = _stock_triplets((weather.get("SZ") or []) if isinstance(weather, dict) else [], 1, 2, 3, limit=3)
    weak_weather = _stock_triplets((weather.get("XD") or []) if isinstance(weather, dict) else [], 1, 2, 3, limit=3)
    ranking_focus = _extract_ranking_focus(phb_list, limit=3)
    money_focus = _extract_money_flow(jjxt_list, zqfk_list, zlsclist, limit=3)
    lock_positions = [f"{item[1]} {item[7]} 题材:{item[3]} 当日涨跌:{item[5]}%" for item in (zlsclist or [])[:3] if isinstance(item, list) and len(item) > 7]
    fkyd_focus = [f"{item.get('StockName','')} {item.get('zhangfu','')}" for item in (fkyd_list or [])[:3] if isinstance(item, dict)]

    actual_amount_raw = int(_safe_num(da_ban.get("qscln", 0), 0)) if isinstance(da_ban, dict) else 0
    actual_amount_display = int(round(actual_amount_raw / 10000)) if actual_amount_raw else 0

    market_overview = [
        f"上涨家数 {up_count} / 下跌家数 {down_count} / 平盘 {flat_count}",
        f"涨停 {up_limit} / 跌停 {down_limit}",
        f"综合强度 {strength_score:.0f}",
        f"炸板率 {blowup_rate:.2f}%",
        f"沪深实际量能 {actual_amount_display}",
    ]

    risk_flags = weak_weather + ([f"炸板率偏高: {blowup_rate:.2f}%"] if blowup_rate >= 35 else [])
    review_tone = _extract_review_tone(mood, blowup_rate, hot_themes, strong_weather or fkyd_focus, risk_flags)
    day_compare = _build_day_compare(raw, previous_raw)

    bullets: list[str] = []
    if result.status not in {"success", "partial"}:
        bullets.append("本次抓取未形成可稳定解读的市场摘要，请先检查抓取状态和错误信息。")
    else:
        bullets.append(completeness_text)
        bullets.append(signal_focus_text)
        bullets.append(f"盘面整体判断偏{mood}：{mood_reason}")
        if hot_themes:
            bullets.append(f"热点主线先看：{'、'.join(hot_themes[:4])}。")
        if ranking_focus:
            bullets.append(f"连板/辨识度个股可先盯：{'；'.join(ranking_focus[:2])}。")
        if money_focus:
            bullets.append(f"资金与强势股反馈集中在：{'；'.join(money_focus[:2])}。")
        if weak_weather:
            bullets.append(f"弱势/风险方向主要在：{'；'.join(weak_weather)}。")
        if day_compare:
            bullets.extend(day_compare["summary"][:2])
        bullets.extend(review_tone)
        bullets.append(f"验真主值：综合强度 {strength_score:.0f}，上涨 {up_count}，下跌 {down_count}，平盘 {flat_count}，涨停 {up_limit}，跌停 {down_limit}，炸板率 {blowup_rate:.2f}%，沪深实际量能 {actual_amount_display}。")
        bullets.append(parser_confidence_text)

    sections = {
        "market_overview": market_overview,
        "emotion_judgement": [f"情绪判断: {mood}", mood_reason, f"上涨/下跌比约 {breadth_ratio:.2f}"],
        "verification_fields": [
            f"页面: {task.page}",
            f"页面日期: {raw.get('Day', '')}",
            f"页面时间: {raw.get('Time', '')}",
            f"selected raw ts: {selected_snapshot.get('raw_ts', '')}",
            f"selected PHBTitle: {selected_snapshot.get('phb_title', '')}",
            f"selected reason: {selected_snapshot.get('reason', '')}",
            "主值来源: DaBanList",
            f"综合强度: {strength_score:.0f}",
            f"上涨家数: {up_count}",
            f"下跌家数: {down_count}",
            f"平盘家数: {flat_count}",
            f"涨停家数: {up_limit}",
            f"跌停家数: {down_limit}",
            f"炸板率: {blowup_rate:.2f}%",
            f"沪深实际量能(raw): {actual_amount_raw}",
            f"沪深实际量能(display): {actual_amount_display}",
        ],
        "day_compare": day_compare,
        "hot_themes": hot_themes,
        "strong_watchlist": strong_weather or fkyd_focus,
        "ranking_focus": ranking_focus,
        "money_flow": money_focus,
        "review_tone": review_tone,
        "risk_flags": risk_flags,
        "observation_points": [
            "优先观察热点题材能否从点状走向扩散。",
            "观察强势风向标个股是否继续封板/加强。",
            "留意弱势方向是否继续扩散成风险传导。",
        ],
    }

    return {
        "page": task.page,
        "status": result.status,
        "completeness": completeness,
        "signal_focus": signal_focus,
        "parser_confidence": parser_confidence,
        "weather_present": weather_present,
        "comment_present": comment_present,
        "active_modules": modules,
        "mood": mood,
        "sections": sections,
        "counts": {
            "captured_count": result.captured_count,
            "parsed_count": result.parsed_count,
            "msg_top": msg_top,
            "market_fkyd": fkyd,
            "market_baceface": baceface,
            "market_jjxt": jjxt,
            "market_phb": phb,
            "market_zqfk": zqfk,
            "market_zlsc": zlsc,
            "market_emotion_summary": summary,
            "market_plz": plz,
            "unknown": unknown,
            "up_count": up_count,
            "down_count": down_count,
            "flat_count": flat_count,
            "up_limit": up_limit,
            "down_limit": down_limit,
            "strength_score": strength_score,
            "blowup_rate": blowup_rate,
        },
        "bullets": bullets,
        "selected_snapshot": selected_snapshot,
        "raw_snapshot": {
            "hot_themes": hot_themes,
            "strong_weather": strong_weather,
            "weak_weather": weak_weather,
            "ranking_focus": ranking_focus,
            "money_focus": money_focus,
            "lock_positions": lock_positions,
            "fkyd_focus": fkyd_focus,
            "previous_day": previous_raw.get("Day") if isinstance(previous_raw, dict) else None,
        },
    }


def _build_exploration_summary(task: TaskSpec, result: RunResult) -> dict:
    exploration = build_exploration_result(task.task_id, result, task.target_hint or task.goal)
    bullets = [
        f"探索目标：{task.target_hint or task.goal}",
        f"探索状态：{exploration.status}",
        f"候选关键字段：{', '.join(exploration.candidate_keys) or '无'}",
        f"命中记录数：{exploration.matched_records}",
        f"到达导航节点：{', '.join(exploration.navigation_reached) or '无'}",
        f"建议：{exploration.recommendation}",
    ]
    return {
        "page": task.page,
        "mode": "exploration",
        "status": result.status,
        "bullets": bullets,
        "counts": {
            "captured_count": result.captured_count,
            "parsed_count": result.parsed_count,
            "matched_records": exploration.matched_records,
        },
        "sections": {
            "candidate_keys": exploration.candidate_keys,
            "likely_noise_keys": exploration.likely_noise_keys,
            "navigation_reached": exploration.navigation_reached,
            "recommendation": exploration.recommendation,
            "recommended_page_name": exploration.recommended_page_name,
        },
        "exploration": exploration.to_dict(),
    }


def build_page_summary(task: TaskSpec, result: RunResult) -> dict:
    if getattr(task, "mode", "registered") == "exploration":
        return _build_exploration_summary(task, result)
    if task.page == "market_emotion":
        return build_market_summary(task, result)
    return _build_generic_page_summary(task, result)


def _render_human_summary(task: TaskSpec, result: RunResult) -> list[str]:
    summary = build_page_summary(task, result)
    lines = [f"- {line}" for line in summary["bullets"]]
    sections = summary.get("sections", {})
    day_compare = sections.get("day_compare")
    if day_compare and day_compare.get("summary"):
        lines.append("- 跨日对比：" + "；".join(day_compare["summary"][:3]))
    if sections.get("market_overview"):
        lines.append("- 市场总览：" + "；".join(sections["market_overview"]))
    if sections.get("hot_themes"):
        lines.append("- 热点方向：" + "、".join(sections["hot_themes"][:5]))
    if sections.get("ranking_focus"):
        lines.append("- 连板/辨识度：" + "；".join(sections["ranking_focus"][:3]))
    if sections.get("money_flow"):
        lines.append("- 资金/强势股：" + "；".join(sections["money_flow"][:3]))
    if sections.get("review_tone"):
        lines.append("- 复盘口吻：" + "；".join(sections["review_tone"][:3]))
    if sections.get("risk_flags"):
        lines.append("- 风险提示：" + "；".join(sections["risk_flags"][:3]))
    if sections.get("observation_points"):
        lines.append("- 观察点：" + "；".join(sections["observation_points"][:3]))
    return lines


def render_run_report(task: TaskSpec, result: RunResult) -> str:
    if getattr(task, "mode", "registered") == "exploration":
        exploration = build_exploration_result(task.task_id or result.task_id, result, task.target_hint or task.goal)
        lines = [
            f"# Kaipanla Exploration Report · {task.task_id or result.task_id}",
            "",
            "## 概览",
            f"- 应用: {task.app}",
            f"- 页面: {task.page}",
            f"- 目标: {task.target_hint or task.goal or '无'}",
            f"- 证据状态: {exploration.evidence_status}",
            f"- 导航事件: {', '.join(exploration.navigation_events) or '无'}",
            f"- 观测到的 key: {', '.join(exploration.observed_keys[:12]) or '无'}",
            f"- 观测到的 path: {', '.join(exploration.observed_paths) or '无'}",
            f"- raw 记录数: {exploration.raw_record_count}",
            "",
            "## 说明",
            "- 这是事实证据包，不代表 bridge 已确认目标页面语义或主块。",
            "- 是否继续、收紧、停止、ask-human，均应由 AI 基于该证据包决定。",
            "",
            "## Evidence Bundle",
            "```json",
            json.dumps(exploration.to_dict(), ensure_ascii=False, indent=2),
            "```",
            "",
        ]
        return "\n".join(lines).rstrip() + "\n"

    lines: list[str] = [
        f"# {task.task_id}",
        "",
        "## 概览",
        f"- 应用: {task.app}",
        f"- 页面: {task.page}",
        f"- 目标: {task.goal or '无'}",
        f"- 状态: {result.status}",
        f"- 开始: {result.started_at}",
        f"- 结束: {result.finished_at or '进行中'}",
        f"- 耗时: {result.duration_sec:.1f}s",
        "",
        "## 结果",
        f"- 原始请求: {result.captured_count}",
        f"- 解析记录: {result.parsed_count}",
        f"- 数据库: {result.db_path or task.db_path}",
        f"- 原始样本: {', '.join(result.raw_paths) or '无'}",
        f"- 下一步: {result.next_action or task.next_action_hint or '无'}",
        "",
        "## 盘面摘要",
    ]

    lines.extend(_render_human_summary(task, result))

    lines.extend([
        "",
        "## 来源统计",
    ])

    if result.source_counts:
        for source, count in sorted(result.source_counts.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {source}: {count}")
    else:
        lines.append("- 无")

    lines.extend([
        "",
        "## 类型统计",
    ])
    if result.note_type_counts:
        for note_type, count in sorted(result.note_type_counts.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {note_type}: {count}")
    else:
        lines.append("- 无")

    lines.extend([
        "",
        "## 步骤时间线",
    ])
    step_events = getattr(result, "step_events", []) or []
    if step_events:
        for event in step_events:
            detail = f" | {event.get('detail', '')}" if event.get("detail") else ""
            lines.append(f"- {event.get('at', '')} {event.get('name', '')}{detail}")
    else:
        lines.append("- 无")

    if result.error:
        lines.extend([
            "",
            "## 错误",
            result.error,
        ])

    if task.notes:
        lines.extend([
            "",
            "## 任务备注",
        ])
        lines.extend([f"- {note}" for note in task.notes])

    return "\n".join(lines).rstrip() + "\n"


def write_run_report(task: TaskSpec, result: RunResult, path: str | Path) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    report = render_run_report(task, result)
    path.write_text(report, encoding="utf-8")
    result.report_path = str(path)
    return report
