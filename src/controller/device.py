"""
设备连接与初始化
uiautomator2 使用懒加载 import，模块可在无设备时导入
"""
from __future__ import annotations

import socket
import subprocess
import time
import logging
from typing import TYPE_CHECKING

from src import config

if TYPE_CHECKING:
    import uiautomator2 as u2

log = logging.getLogger(__name__)

_DISMISS_TEXTS = ["我知道了", "跳过", "允许", "稍后再说", "取消", "关闭", "不再提示"]


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


def launch_app(d, fresh_start: bool = False):
    """启动小红书，处理启动弹窗"""
    if fresh_start:
        d.app_stop(config.APP_PACKAGE)
        time.sleep(1)

    d.app_start(config.APP_PACKAGE, use_monkey=False)
    time.sleep(3)
    _dismiss_startup_dialogs(d)


def _dismiss_startup_dialogs(d):
    """关闭启动时可能出现的弹窗（更新提示/权限请求等）"""
    for text in _DISMISS_TEXTS:
        if d(text=text).exists(timeout=1):
            d(text=text).click()
            time.sleep(0.5)


def preflight_check():
    """代理链路预检：验证 adb reverse、设备代理设置、本地端口监听三项条件"""
    port = config.PROXY_PORT

    # 1. 检查 adb reverse 转发是否包含 tcp:{port} tcp:{port}
    result = subprocess.run(
        ["adb", "reverse", "--list"],
        capture_output=True,
        text=True,
    )
    expected_forward = f"tcp:{port} tcp:{port}"
    if expected_forward not in result.stdout:
        raise RuntimeError(
            f"adb reverse 未设置。请运行：\n"
            f"  adb reverse tcp:{port} tcp:{port}"
        )

    # 2. 检查设备代理设置是否为 127.0.0.1:{port}
    result = subprocess.run(
        ["adb", "shell", "su", "-c", "settings get global http_proxy"],
        capture_output=True,
        text=True,
    )
    proxy_val = result.stdout.strip()
    expected_proxy = f"127.0.0.1:{port}"
    if proxy_val != expected_proxy:
        raise RuntimeError(
            f"设备代理设置错误（当前: {proxy_val!r}）。请运行：\n"
            f"  adb shell su -c \"settings put global http_proxy 127.0.0.1:{port}\""
        )

    # 3. 检查本地端口是否有进程监听
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect(("127.0.0.1", port))
        sock.close()
    except (ConnectionRefusedError, OSError):
        raise RuntimeError(
            f"本地端口 {port} 无监听。请先启动 mitmdump：\n"
            f"  XHS_DB_PATH=\"data/xiaohongshu.db\" mitmdump -p {port} -s src/proxy/addon.py"
        )

    log.info("代理预检通过")
