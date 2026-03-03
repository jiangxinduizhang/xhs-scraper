"""
设备连接与初始化
uiautomator2 使用懒加载 import，模块可在无设备时导入
"""
from __future__ import annotations

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
