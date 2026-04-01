#!/usr/bin/env python3
"""Machine-readable Kaipanla bridge for external agents."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.apps.kaipanla.report import build_market_summary, render_run_report
from src.apps.kaipanla.runner import run_task
from src.apps.kaipanla.task import RunResult, TaskSpec
from src.apps.kaipanla.verify import render_verification_summary, verify_run


def _load_task(task_path: str | None, preset: str | None = None) -> TaskSpec:
    if task_path:
        return TaskSpec.load(task_path)
    return TaskSpec.for_preset(preset)


def _task_meta(task: TaskSpec, *, used_default_preset: bool = False) -> dict:
    return {
        "preset": task.preset,
        "page": task.page,
        "modules": list(task.modules),
        "output": list(task.output),
        "compare": task.compare,
        "interpretation_style": task.interpretation_style,
        "used_default_preset": used_default_preset,
        "message": "当前按默认预设 market_emotion 执行" if used_default_preset else f"当前按预设 {task.preset} 执行",
    }


def _intent_meta(command: str, *, task_path: str | None = None, preset: str | None = None, used_default_preset: bool = False) -> dict:
    intent = "read"
    if command == "capture":
        intent = "capture"
    elif command in {"status", "verify"}:
        intent = "status"

    resolution = "task_file"
    if not task_path:
        resolution = "default_preset" if used_default_preset else "explicit_preset"

    if resolution == "task_file":
        reason = "已提供 task 文件，按显式任务执行或回读"
    elif resolution == "explicit_preset":
        reason = f"未提供 task 文件，按显式 preset={preset or 'market_emotion'} 处理"
    else:
        reason = "未提供 task 文件，按当前默认预设 market_emotion 处理"

    return {
        "intent": intent,
        "command": command,
        "resolution": resolution,
        "reason": reason,
        "task_path_provided": bool(task_path),
        "preset": preset or "market_emotion",
        "used_default_preset": used_default_preset,
    }


def _load_run(run_path: str | Path) -> RunResult:
    return RunResult.load(run_path)


def _contains_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def _parse_focus(text: str) -> list[str]:
    focus: list[str] = []
    mapping = [
        ("day_compare", ["对比", "比较", "昨天", "昨日", "上一交易日", "前一天"]),
        ("hot_themes", ["热点", "主线", "题材", "风口"]),
        ("money_flow", ["资金", "主力", "节奏"]),
        ("risk_flags", ["风险", "弱势", "退潮", "炸板"]),
        ("ranking_focus", ["排行", "龙虎", "辨识度", "连板"]),
        ("status_only", ["运行状态", "状态", "成功没", "成功了吗", "verify", "验证"]),
    ]
    for key, words in mapping:
        if _contains_any(text, words):
            focus.append(key)
    return focus


def _parse_style(text: str) -> str:
    if _contains_any(text, ["结构化", "json", "机器可读", "字段"]):
        return "structured"
    if _contains_any(text, ["人话", "复盘", "复盘口吻", "交易员", "trader"]):
        return "trader_recap"
    if _contains_any(text, ["简短", "简洁", "一句话", "只要结论"]):
        return "brief"
    return "human_summary"


def parse_nl_request(text: str, *, default_preset: str = "market_emotion") -> dict:
    normalized = re.sub(r"\s+", "", text.lower())
    preset = default_preset
    intent = "read"

    if _contains_any(normalized, ["运行状态", "状态", "成功没", "成功了吗", "verify", "验证"]):
        intent = "status"
    elif _contains_any(normalized, ["抓取", "重抓", "重新抓", "重新跑", "执行", "采集", "刷新", "更新最新"]):
        intent = "capture"
    elif _contains_any(normalized, ["看看", "读取", "总结", "报告", "盘面", "市场情况", "最新结果", "最新情况"]):
        intent = "read"

    focus = _parse_focus(normalized)
    style = _parse_style(normalized)
    compare = "previous_trading_day" if "day_compare" in focus else "none"
    output = ["run", "report", "market_summary"]
    if "day_compare" in focus:
        output.append("day_compare")
    if "status_only" in focus and intent == "status":
        output = ["verification"]

    read_mode = "latest"
    if intent == "status":
        read_mode = "status"
    elif intent == "read":
        if _contains_any(normalized, ["报告", "总结", "解读", "盘面摘要", "人话", "复盘"]):
            read_mode = "report"
        else:
            read_mode = "latest"

    ambiguous = not _contains_any(normalized, ["开盘啦", "市场", "盘面", "情绪", "运行状态", "报告", "抓取", "采集", "最新结果"])

    clarification_question = None
    if ambiguous:
        clarification_question = "你是想执行一次抓取、查看运行状态，还是读取最近一次结果？"

    return {
        "ok": not ambiguous,
        "text": text,
        "intent": intent,
        "preset": preset,
        "focus": focus,
        "style": style,
        "compare": compare,
        "output": output,
        "read_mode": read_mode,
        "needs_clarification": ambiguous,
        "clarification_question": clarification_question,
        "reason": "按关键词完成最小自然语言路由；当前仅支持有限意图、默认 preset 和基础 read 路由。",
    }


def _latest_run_path(runs_dir: str = "runs") -> Path | None:
    root = Path(runs_dir)
    candidates = [
        path for path in root.glob("*.json")
        if path.is_file() and not path.name.endswith(".task.json")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _emit(payload: dict, pretty: bool = False) -> int:
    if pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


def _structured_failure(run: RunResult) -> dict | None:
    source_counts = run.source_counts if isinstance(run.source_counts, dict) else {}
    error_code = source_counts.get("error_code")
    error_stage = source_counts.get("error_stage")
    if not error_code and run.status in ("success", "partial"):
        return None
    return {
        "code": error_code or "runtime_failed",
        "stage": error_stage or "runtime",
        "message": run.error,
        "recover_hint": run.next_action,
    }


def cmd_capture(args) -> dict:
    used_default_preset = not args.task and not args.preset
    task = _load_task(args.task, args.preset)
    run = run_task(task)
    payload = {
        "ok": run.status in ("success", "partial"),
        "command": "capture",
        "intent_meta": _intent_meta("capture", task_path=args.task, preset=args.preset, used_default_preset=used_default_preset),
        "task": task.to_dict(),
        "task_meta": _task_meta(task, used_default_preset=used_default_preset),
        "run": run.to_dict(),
        "market_summary": build_market_summary(task, run),
    }
    failure = _structured_failure(run)
    if failure:
        payload["failure"] = failure
    return payload


def cmd_verify(args) -> dict:
    verification = verify_run(args.run, args.task)
    run = _load_run(args.run) if Path(args.run).exists() else None
    task = TaskSpec.load(args.task) if args.task and Path(args.task).exists() else None
    payload = {
        "ok": verification.status == "verified",
        "command": "verify",
        "intent_meta": _intent_meta("verify", task_path=args.task, preset=None, used_default_preset=False),
        "verification": asdict(verification),
        "run": run.to_dict() if run else None,
        "task": task.to_dict() if task else None,
    }
    if task:
        payload["task_meta"] = _task_meta(task)
    if run and task:
        payload["market_summary"] = build_market_summary(task, run)
    return payload


def cmd_report(args) -> dict:
    run = _load_run(args.run)
    if args.task:
        task = TaskSpec.load(args.task)
        used_default_preset = False
    else:
        task_path = Path(args.run).with_suffix(".task.json")
        used_default_preset = not task_path.exists()
        task = TaskSpec.load(task_path) if task_path.exists() else TaskSpec.for_preset(args.preset)
    report = render_run_report(task, run)
    payload = {
        "ok": True,
        "command": "report",
        "intent_meta": _intent_meta("report", task_path=args.task, preset=args.preset, used_default_preset=used_default_preset),
        "task": task.to_dict(),
        "task_meta": _task_meta(task, used_default_preset=used_default_preset),
        "run": run.to_dict(),
        "report_text": report,
        "market_summary": build_market_summary(task, run),
    }
    return payload


def cmd_latest(args) -> dict:
    path = _latest_run_path(args.runs_dir)
    if path is None:
        return {
            "ok": False,
            "command": "latest",
            "intent_meta": _intent_meta("latest", task_path=None, preset=args.preset, used_default_preset=False),
            "message": "no run found",
            "run_path": None,
        }
    run = _load_run(path)
    task_path = path.with_suffix(".task.json")
    used_default_preset = not task_path.exists()
    task = TaskSpec.load(task_path) if task_path.exists() else TaskSpec.for_preset(args.preset)
    payload = {
        "ok": True,
        "command": "latest",
        "intent_meta": _intent_meta("latest", task_path=str(task_path) if task_path.exists() else None, preset=args.preset, used_default_preset=used_default_preset),
        "run_path": str(path),
        "task_path": str(task_path) if task_path.exists() else None,
        "run": run.to_dict(),
        "task": task.to_dict() if task else None,
        "task_meta": _task_meta(task, used_default_preset=used_default_preset),
    }
    if task:
        payload["market_summary"] = build_market_summary(task, run)
    return payload


def cmd_status(args) -> dict:
    latest = cmd_latest(args)
    if not latest.get("ok"):
        latest["command"] = "status"
        latest["intent_meta"] = _intent_meta("status", task_path=None, preset=args.preset, used_default_preset=False)
        return latest
    verification = verify_run(latest["run_path"])
    latest["command"] = "status"
    latest["intent_meta"] = _intent_meta(
        "status",
        task_path=latest.get("task_path"),
        preset=args.preset,
        used_default_preset=latest.get("task_meta", {}).get("used_default_preset", False),
    )
    latest["verification"] = asdict(verification)
    latest["ok"] = verification.status == "verified"
    return latest


def cmd_ask(args) -> dict:
    parsed = parse_nl_request(args.text, default_preset=args.preset)
    payload = {
        "ok": parsed["ok"],
        "command": "ask",
        "execute": bool(args.execute),
        "nl_request": parsed,
    }
    if parsed["needs_clarification"]:
        payload["message"] = parsed["clarification_question"]
        return payload

    route_command = {
        "capture": "capture",
        "status": "status",
        "read": parsed.get("read_mode", "latest"),
    }[parsed["intent"]]

    payload["suggested_route"] = {
        "intent": parsed["intent"],
        "preset": parsed["preset"],
        "runs_dir": args.runs_dir,
        "command": route_command,
    }
    if not args.execute:
        payload["message"] = "已完成自然语言解析；当前为 dry-run，仅返回建议路由，未实际执行。"
        return payload

    if parsed["intent"] == "capture":
        routed = cmd_capture(argparse.Namespace(task=None, preset=parsed["preset"]))
    elif parsed["intent"] == "status":
        routed = cmd_status(argparse.Namespace(runs_dir=args.runs_dir, preset=parsed["preset"]))
    elif parsed.get("read_mode") == "report":
        latest = cmd_latest(argparse.Namespace(runs_dir=args.runs_dir, preset=parsed["preset"]))
        if not latest.get("ok"):
            routed = latest
        else:
            routed = cmd_report(
                argparse.Namespace(
                    run=latest["run_path"],
                    task=latest.get("task_path"),
                    preset=parsed["preset"],
                )
            )
    else:
        routed = cmd_latest(argparse.Namespace(runs_dir=args.runs_dir, preset=parsed["preset"]))
    payload["routed"] = routed
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kaipanla machine-readable bridge")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON")

    sub = parser.add_subparsers(dest="command", required=True)

    p_capture = sub.add_parser("capture", help="execute a capture task")
    p_capture.add_argument("--task", help="task JSON path")
    p_capture.add_argument("--preset", default="market_emotion", help="preset task name")

    p_verify = sub.add_parser("verify", help="verify a completed run")
    p_verify.add_argument("--run", required=True, help="run JSON path")
    p_verify.add_argument("--task", help="task JSON path")

    p_report = sub.add_parser("report", help="render a run report")
    p_report.add_argument("--run", required=True, help="run JSON path")
    p_report.add_argument("--task", help="task JSON path")
    p_report.add_argument("--preset", default="market_emotion", help="preset task name")

    p_latest = sub.add_parser("latest", help="show the latest run")
    p_latest.add_argument("--runs-dir", default="runs", help="runs directory")
    p_latest.add_argument("--preset", default="market_emotion", help="fallback preset when task file is missing")

    p_status = sub.add_parser("status", help="verify the latest run")
    p_status.add_argument("--runs-dir", default="runs", help="runs directory")
    p_status.add_argument("--preset", default="market_emotion", help="fallback preset when task file is missing")

    p_ask = sub.add_parser("ask", help="route a natural-language request")
    p_ask.add_argument("text", help="natural-language request")
    p_ask.add_argument("--runs-dir", default="runs", help="runs directory")
    p_ask.add_argument("--preset", default="market_emotion", help="default preset for routing")
    p_ask.add_argument("--execute", action="store_true", help="actually execute the routed command")

    args = parser.parse_args(argv)

    if args.command == "capture":
        return _emit(cmd_capture(args), pretty=args.pretty)
    if args.command == "verify":
        return _emit(cmd_verify(args), pretty=args.pretty)
    if args.command == "report":
        return _emit(cmd_report(args), pretty=args.pretty)
    if args.command == "latest":
        return _emit(cmd_latest(args), pretty=args.pretty)
    if args.command == "status":
        return _emit(cmd_status(args), pretty=args.pretty)
    if args.command == "ask":
        return _emit(cmd_ask(args), pretty=args.pretty)
    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
