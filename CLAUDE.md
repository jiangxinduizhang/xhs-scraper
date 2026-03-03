# 小红书数据采集 — 项目规则

## 项目简介
ADB + mitmproxy 小红书数据采集系统。通过 USB 代理拦截 API 响应，解析后存入 SQLite。
- 架构文档：`Docs/00-架构总览.md` ~ `Docs/06-Midscene异常处理.md`
- Phase 1 报告：`Docs/Phase1-总结报告.md`

## 技术栈（不可协商）
| 层 | 选型 |
|---|---|
| UI 自动化 | uiautomator2 (Python) |
| 数据拦截 | mitmproxy (mitmdump addon) |
| 存储 | SQLite |
| 设备通信 | ADB (USB tunnel, NOT WiFi) |
| 语言 | Python 3.13 |

## 关键路径文件
修改以下文件须走 Codex Review：
- `src/proxy/addon.py` — mitmproxy 中间件
- `src/proxy/parser.py` — API 响应解析（实测格式，勿臆测）
- `src/storage/db.py` — SQLite 操作
- `src/controller/state.py` — 页面状态检测（基于 activity 名称）
- `src/orchestrator.py` — 主调度循环

## 模型分工
- **编写代码 & 测试**：使用 Sonnet 模型（子代理 `subagent_type` 或 `model: sonnet`）
- **规划 & Review**：使用 Opus 模型（主会话）

## 实施流程
1. **规划（Opus）** → 编写蓝图，明确改动范围
2. **实现（Sonnet）** → 编写代码 + 测试（`python3 -m pytest tests/unit/ -q` 必须全绿）
3. **Review** → 关键路径文件改动后，通过 `Skill("skill-codex")` 调用 Codex 进行 Review
4. **修复（Sonnet）** → P1 问题立即修复；P2 评估后决定；主观建议升级给 boss
5. **提交** → Review 通过后提交，格式见下

## 硬性约束
- 所有 XHS resource-id 已混淆（`0_resource_name_obfuscated`），禁止用 resourceId 定位元素
- API 格式必须基于实测抓包，不可凭文档/猜测（实测格式记录在 memory/MEMORY.md）
- 代理必须走 `adb reverse` USB tunnel（手机与 Mac 不同子网）
- 单元测试必须无设备依赖（用 MagicMock + TYPE_CHECKING）
- 不自动 `git add -A`，只暂存本次改动的文件

## 提交格式
```
fix:/feat:/refactor: <简洁描述>

Generated with [Claude Code](https://claude.ai/code)
via [Happy](https://happy.engineering)

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Happy <yesreply@happy.engineering>
```
