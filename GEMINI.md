# 小红书数据采集 — 项目规则 (GEMINI)

## 技术栈
- **UI 自动化**: uiautomator2 (Python 3.13)
- **数据拦截**: mitmproxy (mitmdump addon)
- **存储**: SQLite (`data/xiaohongshu.db`)
- **通信**: ADB USB Tunnel (禁止 WiFi)

## 核心约束
- **禁止使用 resourceId**: 所有 ID 已混淆，改用 Activity 名称、Text 或 Description 定位。
- **实测数据优先**: API 解析必须基于 `tests/fixtures/` 中的实测抓包格式。
- **无设备测试**: 单元测试必须使用 `MagicMock`，确保 CI 环境可运行。
- **USB 代理**: 必须运行 `adb reverse tcp:8080 tcp:8080` 确保手机流量经过 Mac。

## 关键文件
- `src/proxy/addon.py`: 拦截逻辑
- `src/proxy/parser.py`: 解析逻辑
- `src/storage/db.py`: 数据库操作
- `src/controller/state.py`: 页面检测
- `src/orchestrator.py`: 主调度循环

## 开发流程
1. **实现**: 编写代码 + 单元测试 (`pytest tests/unit/`)。
2. **验证**: 真机端到端测试。
3. **提交**: 格式 `fix:/feat:/refactor: <描述>`。
