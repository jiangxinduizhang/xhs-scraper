"""
开盘红任务契约 - 工厂方法层。

这一层继承公共数据结构，添加开盘红特有的工厂方法。

【APP-SPECIFIC 边界 - 这是开盘红特有的工厂方法】
- 这个文件是开盘红特有的任务工厂
- 不应被视为通用的多 app 工厂
- 所有工厂方法都假设 app="kaipanhong"（或通过 registry 填充）
- 提供开盘红特有的预设和默认值覆盖

【依赖关系】
- 继承公共数据结构：from src.common.task import TaskSpec as BaseTaskSpec, RunResult as BaseRunResult
- 使用 registry 的 build_app_task_defaults 和 get_app_spec
- 通过 registry 或显式参数填充 app-specific 配置

【向后兼容】
- TaskSpec 和 RunResult 继承公共数据结构，添加开盘红特有的工厂方法
- 其他模块可以继续导入 TaskSpec 和 RunResult，并使用类方法
- 例如：TaskSpec.market_emotion_default()、TaskSpec.for_preset()、TaskSpec.for_exploration()

【禁止跨 app 复用的内容】
- 所有工厂方法（如 market_emotion_default、for_preset、for_exploration）
- 所有开盘红特有的预设名称和默认值

如果其他 app 需要类似工厂方法：
1. 应建立独立的 task.py
2. 继承公共数据结构：from src.common.task import TaskSpec as BaseTaskSpec
3. 定义自己的工厂方法（如 for_preset、for_exploration）
4. 通过自己的 registry 配置填充 app-specific 参数
5. 不应复用此文件的任何工厂方法

【与多 app bridge 的关系】
- 多 app bridge 的公共数据结构在 src/common/task.py
- 此文件是开盘红特有的工厂层，继承公共数据结构并添加便捷方法
- 其他 app adapter 应继承公共数据结构，然后定义自己的工厂方法
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.common.task import TaskSpec as BaseTaskSpec, RunResult as BaseRunResult
from src.apps.registry import build_app_task_defaults, get_app_spec


@dataclass(slots=True)
class TaskSpec(BaseTaskSpec):
    """
    开盘红任务规格 - 继承公共数据结构，添加工厂方法。

    字段定义来自公共数据结构，工厂方法是开盘红特有的。
    """

    @classmethod
    def market_emotion_default(cls, app: str | None = None) -> "TaskSpec":
        """创建市场情绪任务的默认实例。"""
        return cls.for_preset("market_emotion", app=app)

    @classmethod
    def for_preset(cls, preset: str | None, *, app: str | None = None) -> "TaskSpec":
        """
        根据预设创建任务实例。

        参数：
            preset: 预设名称（如 "market_emotion"、"dragon_tiger"）
            app: app 名称（默认为 "kaipanhong"，可显式指定其他 app）

        返回：
            TaskSpec 实例，填充了开盘红特有的配置
        """
        # 如果 app 未指定，默认为开盘红
        effective_app = app or "kaipanhong"
        app_spec = get_app_spec(effective_app)
        defaults = build_app_task_defaults(app_spec.app_id, preset or "market_emotion")

        # 填充 app-specific 配置
        defaults.setdefault("app", app_spec.app_id)
        defaults.setdefault("package_name", app_spec.package_name)
        defaults.setdefault("launch_activity", app_spec.launch_activity)
        defaults.setdefault("db_path", app_spec.db_path)
        defaults.setdefault("mode", "registered")
        defaults.setdefault("success_criteria", ["artifacts_complete"])

        return cls(**defaults)

    @classmethod
    def for_exploration(
        cls,
        target_hint: str,
        *,
        page: str | None = None,
        preset: str | None = None,
        navigation_hint: str = "",
        app: str | None = None,
    ) -> "TaskSpec":
        """
        创建探索任务实例。

        参数：
            target_hint: 探索目标描述
            page: 页面名称（可选）
            preset: 预设名称（可选）
            navigation_hint: 导航提示（可选）
            app: app 名称（默认为 "kaipanhong"，可显式指定其他 app）

        返回：
            TaskSpec 实例，配置为探索模式
        """
        # 如果 app 未指定，默认为开盘红
        effective_app = app or "kaipanhong"
        app_spec = get_app_spec(effective_app)
        chosen_page = page or preset or "market_emotion"
        base = build_app_task_defaults(app_spec.app_id, chosen_page)

        # 填充 app-specific 配置
        base.setdefault("app", app_spec.app_id)
        base.setdefault("package_name", app_spec.package_name)
        base.setdefault("launch_activity", app_spec.launch_activity)
        base.setdefault("db_path", app_spec.db_path)

        # 探索模式特有配置
        base.update(
            {
                "mode": "exploration",
                "page": chosen_page,
                "preset": preset or chosen_page,
                "goal": f"探索抓取目标:{target_hint}",
                "target_hint": target_hint,
                "success_criteria": [
                    "collect_evidence_bundle",
                    "persist_exploration_artifacts",
                ],
                "output": ["run", "report", "evidence_bundle"],
                "interpretation_style": "evidence_bundle",
                "round_index": 1,
                "max_rounds": 1,
                "session_id": "",
                "action_plan": [],
                "capture_options": {
                    "screenshot_before_after": True,
                    "ui_dump_before_after": True,
                    "visible_text_before_after": True,
                    "focus_post_action_window": True,
                },
                "notes": list(base.get("notes", [])) + [
                    f"探索目标: {target_hint}",
                    f"navigation_hint: {navigation_hint}" if navigation_hint else "navigation_hint: <none>",
                    "runtime_role: execution_only",
                ],
                "next_action_hint": "由 AI 基于 evidence bundle 决定下一步动作",
            }
        )

        return cls(**base)


@dataclass(slots=True)
class RunResult(BaseRunResult):
    """
    开盘红执行结果 - 继承公共数据结构。

    字段定义来自公共数据结构，无额外方法。
    """
    pass


# 为向后兼容，保留旧的导入名称
__all__ = ["TaskSpec", "RunResult"]