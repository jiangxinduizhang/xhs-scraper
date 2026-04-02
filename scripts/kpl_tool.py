#!/usr/bin/env python3
"""Machine-readable Kaipanla bridge for external agents."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.apps.kaipanla.agent_loop import build_round1_plan, decide_next_step
from src.apps.kaipanla.exploration import build_exploration_result
from src.apps.kaipanla.pages import list_pages
from src.apps.kaipanla.report import build_page_summary, render_run_report
from src.apps.kaipanla.runner import run_task
from src.apps.kaipanla.task import RunResult, TaskSpec
from src.apps.kaipanla.verify import verify_run


def _load_task(task_path: str | None, preset: str | None = None) -> TaskSpec:
    if task_path:
        return TaskSpec.load(task_path)
    return TaskSpec.for_preset(preset)


def _parse_action_plan(action_plan: str | None) -> list[dict]:
    if not action_plan:
        return []
    data = json.loads(action_plan)
    if not isinstance(data, list):
        raise ValueError("action_plan must be a JSON list")
    return [item for item in data if isinstance(item, dict)]


def _load_exploration_task(
    text: str,
    preset: str | None = None,
    *,
    navigation_hint: str = "",
    round_index: int = 1,
    max_rounds: int = 1,
    session_id: str = "",
    action_plan: list[dict] | None = None,
    capture_options: dict | None = None,
) -> TaskSpec:
    chosen = preset or "market_emotion"
    task = TaskSpec.for_exploration(text, page=chosen, preset=chosen, navigation_hint=navigation_hint)
    task.round_index = max(1, int(round_index or 1))
    task.max_rounds = max(1, int(max_rounds or 1))
    task.session_id = session_id or ""
    if action_plan:
        task.action_plan = list(action_plan)
    if capture_options:
        task.capture_options.update(capture_options)
    return task


def _task_meta(task: TaskSpec, *, used_default_preset: bool = False) -> dict:
    return {
        "preset": task.preset,
        "page": task.page,
        "modules": list(task.modules),
        "output": list(task.output),
        "compare": task.compare,
        "interpretation_style": task.interpretation_style,
        "used_default_preset": used_default_preset,
        "supported_pages": list_pages(),
        "message": "当前按默认预设 market_emotion 执行" if used_default_preset else f"当前按预设 {task.preset} 执行",
    }


def _intent_meta(command: str, *, task_path: str | None = None, preset: str | None = None, used_default_preset: bool = False) -> dict:
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
        "command": command,
        "resolution": resolution,
        "reason": reason,
        "task_path_provided": bool(task_path),
        "preset": preset or "market_emotion",
        "used_default_preset": used_default_preset,
    }


def _load_run(run_path: str | Path) -> RunResult:
    return RunResult.load(run_path)


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
        "page_summary": build_page_summary(task, run),
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
        "ok": verification.status in {"artifacts_complete", "evidence_complete"},
        "command": "verify",
        "intent_meta": _intent_meta("verify", task_path=args.task, preset=None, used_default_preset=False),
        "verification": asdict(verification),
        "run": run.to_dict() if run else None,
        "task": task.to_dict() if task else None,
    }
    if task:
        payload["task_meta"] = _task_meta(task)
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
        "page_summary": build_page_summary(task, run),
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
    latest["ok"] = verification.status in {"artifacts_complete", "evidence_complete"}
    return latest


def cmd_explore(args) -> dict:
    capture_options = {
        "screenshot_before_after": not bool(getattr(args, "no_screenshot", False)),
        "ui_dump_before_after": not bool(getattr(args, "no_ui_dump", False)),
        "visible_text_before_after": not bool(getattr(args, "no_visible_text", False)),
        "focus_post_action_window": not bool(getattr(args, "no_focus_post_action_window", False)),
    }
    round_index = getattr(args, "round_index", 1) or 1
    max_rounds = max(1, int(getattr(args, "max_rounds", 2) or 2))
    action_plan = _parse_action_plan(getattr(args, "action_plan", None))
    navigation_hint = getattr(args, "navigation_hint", "") or ""

    planner = None
    if round_index == 1 and not args.preset and not action_plan and not navigation_hint:
        planner = build_round1_plan(args.text, max_rounds=max_rounds)
        if planner.preset:
            args.preset = planner.preset
        navigation_hint = planner.navigation_hint
        action_plan = planner.action_plan

    task = _load_exploration_task(
        args.text,
        args.preset,
        navigation_hint=navigation_hint,
        round_index=round_index,
        max_rounds=max_rounds,
        session_id=getattr(args, "session_id", "") or "",
        action_plan=action_plan,
        capture_options=capture_options,
    )
    payload = {
        "ok": True,
        "command": "explore",
        "execute": bool(args.execute),
        "planner": planner.to_dict() if planner else None,
        "task": task.to_dict(),
        "task_meta": {
            **_task_meta(task, used_default_preset=False),
            "mode": "exploration",
        },
        "runtime_policy": {
            "max_rounds": max_rounds,
            "semantic_routing": False,
            "semantic_adjustment": False,
            "ai_must_decide_next_step": True,
        },
    }
    if not args.execute:
        payload["message"] = "已生成 exploration task；当前为 dry-run，未实际执行。"
        return payload

    rounds = []
    previous_signature = None
    final_run = None
    final_exploration = None
    reached_limit = False

    for round_no in range(1, max_rounds + 1):
        if round_no > 1:
            task.notes = list(task.notes) + [f"auto_round_{round_no}: repeated evidence collection without runtime-side semantic adjustment"]

        run = run_task(task)
        exploration = build_exploration_result(task.task_id, run, task.target_hint or task.goal)
        current_signature = (
            tuple(exploration.observed_keys[:12]),
            tuple(exploration.observed_paths[:6]),
            exploration.raw_record_count,
        )

        decision = decide_next_step(exploration)
        rounds.append({
            "round": round_no,
            "task": task.to_dict(),
            "run": run.to_dict(),
            "exploration": exploration.to_dict(),
            "decision": decision.to_dict(),
        })

        final_run = run
        final_exploration = exploration

        if decision.decision != "continue":
            if round_no >= max_rounds:
                reached_limit = True
            break

        no_improvement = previous_signature == current_signature
        if no_improvement or round_no >= max_rounds:
            reached_limit = True
            break

        previous_signature = current_signature
        task.round_index = decision.next_round_index or (round_no + 1)
        if decision.next_navigation_hint:
            task.notes = [note for note in task.notes if not str(note).startswith("navigation_hint:")]
            task.notes.append(f"navigation_hint: {decision.next_navigation_hint}")
        if decision.next_action_plan:
            task.action_plan = list(decision.next_action_plan)

    payload["rounds"] = rounds
    payload["run"] = final_run.to_dict() if final_run else None
    payload["exploration"] = final_exploration.to_dict() if final_exploration else None
    payload["runtime_stop_reason"] = "evidence_bundle_collected" if final_exploration and final_exploration.evidence_status == "evidence_complete" else ("max_rounds_reached" if reached_limit else "incomplete")
    payload["requires_ai_decision"] = True
    payload["ok"] = bool(final_run and final_run.status in ("success", "partial"))
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

    p_explore = sub.add_parser("explore", help="assistant-directed exploration")
    p_explore.add_argument("text", help="exploration target")
    p_explore.add_argument("--preset", default=None, help="explicit preset/page for exploration bootstrap")
    p_explore.add_argument("--navigation-hint", default="", help="human/AI supplied navigation hint for this exploration round")
    p_explore.add_argument("--round-index", type=int, default=1, help="exploration round index")
    p_explore.add_argument("--max-rounds", type=int, default=2, help="max execution rounds before handing control back to AI")
    p_explore.add_argument("--session-id", default="", help="session identifier for multi-round exploration")
    p_explore.add_argument("--action-plan", help="JSON list describing explicit action plan for this round")
    p_explore.add_argument("--no-screenshot", action="store_true", help="disable screenshot before/after capture")
    p_explore.add_argument("--no-ui-dump", action="store_true", help="disable UI dump before/after capture")
    p_explore.add_argument("--no-visible-text", action="store_true", help="disable visible text before/after capture")
    p_explore.add_argument("--no-focus-post-action-window", action="store_true", help="disable focus on post-action request window")
    p_explore.add_argument("--execute", action="store_true", help="actually execute the exploration task")

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
    if args.command == "explore":
        return _emit(cmd_explore(args), pretty=args.pretty)
    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
