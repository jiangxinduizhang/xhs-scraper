"""
开盘啦 App 级清单。

这里描述目标 App 的基础信息和待验证项，不放具体抓取实现。

【APP-SPECIFIC 边界 - 这是开盘啦特有的 manifest】
- 这个文件是开盘啦特有的应用清单
- 不应被视为通用的多 app manifest
- build_stub_manifest() 返回开盘啦的配置
- 包含开盘啦特有的 package_name、launch_activity、target_hosts、target_paths

【禁止跨 app 复用的内容】
- build_stub_manifest() 的具体配置值
- package_name="com.aiyu.kaipanla"
- launch_activity=".splash.SplashActivity"
- target_hosts 和 target_paths 的具体值

如果其他 app（如开盘红）需要类似 manifest：
1. 应建立独立的 manifest.py
2. 使用自己的 package_name、launch_activity
3. 使用自己的 target_hosts、target_paths
4. 不应复用此文件的任何具体配置值

【与多 app bridge 的关系】
- 多 app bridge 通过 registry.load_app_manifest(name) 分发
- registry 会调用对应 app adapter 的 build_stub_manifest()
- 此文件是开盘啦的具体 manifest 实现
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
    """返回开盘啦的初始占位配置。"""

    return AppManifest(
        app_name="开盘啦",
        package_name="com.aiyu.kaipanla",
        launch_activity=".splash.SplashActivity",
        db_path="data/kaipanla.db",
        proxy_port=8080,
        target_hosts={
            "applhb.longhuvip.com",
            "apparticle.longhuvip.com",
            "apphwhq.longhuvip.com",
            "apppage.longhuvip.com",
            "apphotfix.longhuvip.com",
        },
        target_paths=[
            "/w1/api/index.php",
            "/w44/web/index.html",
            "/hotfix/path",
        ],
        page_markers={
            "home": ("首页", "行情", "自选股", "龙虎榜", "推荐"),
            "list": ("列表", "详情"),
            "detail": ("详情", "评论"),
            "login": ("登录", "注册"),
            "captcha": ("验证码", "安全验证"),
            "unknown_dialog": ("知道了", "稍后再说", "取消"),
        },
        notes=[
            "首次验证时已确认包名、启动页和首页结构。",
            "市场情绪页已抓到真实响应，可作为首个可落库页面。",
            "网络层优先看是否存在标准 JSON 接口或 WebSocket。",
            "如果出现证书校验失败，先记录，不要直接硬改解析器。",
        ],
    )
