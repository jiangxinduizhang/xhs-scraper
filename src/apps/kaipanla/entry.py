"""
开盘啦迁移入口。

当前只负责把占位配置、缺失字段和首轮验证清单打印出来，
用于接续上下文和 Mac mini 首轮验证前的快速检查。
"""

from __future__ import annotations

import argparse
from textwrap import indent

from src.apps.kaipanla.checklist import build_first_round_checklist
from src.apps.kaipanla.manifest import build_stub_manifest


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
    return _format_block(sections)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="开盘啦迁移入口")
    parser.add_argument(
        "--section",
        choices=["all", "manifest", "checklist"],
        default="all",
        help="输出指定内容",
    )
    args = parser.parse_args(argv)
    print(build_report(args.section))
    return 0

