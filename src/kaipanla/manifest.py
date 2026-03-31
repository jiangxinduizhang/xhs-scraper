"""
开盘啦 App 级清单。

这个文件只描述目标 App 的基础信息和待验证项，不放具体抓取实现。
后续在 Mac mini 上完成首轮画像后，再把这里的占位项补齐。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AppManifest:
    """描述一个目标 App 的最小运行所需元数据。"""

    app_name: str
    package_name: str | None
    launch_activity: str | None
    db_path: str
    proxy_port: int
    target_hosts: set[str] = field(default_factory=set)
    target_paths: list[str] = field(default_factory=list)
    page_markers: dict[str, tuple[str, ...]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def missing_fields(self) -> list[str]:
        """返回尚未补齐的关键字段。"""
        missing: list[str] = []
        if not self.package_name:
            missing.append("package_name")
        if not self.launch_activity:
            missing.append("launch_activity")
        if not self.target_hosts:
            missing.append("target_hosts")
        if not self.target_paths:
            missing.append("target_paths")
        return missing

    def is_ready(self) -> bool:
        """是否已经具备首轮验证所需的最小信息。"""
        return not self.missing_fields()


def build_stub_manifest() -> AppManifest:
    """返回开盘啦的初始占位配置。

    注意：这里故意不猜测包名、activity、host 和 path。
    这些值必须在真机首轮验证后再填。
    """

    return AppManifest(
        app_name="开盘啦",
        package_name=None,
        launch_activity=None,
        db_path="data/kaipanla.db",
        proxy_port=8080,
        target_hosts=set(),
        target_paths=[],
        page_markers={
            "home": (),
            "list": (),
            "detail": (),
            "login": (),
            "captcha": (),
            "unknown_dialog": (),
        },
        notes=[
            "首次验证时先确认包名、启动页、首页和目标列表页。",
            "网络层优先看是否存在标准 JSON 接口或 WebSocket。",
            "如果出现证书校验失败，先记录，不要直接硬改解析器。",
        ],
    )
