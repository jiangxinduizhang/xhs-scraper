# 开盘啦接续说明

当前对外应以以下文件为准：

- `skills/openclaw-kaipanla-bridge/SKILL.md`
- `Docs/kaipanla-bridge-architecture.md`
- `Docs/kaipanla-implementation-round1.md`

## 当前主线

项目当前主线已经明确为：

- **AI / OpenClaw 负责理解、识别、判断、控制下一步与对外解释**
- **Kaipanla bridge / runtime 负责执行动作、抓包、落盘、回读、输出事实证据**

bridge 应被理解成：
- 执行工具
- 证据采集器
- 产物回读器

而不是：
- 页面语义识别器
- 候选判定器
- promote 决策器
- ask-human 业务判断器

## 当前推荐入口

- 执行/取证：`scripts/kpl_tool.py`
- 对外使用说明：`skills/openclaw-kaipanla-bridge/SKILL.md`
- 架构边界：`Docs/kaipanla-bridge-architecture.md`

## 当前约束

如果后续实现与旧 run / 旧报告 / 旧文档中的术语冲突，
以**当前 skill 与架构文档**为准，不要再被旧字段或旧成功口径带偏。
