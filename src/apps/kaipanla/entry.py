"""
开盘啦迁移入口。

当前只负责把占位配置、缺失字段和首轮验证清单打印出来，
用于接续上下文和 Mac mini 首轮验证前的快速检查。
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
from pathlib import Path

from src.apps.kaipanla.checklist import build_first_round_checklist
from src.apps.kaipanla.manifest import build_stub_manifest
from src.apps.kaipanla.report import render_run_report
from src.apps.kaipanla.runner import run_task
from src.apps.kaipanla.verify import render_verification_summary, verify_run
from src.apps.kaipanla.task import TaskSpec


def _format_block(lines: list[str]) -> str:
    return "\n".join(lines)


def render_manifest() -> str:
    manifest = build_stub_manifest()
    lines = [
        f"应用名称: {manifest.app_name}",
        f"包名: {manifest.package_name or '待确认'}",
        f"启动 Activity: {manifest.launch_activity or '待确认'}",
        f"数据库路径: {manifest.db_path}",
        f"代理端口: {manifest.proxy_port}",
        f"目标主机: {', '.join(sorted(manifest.target_hosts)) or '待确认'}",
        f"目标路径: {', '.join(manifest.target_paths) or '待确认'}",
        f"页面标记: {', '.join(manifest.page_markers.keys())}",
        f"缺失字段: {', '.join(manifest.missing_fields()) or '无'}",
        "",
        "备注:",
    ]
    lines.extend([f"- {note}" for note in manifest.notes])
    return _format_block(lines)


def render_checklist() -> str:
    checklist = build_first_round_checklist()
    lines = [f"清单名称: {checklist.title}", ""]

    for index, item in enumerate(checklist.items, start=1):
        lines.extend([
            f"{index}. {item.step}",
            f"   目的: {item.purpose}",
            f"   证据: {item.evidence}",
            f"   完成标准: {item.done_when}",
            f"   失败回退: {item.fallback}",
            "",
        ])

    lines.append("风险提示:")
    lines.extend([f"- {risk}" for risk in checklist.risks])
    lines.append("")
    lines.append("复盘模板:")
    lines.extend([f"- {field}" for field in checklist.recap_template])
    return _format_block(lines)


def render_action_plan() -> str:
    manifest = build_stub_manifest()
    ready_text = "已就绪" if manifest.is_ready() else "未就绪"
    missing = ", ".join(manifest.missing_fields()) or "无"
    lines = [
        f"当前状态: {ready_text}",
        f"缺失字段: {missing}",
        "",
        "下一步动作:",
        "- 在 Mac mini 上先确认 `adb devices`、`mitmdump --version`、`node --version`",
        "- 首页、包名、启动 Activity、首页结构都已确认",
        "- 优先继续抓 `市场情绪` 页之外的 `行情 / 自选股 / 龙虎榜`",
        "- 对新页面只保留原始样本，再按真实字段补 parser",
        "- 维持 SQLite 去重落库，不扩大框架面",
    ]
    return _format_block(lines)


def _check_command_version(command: str, version_args: list[str]) -> tuple[bool, str]:
    if shutil.which(command) is None:
        return False, "未安装"

    try:
        result = subprocess.run(
            [command, *version_args],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:  # pragma: no cover - subprocess failure path
        return False, f"执行失败: {exc}"

    output = (result.stdout or result.stderr).strip().splitlines()
    first_line = output[0].strip() if output else "无法获取版本"
    if result.returncode != 0:
        return False, first_line
    return True, first_line


def render_environment_check() -> str:
    manifest = build_stub_manifest()
    checks: list[tuple[str, bool, str]] = []

    for command, args in (
        ("git", ["--version"]),
        ("python3", ["--version"]),
        ("node", ["--version"]),
        ("adb", ["version"]),
        ("mitmdump", ["--version"]),
    ):
        ok, detail = _check_command_version(command, args)
        checks.append((command, ok, detail))

    checks.append(
        (
            "uiautomator2",
            importlib.util.find_spec("uiautomator2") is not None,
            "可导入" if importlib.util.find_spec("uiautomator2") is not None else "未安装",
        )
    )

    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip().splitlines()
        has_device = any(
            line.strip().endswith("\tdevice")
            for line in output[1:]
        )
        device_detail = "已连接设备" if has_device else "未发现设备"
    except Exception as exc:  # pragma: no cover - subprocess failure path
        has_device = False
        device_detail = f"执行失败: {exc}"

    checks.append(("adb devices", has_device, device_detail))
    ready = all(ok for _, ok, _ in checks)

    lines = [
        f"目标应用: {manifest.app_name}",
        f"整体状态: {'就绪' if ready else '未就绪'}",
        "",
        "检查结果:",
    ]
    for name, ok, detail in checks:
        status = "OK" if ok else "FAIL"
        lines.append(f"- {name}: {status} ({detail})")

    lines.extend([
        "",
        "如果未就绪，先补齐失败项，再进入画像和抓包。",
    ])
    return _format_block(lines)


def build_report(section: str = "all") -> str:
    sections: list[str] = []
    if section in ("all", "manifest"):
        sections.append("【开盘啦占位配置】")
        sections.append(render_manifest())
    if section in ("all", "checklist"):
        if sections:
            sections.append("")
        sections.append("【开盘啦首轮验证清单】")
        sections.append(render_checklist())
    if section in ("all", "actions"):
        if sections:
            sections.append("")
        sections.append("【开盘啦下一步动作】")
        sections.append(render_action_plan())
    if section in ("all", "env"):
        if sections:
            sections.append("")
        sections.append("【Mac mini 环境自检】")
        sections.append(render_environment_check())
    return _format_block(sections)


def _load_task(task_path: str | None) -> TaskSpec:
    if task_path:
        return TaskSpec.load(task_path)
    return TaskSpec.market_emotion_default()


def render_capture_summary(task: TaskSpec, result) -> str:
    lines = [
        f"任务: {task.task_id}",
        f"页面: {task.page}",
        f"状态: {result.status}",
        f"原始请求: {result.captured_count}",
        f"解析记录: {result.parsed_count}",
        f"结果报告: {result.report_path or Path(task.reports_dir) / f'{task.task_id}.md'}",
        f"运行记录: {Path(task.runs_dir) / f'{task.task_id}.json'}",
    ]
    if result.error:
        lines.append(f"错误: {result.error}")
    if result.next_action:
        lines.append(f"下一步: {result.next_action}")
    return _format_block(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="开盘啦迁移入口")
    parser.add_argument(
        "--section",
        choices=["all", "manifest", "checklist", "actions", "env"],
        default="all",
        help="输出指定内容（未指定子命令时生效）",
    )
    subparsers = parser.add_subparsers(dest="command")

    capture_parser = subparsers.add_parser("capture", help="执行一次抓取任务")
    capture_parser.add_argument("--task", help="任务 JSON 路径")

    report_parser = subparsers.add_parser("report", help="打印运行报告")
    report_parser.add_argument("--task", help="任务 JSON 路径")
    report_parser.add_argument("--run", help="运行结果 JSON 路径")

    verify_parser = subparsers.add_parser("verify", help="校验一次抓取结果")
    verify_parser.add_argument("--run", required=True, help="运行结果 JSON 路径")
    verify_parser.add_argument("--task", help="任务 JSON 路径")

    args = parser.parse_args(argv)

    if args.command == "capture":
        task = _load_task(args.task)
        result = run_task(task)
        print(render_capture_summary(task, result))
        print("")
        print(render_run_report(task, result))
        return 0 if result.status in ("success", "partial") else 1

    if args.command == "report":
        if not args.run:
            raise SystemExit("--run 是 report 子命令的必填参数")
        run_path = Path(args.run)
        from src.apps.kaipanla.task import RunResult

        result = RunResult.load(run_path)
        if args.task:
            task = _load_task(args.task)
        else:
            task_path = run_path.with_suffix(".task.json")
            task = TaskSpec.load(task_path) if task_path.exists() else TaskSpec.market_emotion_default()
        print(render_run_report(task, result))
        return 0

    if args.command == "verify":
        verification = verify_run(args.run, args.task)
        print(render_verification_summary(verification))
        return 0 if verification.status == "verified" else 1

    print(build_report(args.section))
    return 0
