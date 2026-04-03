"""
公共数据结构与工具层。

这一层提供可被所有 app adapter 复用的数据结构定义和通用工具。

【公共层边界 - 可以被所有 app 复用】
- TaskSpec 和 RunResult 的数据结构定义（字段定义通用化）
- 通用工具方法（如时间格式化、路径处理）

【不允许的内容】
- 任何 app-specific 的默认值（如 package_name、launch_activity）
- 任何 app-specific 的解析逻辑（如 XHSParser）
- 任何 app-specific 的锚点或判定逻辑

【与 app adapter 的关系】
- app adapter 导入公共数据结构，然后添加 app-specific 工厂方法
- app adapter 可以扩展公共数据结构，但不应改变公共层的定义
- 公共层不依赖任何 app adapter
"""

from src.common.task import TaskSpec, RunResult

__all__ = ["TaskSpec", "RunResult"]