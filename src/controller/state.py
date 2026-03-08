"""
页面状态检测 - 判断当前停留在哪个页面
小红书 v9.x resource-id 全部混淆，使用 activity 名称 + text / content-desc 判断
"""
from __future__ import annotations

import time
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uiautomator2 as u2


class PageState(Enum):
    UNKNOWN = "unknown"
    HOME = "home"
    SEARCH_INPUT = "search_input"
    SEARCH_RESULT = "search_result"
    NOTE_DETAIL = "note_detail"
    COMMENT = "comment"
    USER_PROFILE = "user_profile"
    LOGIN = "login"
    CAPTCHA = "captcha"
    UNKNOWN_DIALOG = "unknown_dialog"


def detect_page(d: u2.Device) -> PageState:
    """检测当前页面状态"""
    current_app = d.app_current()
    if current_app.get("package") != "com.xingin.xhs":
        return PageState.UNKNOWN

    activity = current_app.get("activity", "")

    # ─── Activity 名称快速判断（优先，无需元素查询）────────────
    if any(s in activity for s in ("Login", "login", "SignIn", "Register")):
        return PageState.LOGIN

    if "NoteDetail" in activity or "notedetail" in activity.lower():
        # 简化判断：在详情页内只要有评论输入框就视为可采集评论状态
        # 进入详情页后评论 API 已自动触发，不需要区分"展开"状态
        if (d(descriptionContains="说点什么").exists(timeout=0.5) or
                d(text="说点什么").exists(timeout=0.5)):
            return PageState.COMMENT
        return PageState.NOTE_DETAIL

    if any(s in activity for s in ("Search", "search")) and "ImageBrowser" not in activity:
        if d(className="android.widget.EditText", focused=True).exists(timeout=0.5):
            return PageState.SEARCH_INPUT
        return PageState.SEARCH_RESULT

    if any(s in activity for s in ("User", "Profile", "user", "profile")):
        return PageState.USER_PROFILE

    # ─── 兜底：元素检测 ──────────────────────────────────────
    if _has_captcha(d):
        return PageState.CAPTCHA

    # 搜索结果：有"综合"tab
    if d(text="综合").exists(timeout=0.5):
        return PageState.SEARCH_RESULT

    # 首页：底栏同时有"首页"和"发现"
    if d(description="首页").exists(timeout=0.5) and \
       d(description="发现").exists(timeout=0.5):
        return PageState.HOME

    if _has_dialog(d):
        return PageState.UNKNOWN_DIALOG

    return PageState.UNKNOWN


def _has_captcha(d: u2.Device) -> bool:
    indicators = [
        d(textContains="滑动验证"),
        d(textContains="拖动滑块"),
        d(descriptionContains="验证码"),
        d(textContains="图形验证"),
    ]
    return any(elem.exists(timeout=0.3) for elem in indicators)


def _has_dialog(d: u2.Device) -> bool:
    return d(className="android.app.Dialog").exists(timeout=0.3)


def navigate_to_home(d: u2.Device, max_back: int = 5) -> bool:
    """多次返回直到首页，处理搜索页避免误退出 APP"""
    for _ in range(max_back):
        page = detect_page(d)
        if page == PageState.HOME:
            return True
        # 在搜索结果或搜索输入页时先 back 退出搜索，再继续判断
        if page in (PageState.SEARCH_RESULT, PageState.SEARCH_INPUT):
            d.press("back")
            time.sleep(0.8)
            # 退出搜索后再检测，避免继续循环多次 back 导致退出 APP
            if detect_page(d) == PageState.HOME:
                return True
        d.press("back")
        time.sleep(0.8)
    return False
