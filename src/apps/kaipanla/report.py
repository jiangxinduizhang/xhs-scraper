"""
开盘啦运行报告生成。
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from src.apps.kaipanla.task import RunResult, TaskSpec


def _count(result: RunResult, key: str) -> int:
    return int((result.note_type_counts or {}).get(key, 0) or 0)


def _find_latest_raw_record(result: RunResult) -> dict:
    for raw_path in result.raw_paths or []:
        path = Path(raw_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            continue
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for line in reversed(lines):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            data = rec.get("data")
            if isinstance(data, dict) and ("DaBanList" in data or "BaceFaceList" in data):
                return data
    return {}


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

    raw = _find_latest_raw_record(result)
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

    market_overview = [
        f"上涨家数 {up_count} / 下跌家数 {down_count} / 平盘 {flat_count}",
        f"涨停 {up_limit} / 跌停 {down_limit}",
        f"综合强度 {strength_score:.0f}",
        f"炸板率 {blowup_rate:.2f}%",
    ]

    risk_flags = weak_weather + ([f"炸板率偏高: {blowup_rate:.2f}%"] if blowup_rate >= 35 else [])
    review_tone = _extract_review_tone(mood, blowup_rate, hot_themes, strong_weather or fkyd_focus, risk_flags)

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
        bullets.extend(review_tone)
        bullets.append(parser_confidence_text)

    sections = {
        "market_overview": market_overview,
        "emotion_judgement": [f"情绪判断: {mood}", mood_reason, f"上涨/下跌比约 {breadth_ratio:.2f}"],
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
        "raw_snapshot": {
            "hot_themes": hot_themes,
            "strong_weather": strong_weather,
            "weak_weather": weak_weather,
            "ranking_focus": ranking_focus,
            "money_focus": money_focus,
            "lock_positions": lock_positions,
            "fkyd_focus": fkyd_focus,
        },
    }


def _render_human_summary(task: TaskSpec, result: RunResult) -> list[str]:
    summary = build_market_summary(task, result)
    lines = [f"- {line}" for line in summary["bullets"]]
    sections = summary.get("sections", {})
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
