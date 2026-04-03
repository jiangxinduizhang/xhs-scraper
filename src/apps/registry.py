"""
多 APP 注册表。

这一层只负责声明“当前支持哪些 app，以及它们的基础默认值”。
不负责页面语义判断，也不负责执行决策。
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib


@dataclass(frozen=True, slots=True)
class AppSpec:
    app_id: str
    app_name: str
    package_name: str
    launch_activity: str
    db_path: str
    adapter_module: str
    skill_label: str


APP_SPECS: dict[str, AppSpec] = {
    "kaipanla": AppSpec(
        app_id="kaipanla",
        app_name="开盘啦",
        package_name="com.aiyu.kaipanla",
        launch_activity=".splash.SplashActivity",
        db_path="data/kaipanla.db",
        adapter_module="src.apps.kaipanla",
        skill_label="openclaw-kaipanla-bridge",
    ),
    "kaipanhong": AppSpec(
        app_id="kaipanhong",
        app_name="开盘红",
        package_name="com.aiyu.kaipanhong",
        launch_activity=".splash.SplashActivity",
        db_path="data/kaipanhong.db",
        adapter_module="src.apps.kaipanhong",
        skill_label="openclaw-kaipanla-bridge",
    ),
}

ALIASES = {
    "开盘啦": "kaipanla",
    "kaipanla": "kaipanla",
    "kpl": "kaipanla",
    "开盘红": "kaipanhong",
    "kaipanhong": "kaipanhong",
    "kph": "kaipanhong",
}


def normalize_app_name(name: str | None) -> str:
    value = (name or "kaipanla").strip()
    if not value:
        return "kaipanla"
    return ALIASES.get(value, ALIASES.get(value.lower(), value.lower()))


def get_app_spec(name: str | None) -> AppSpec:
    normalized = normalize_app_name(name)
    if normalized not in APP_SPECS:
        raise ValueError(f"unsupported app: {name}")
    return APP_SPECS[normalized]


def list_apps() -> list[str]:
    return sorted(APP_SPECS.keys())


def load_app_module(name: str | None):
    spec = get_app_spec(name)
    return importlib.import_module(spec.adapter_module)


def load_app_manifest(name: str | None):
    module = load_app_module(name)
    return module.build_stub_manifest()


def load_page_spec(app: str | None, page: str | None):
    module = load_app_module(app)
    return module.get_page_spec(page)


def build_app_task_defaults(app: str | None, page: str | None) -> dict:
    module = load_app_module(app)
    return module.build_task_defaults(page)


def list_app_pages(app: str | None) -> list[str]:
    module = load_app_module(app)
    return module.list_pages()
