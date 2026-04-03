"""
开盘红运行报告入口。

当前阶段先复用开盘啦报告实现，先把 app-aware 分流入口补齐。
等开盘红出现独有页面摘要或报告结构，再在此独立分叉。

【临时复用说明】
- 当前复用开盘啦的 build_page_summary、render_run_report、write_run_report
- 这只是工程过渡期的临时方案
- 未来开盘红应：
  1. 建立独立的报告生成逻辑
  2. import 自己的 exploration 模块
  3. 不应长期依赖开盘啦的 report 实现

【APP-SPECIFIC 边界】
- 即使当前复用开盘啦逻辑，也应通过此 adapter 入口调用
- 不应在其他模块直接 import 开盘啦的 report
- 保持 adapter 边界清晰，为未来独立演化做准备

【依赖关系警告】
- 开盘啦的 report.py 依赖开盘啦特有的 exploration 模块
- 当前复用意味着开盘红间接依赖开盘啦的 exploration
- 这是过渡期的临时妥协，未来必须解耦

【禁止的内容】
- 长期依赖开盘啦的 exploration 模块
- 使用开盘啦特有的 evidence bundle 结构（应有开盘红独立结构）
"""

from src.apps.kaipanla.report import build_page_summary, render_run_report, write_run_report

__all__ = ["build_page_summary", "render_run_report", "write_run_report"]
