"""
Midscene 异常场景处理器
"""
import logging
import time
import tempfile
import uiautomator2 as u2
from typing import Optional
from src.midscene.bridge import MidsceneBridge
from src.controller.state import detect_page, PageState

log = logging.getLogger(__name__)

class MidsceneHandler:
    def __init__(self, device: u2.Device, bridge: MidsceneBridge):
        self.device = device
        self.bridge = bridge

    def _take_screenshot(self) -> str:
        """保存临时截图"""
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp_path = tmp.name
        tmp.close()
        self.device.screenshot(tmp_path)
        return tmp_path

    def handle(self) -> bool:
        """
        触发视觉异常处理
        判断当前状态并调用相应的视觉任务
        """
        # 1. 首先尝试基于传统 UI 定位的状态检测
        page = detect_page(self.device)
        log.info(f"MidsceneHandler: 触发异常处理，当前逻辑检测状态: {page}")

        # 如果已经是明确的验证码，直接视觉处理
        if page == PageState.CAPTCHA:
            return self._solve_captcha()

        # 如果是已知但难以通过 u2 关闭的弹窗，或者未知状态
        # 此时使用视觉识别来确认真正的页面类型
        shot = self._take_screenshot()
        try:
            visual_type = self.bridge.detect_page_type(shot)
            log.info(f"Midscene 视觉识别结果: {visual_type}")

            if visual_type == "captcha":
                return self._solve_captcha(shot)
            elif visual_type in ("unknown", "login"):
                # 如果视觉识别为未知或登录，尝试关闭可能存在的弹窗
                return self.bridge.dismiss_dialog(shot)
            elif visual_type == "home":
                log.info("视觉判断已在首页，无需处理")
                return True
            else:
                # 尝试点击通用关闭
                return self.bridge.dismiss_dialog(shot)
        finally:
            if shot and os.path.exists(shot):
                os.unlink(shot)

    def _solve_captcha(self, screenshot_path: Optional[str] = None) -> bool:
        """处理验证码"""
        log.info("Midscene: 正在处理验证码...")
        shot = screenshot_path or self._take_screenshot()
        try:
            success = self.bridge.handle_captcha(shot)
            if success:
                log.info("Midscene: 验证码处理成功")
                time.sleep(2)  # 等待加载
            return success
        finally:
            if not screenshot_path and shot and os.path.exists(shot):
                os.unlink(shot)

import os
