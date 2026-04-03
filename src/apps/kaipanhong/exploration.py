"""
开盘红 exploration 证据包入口。

当前阶段先复用开盘啦的 evidence bundle 构建逻辑，
目的是保留旧经验基线，同时给开盘红建立独立 adapter 接口。
后续若开盘红出现独有请求结构或 UI 特征，再在此分叉实现。

【临时复用说明】
- 当前复用开盘啦的 ExplorationResult 和 build_exploration_result
- 这只是工程过渡期的临时方案
- 未来开盘红应：
  1. 建立独立的 NOISE_KEYS（基于开盘红请求结构）
  2. 可能调整请求结构解析逻辑
  3. 不应长期依赖开盘啦的 exploration 实现

【APP-SPECIFIC 边界】
- 即使当前复用开盘啦逻辑，也应通过此 adapter 入口调用
- 不应在其他模块直接 import 开盘啦的 exploration
- 保持 adapter 边界清晰，为未来独立演化做准备

【禁止的内容】
- 直接复用开盘啦的 NOISE_KEYS（应建立开盘红独立的集合）
- 直接复用开盘啦对请求结构的假设（应验证开盘红格式）
"""

from src.apps.kaipanla.exploration import ExplorationResult, build_exploration_result

__all__ = ["ExplorationResult", "build_exploration_result"]
