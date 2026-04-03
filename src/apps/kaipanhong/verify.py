"""
开盘红运行结果校验入口。

当前阶段先复用开盘啦 verify 逻辑，只补 app adapter 边界。
后续若开盘红需要不同的产物检查或 evidence 摘要，再在此独立实现。

【临时复用说明】
- 当前复用开盘啦的 VerificationResult、render_verification_summary、verify_run
- 这只是工程过渡期的临时方案
- 未来开盘红应：
  1. 建立独立的 verify 逻辑
  2. import 自己的 exploration 模块
  3. 使用自己的 default preset
  4. 不应长期依赖开盘啦的 verify 实现

【APP-SPECIFIC 边界】
- 即使当前复用开盘啦逻辑，也应通过此 adapter 入口调用
- 不应在其他模块直接 import 开盘啦的 verify
- 保持 adapter 边界清晰，为未来独立演化做准备

【依赖关系警告】
- 开盘啦的 verify.py 依赖开盘啦特有的 exploration 模块和 default preset
- 当前复用意味着开盘红间接依赖开盘啦的 exploration
- 这是过渡期的临时妥协，未来必须解耦

【禁止的内容】
- 长期依赖开盘啦的 exploration 模块
- 使用开盘啦特有的 TaskSpec.market_emotion_default() 作为 fallback
- 对 db_path 的假设（应有开盘红独立的数据库路径）
"""

from src.apps.kaipanla.verify import VerificationResult, render_verification_summary, verify_run

__all__ = ["VerificationResult", "render_verification_summary", "verify_run"]
