"""
开盘红 exploration 判定入口。

当前阶段先复用开盘啦 judger，避免在多 app 重整初期误伤已验证的开盘啦经验。
这个文件的存在本身就是边界：以后若开盘红锚点/噪声模式不同，应在此独立演化。

【临时复用说明】
- 当前复用开盘啦的 Judgement、JudgementBundle、judge_exploration
- 这只是工程过渡期的临时方案
- 未来开盘红应：
  1. 建立独立的锚点集合（HOME_FEED_HINTS、DRAGON_TIGER_PAGE_HINTS 等）
  2. 编写独立的判定逻辑（基于开盘红 UI 特征）
  3. 不应长期依赖开盘啦的 judger 实现

【APP-SPECIFIC 边界】
- 即使当前复用开盘啦逻辑，也应通过此 adapter 入口调用
- 不应在其他模块直接 import 开盘啦的 judgers
- 保持 adapter 边界清晰，为未来独立演化做准备

【禁止的内容】
- 直接复用开盘啦的锚点集合（应建立开盘红独立的集合）
- 直接复用开盘啦的判定逻辑（应基于开盘红 UI 特征重写）
- 使用开盘啦特有的 HTML 编码文本特征

【特别警告】
- 开盘啦的 judger 包含大量开盘啦特有的 UI 文本特征
- 这些特征不应被用于判定开盘红页面
- 如果直接复用可能导致误判
"""

from src.apps.kaipanla.judgers import Judgement, JudgementBundle, judge_exploration

__all__ = ["Judgement", "JudgementBundle", "judge_exploration"]
