"""
设备连接与初始化
uiautomator2 使用懒加载 import，模块可在无设备时导入
"""
from __future__ import annotations

import json
import socket
import subprocess
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from src import config

if TYPE_CHECKING:
    import uiautomator2 as u2

log = logging.getLogger(__name__)

_DISMISS_TEXTS = ["我知道了", "跳过", "允许", "稍后再说", "取消", "关闭", "不再提示"]


class PreflightError(RuntimeError):
    """结构化预检失败。"""

    def __init__(self, code: str, message: str, recover_hint: str = ""):
        super().__init__(message)
        self.code = code
        self.recover_hint = recover_hint

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": str(self),
            "recover_hint": self.recover_hint,
        }


def connect_device(serial: str = None):
    """连接 ADB 设备，返回 u2.Device 实例"""
    import uiautomator2 as u2

    d = u2.connect(serial) if serial else u2.connect_usb()

    info = d.device_info
    log.info(f"已连接: {info['brand']} {info['model']} (Android {info['version']})")
    log.info(f"分辨率: {d.window_size()}")

    d.settings["wait_timeout"] = 10
    d.settings["operation_delay"] = (0.5, 1.0)
    return d


def launch_app(d, fresh_start: bool = False, package: str | None = None, activity: str | None = None):
    """启动小红书，处理启动弹窗"""
    package_name = package or config.APP_PACKAGE
    launch_activity = activity or config.APP_ACTIVITY
    if fresh_start:
        d.app_stop(package_name)
        time.sleep(1)

    d.app_start(package_name, activity=launch_activity, use_monkey=False)
    time.sleep(3)
    _dismiss_startup_dialogs(d)


def configure_proxy(port: int = None):
    """配置 adb reverse + 全局代理。"""
    port = port or config.PROXY_PORT
    subprocess.run(["adb", "reverse", "tcp:%s" % port, "tcp:%s" % port], check=True)
    subprocess.run(
        ["adb", "shell", "su", "-c", f"settings put global http_proxy 127.0.0.1:{port}"],
        check=True,
    )


def clear_proxy(port: int = None):
    """清理 adb reverse + 全局代理。"""
    port = port or config.PROXY_PORT
    subprocess.run(
        ["adb", "shell", "su", "-c", "settings put global http_proxy :0"],
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["adb", "shell", "su", "-c", "settings delete global http_proxy"],
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["adb", "reverse", "--remove", f"tcp:{port}"],
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["adb", "reverse", "--remove-all"],
        capture_output=True,
        text=True,
    )


def _dismiss_startup_dialogs(d):
    """关闭启动时可能出现的弹窗（更新提示/权限请求等）"""
    for text in _DISMISS_TEXTS:
        if d(text=text).exists(timeout=1):
            d(text=text).click()
            time.sleep(0.5)


def capture_screenshot(d, path: str | Path) -> dict:
    """保存截图；失败时返回结构化错误，不抛异常。"""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        ok = d.screenshot(str(out))
        return {
            "ok": bool(ok),
            "path": str(out),
            "captured_at": datetime.now().isoformat(timespec="seconds"),
            "error": "" if ok else "screenshot_failed",
        }
    except Exception as exc:
        return {
            "ok": False,
            "path": str(out),
            "captured_at": datetime.now().isoformat(timespec="seconds"),
            "error": f"{type(exc).__name__}: {exc}",
        }


def capture_ui_dump(d, path: str | Path) -> dict:
    """导出 UI hierarchy；失败时返回结构化错误。"""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        xml = d.dump_hierarchy(compressed=False, pretty=True)
        out.write_text(xml, encoding="utf-8")
        return {
            "ok": True,
            "path": str(out),
            "captured_at": datetime.now().isoformat(timespec="seconds"),
            "error": "",
        }
    except Exception as exc:
        return {
            "ok": False,
            "path": str(out),
            "captured_at": datetime.now().isoformat(timespec="seconds"),
            "error": f"{type(exc).__name__}: {exc}",
        }


def capture_visible_text(d, limit: int = 120) -> dict:
    """提取当前 UI 可见文本；失败时返回空列表与错误。"""
    try:
        xml = d.dump_hierarchy(compressed=False, pretty=False)
        texts: list[str] = []
        seen: set[str] = set()
        marker = ' text="'
        start = 0
        while True:
            idx = xml.find(marker, start)
            if idx == -1:
                break
            idx += len(marker)
            end = xml.find('"', idx)
            if end == -1:
                break
            text = xml[idx:end].strip()
            start = end + 1
            if not text or text in seen:
                continue
            seen.add(text)
            texts.append(text)
            if len(texts) >= limit:
                break
        return {
            "ok": True,
            "texts": texts,
            "captured_at": datetime.now().isoformat(timespec="seconds"),
            "error": "",
        }
    except Exception as exc:
        return {
            "ok": False,
            "texts": [],
            "captured_at": datetime.now().isoformat(timespec="seconds"),
            "error": f"{type(exc).__name__}: {exc}",
        }


def preflight_check() -> dict:
    """代理链路预检：验证设备、adb reverse、设备代理设置、本地端口监听四项条件。"""
    port = config.PROXY_PORT
    expected_forward = f"tcp:{port} tcp:{port}"
    expected_proxy = f"127.0.0.1:{port}"

    devices = subprocess.run(
        ["adb", "devices"],
        capture_output=True,
        text=True,
    )
    device_lines = [line.strip() for line in devices.stdout.splitlines()[1:] if line.strip()]
    online_devices = [line for line in device_lines if "\tdevice" in line]
    if not online_devices:
        raise PreflightError(
            code="device_offline",
            message="未检测到在线 ADB 设备。",
            recover_hint="检查 USB/无线 ADB 连接、开发者调试授权，然后重试 adb devices。",
        )

    reverse_list = subprocess.run(
        ["adb", "reverse", "--list"],
        capture_output=True,
        text=True,
    )
    if reverse_list.returncode != 0:
        raise PreflightError(
            code="adb_reverse_list_failed",
            message=f"读取 adb reverse 列表失败: {reverse_list.stderr.strip() or reverse_list.stdout.strip()}",
            recover_hint=f"确认设备在线后重试：adb reverse tcp:{port} tcp:{port}",
        )
    if expected_forward not in reverse_list.stdout:
        raise PreflightError(
            code="adb_reverse_missing",
            message=f"adb reverse 未设置 {expected_forward}。",
            recover_hint=f"运行：adb reverse tcp:{port} tcp:{port}",
        )

    proxy_result = subprocess.run(
        ["adb", "shell", "su", "-c", "settings get global http_proxy"],
        capture_output=True,
        text=True,
    )
    proxy_val = proxy_result.stdout.strip()
    if proxy_result.returncode != 0:
        raise PreflightError(
            code="device_proxy_read_failed",
            message=f"读取设备代理设置失败: {proxy_result.stderr.strip() or proxy_result.stdout.strip()}",
            recover_hint=f"确认设备可执行 su，并设置代理到 {expected_proxy}",
        )
    if proxy_val != expected_proxy:
        raise PreflightError(
            code="device_proxy_mismatch",
            message=f"设备代理设置错误，当前值为 {proxy_val!r}。",
            recover_hint=f"运行：adb shell su -c \"settings put global http_proxy {expected_proxy}\"",
        )

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect(("127.0.0.1", port))
        sock.close()
    except (ConnectionRefusedError, OSError):
        raise PreflightError(
            code="proxy_not_listening",
            message=f"本地端口 {port} 无监听。",
            recover_hint=f"先启动：XHS_DB_PATH=\"data/xiaohongshu.db\" mitmdump -p {port} -s src/proxy/addon.py",
        )

    summary = {
        "ok": True,
        "code": "ok",
        "message": "代理预检通过",
        "recover_hint": "",
        "port": port,
        "online_devices": online_devices,
        "expected_forward": expected_forward,
        "expected_proxy": expected_proxy,
    }
    log.info("代理预检通过: %s", json.dumps(summary, ensure_ascii=False))
    return summary
