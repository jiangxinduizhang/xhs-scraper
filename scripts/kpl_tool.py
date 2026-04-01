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

from src.apps.kaipanla.report import build_market_summary, render_run_report
from src.apps.kaipanla.runner import run_task
from src.apps.kaipanla.task import RunResult, TaskSpec
from src.apps.kaipanla.verify import render_verification_summary, verify_run


def _load_task(task_path: str | None) -> TaskSpec:
    if task_path:
        return TaskSpec.load(task_path)
    return TaskSpec.market_emotion_default()


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


def cmd_capture(args) -> dict:
    task = _load_task(args.task)
    run = run_task(task)
    payload = {
        "ok": run.status in ("success", "partial"),
        "command": "capture",
        "task": task.to_dict(),
        "run": run.to_dict(),
        "market_summary": build_market_summary(task, run),
    }
    return payload


def cmd_verify(args) -> dict:
    verification = verify_run(args.run, args.task)
    run = _load_run(args.run) if Path(args.run).exists() else None
    task = TaskSpec.load(args.task) if args.task and Path(args.task).exists() else None
    payload = {
        "ok": verification.status == "verified",
        "command": "verify",
        "verification": asdict(verification),
        "run": run.to_dict() if run else None,
        "task": task.to_dict() if task else None,
    }
    if run and task:
        payload["market_summary"] = build_market_summary(task, run)
    return payload


def cmd_report(args) -> dict:
    run = _load_run(args.run)
    if args.task:
        task = TaskSpec.load(args.task)
    else:
        task_path = Path(args.run).with_suffix(".task.json")
        task = TaskSpec.load(task_path) if task_path.exists() else TaskSpec.market_emotion_default()
    report = render_run_report(task, run)
    payload = {
        "ok": True,
        "command": "report",
        "task": task.to_dict(),
        "run": run.to_dict(),
        "report_text": report,
        "market_summary": build_market_summary(task, run),
    }
    return payload


def cmd_latest(args) -> dict:
    path = _latest_run_path(args.runs_dir)
    if path is None:
        return {"ok": False, "command": "latest", "message": "no run found", "run_path": None}
    run = _load_run(path)
    task_path = path.with_suffix(".task.json")
    task = TaskSpec.load(task_path) if task_path.exists() else None
    payload = {
        "ok": True,
        "command": "latest",
        "run_path": str(path),
        "task_path": str(task_path) if task else None,
        "run": run.to_dict(),
        "task": task.to_dict() if task else None,
    }
    if task:
        payload["market_summary"] = build_market_summary(task, run)
    return payload


def cmd_status(args) -> dict:
    latest = cmd_latest(args)
    if not latest.get("ok"):
        latest["command"] = "status"
        return latest
    verification = verify_run(latest["run_path"])
    latest["command"] = "status"
    latest["verification"] = asdict(verification)
    latest["ok"] = verification.status == "verified"
    return latest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kaipanla machine-readable bridge")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON")

    sub = parser.add_subparsers(dest="command", required=True)

    p_capture = sub.add_parser("capture", help="execute a capture task")
    p_capture.add_argument("--task", help="task JSON path")

    p_verify = sub.add_parser("verify", help="verify a completed run")
    p_verify.add_argument("--run", required=True, help="run JSON path")
    p_verify.add_argument("--task", help="task JSON path")

    p_report = sub.add_parser("report", help="render a run report")
    p_report.add_argument("--run", required=True, help="run JSON path")
    p_report.add_argument("--task", help="task JSON path")

    p_latest = sub.add_parser("latest", help="show the latest run")
    p_latest.add_argument("--runs-dir", default="runs", help="runs directory")

    p_status = sub.add_parser("status", help="verify the latest run")
    p_status.add_argument("--runs-dir", default="runs", help="runs directory")

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
    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
