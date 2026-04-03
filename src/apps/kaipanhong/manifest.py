"""
开盘红 App 级清单。

当前为最小占位 manifest。
字段尽量与开盘啦保持同构，但值必须是 app-specific，不能偷用开盘啦身份。
"""

from __future__ import annotations

from src import config
from src.apps.kaipanla.manifest import AppManifest


def build_stub_manifest() -> AppManifest:
    return AppManifest(
        app_name="开盘红",
        package_name="com.aiyu.kaipanhong",
        launch_activity=".splash.SplashActivity",
        db_path="data/kaipanhong.db",
        proxy_port=config.PROXY_PORT,
        target_hosts=set(),
        target_paths=[],
        page_markers={
            "home": ("首页", "行情", "自选", "龙虎榜"),
            "login": ("登录", "注册"),
            "unknown_dialog": ("知道了", "稍后再说", "取消"),
        },
        notes=[
            "这是开盘红的最小 adapter manifest，占位先行。",
            "target_hosts / target_paths / 页面锚点需基于真实抓包与 UI 证据补齐。",
            "不得直接把开盘啦的网络特征当成开盘红已验证事实。",
        ],
    )
