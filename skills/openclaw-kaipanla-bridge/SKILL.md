---
name: openclaw-kaipanla-bridge
description: "开盘啦通用采集桥：用于执行、校验、回读和探索用户指定的开盘啦 APP 采集任务。当用户要抓取开盘啦里的市场情绪、排行、连板、资金、题材、个股、板块、龙虎榜，查询最近一次运行状态，读取最新结果，或先探索某个页面/区域怎么抓时触发。"
---

# 开盘啦通用采集桥

这个 skill 不是“某几个 preset 的说明书”，而是一个**分层的开盘啦采集桥**：

- 已注册页面：稳定执行、稳定验真
- 探索模式：先摸清页面怎么抓，再决定要不要沉淀
- 回读/状态：消费已有运行结果，不重复抓取

一句话边界：

**OpenClaw 负责理解目标、选择策略、消费结果；Kaipanla runtime 负责执行页面动作、抓包解析、产出证据、完成验真。**

---

## 1. 职责边界

### OpenClaw 负责

- 理解自然语言请求
- 判断这次是：
  - `capture_registered`
  - `capture_exploratory`
  - `read_latest`
  - `read_report`
  - `status`
  - `verify`
  - `promote_candidate`（后续可扩）
- 决定走已注册页面、探索模式，还是回读已有结果
- 读取结构化结果后做人话解释
- 判断某次 exploration 是否值得沉淀为 registered page

### Kaipanla runtime 负责

- 接收明确任务协议
- 执行导航、抓包、解析、落盘
- 产出：
  - `run.json`
  - `task.json`
  - `report.md`
  - `raw jsonl`
  - `db`
  - `step_events`
- 用 `verify` 做闭环验真
- 在 exploration 模式下输出候选证据：
  - `candidate_keys`
  - `likely_noise_keys`
  - `navigation_reached`
  - `recommendation`
  - `readiness_score`
  - `readiness_reasons`
  - `recommended_page_name`（仅弱归因，不是最终判断）

### bridge 默认不该做

除非人类明确要求，否则不要把以下能力塞进 runtime：

- 开放式自然语言理解
- 替用户猜真实意图
- 自行宣布“这个页面已经正式支持”
- 投资判断 / 复盘观点 / 交易建议
- 为一次性需求过度产品化
- 把 bridge 变成 AI 决策引擎

---

## 2. 能力分层

### A. registered reusable pages/tasks

适合高频、稳定、已知、可验证的任务。

当前心智应是：
- `market_emotion` 已属于这一层
- `market_radar` / `market_featured` / `dragon_tiger` 只有在稳定后才进入这一层

这一层的成功定义：

- 有明确 task/page spec
- 有稳定导航
- 有页面级 verify
- `verify=verified`
- 报告可读
- 可重复执行

### B. composite tasks

适合把多个已知能力拼成一个任务，例如：
- 热点 + 资金 + 排行
- 跨日对比
- 情绪 + 资金节奏联合观察

组合任务仍依赖已注册能力，不应绕过 verify。

### C. assistant-directed exploration

适合：
- 新页面
- 页面改版
- 入口变化
- 需要先探路、先摸清请求和候选字段

exploration 不是“半成品 registered page”，而是一类正式协议。

exploration 的成功定义是：

- 获得可行动的新证据
- 找到候选字段 / 候选块 / 导航证据
- 帮助 OpenClaw 判断下一步怎么走

**exploration 成功 ≠ 页面已正式支持。**

当前推荐状态语义：
- `not_ready`
- `candidate_found`
- `strong_candidate_evidence`

注意：
- `strong_candidate_evidence` 只表示候选证据较强
- 不表示 runtime 已经决定可以 promote
- promote 与否由 OpenClaw 结合语义与复用价值判断

---

## 3. 什么时候走 registered，什么时候走 exploration

### 走 registered 的情况

当满足以下特征时，优先走已注册页面：

- 页面已注册
- 导航稳定
- verify 规则已存在
- 用户要的是结果，不是探路

典型请求：
- 抓今天市场情绪
- 看最新市场情绪报告
- 抓盘中雷达
- 校验最近一次 run
- 看最新状态

### 走 exploration 的情况

当满足以下特征时，优先走 exploration：

- 新页面
- 页面可能改版
- 当前不能承诺稳定支持
- 用户在问“这个页面怎么抓”
- 用户要先摸清入口、接口、候选字段

典型请求：
- 抓龙虎榜看看能不能形成稳定候选块
- 看行情 tab 某个区域怎么抓
- 先摸清这个页面的数据结构
- 这个页面改版了，重新探一下

---

## 4. 交互心智

始终先判断用户属于哪类意图，再决定执行、回读、校验，还是探索。

### 执行采集

当用户明确要“抓”“采集”“更新”“重跑”“执行任务”时，进入执行路径。

处理原则：
- 目标清楚：直接执行
- 能映射到 registered：直接走 registered
- 暂未注册但目标明确：走 exploration，并明确告诉用户这是探索抓取
- 高歧义时最多只追问一次关键问题

### 查询状态

当用户想知道最近一次任务是否成功、卡在哪、产物在哪时，进入状态路径。

返回应优先包含：
- `status`
- `verify`
- 主要产物路径
- 失败卡点 / error stage

### 读取或解读结果

当用户不是要重跑，而是要消费已有结果时，进入读取路径。

处理原则：
- 优先读最近一次成功且可校验的 run
- 根据需要返回：
  - 状态版
  - 结构化版
  - 人话版
  - 对比版

### promote 判断

当用户问“能不能正式沉淀”“要不要注册成正式页面”时：
- 由 OpenClaw 基于 exploration 结果、稳定性和复用价值判断
- 不要把 runtime 输出直接等价成 promote 决策

---

## 5. 核心动作

优先使用 bridge 提供的稳定动作，而不是让 runtime 接开放式对话。

- `capture`：执行已定义任务并写出产物
- `explore`：执行探索任务并输出 exploration 证据；默认应受有限轮数、self-proof gate、ask-human gate 约束
- `verify`：校验运行是否真的成立，并在 exploration 场景下判断是否仍只能视为候选证据
- `report`：回读运行结果；如果存在 blocker，应明确写出“不能宣称稳定抓到”
- `latest`：查看最近一次运行
- `status`：查看最近一次运行及校验结果
- `ask`：做自然语言到动作/参数的路由建议；不是 runtime 自己做开放式对话理解

---

## 6. 输入输出心智

### `task.json`
至少应表达：
- `task_id`
- `app`
- `page`
- `goal`
- `success_criteria`
- `max_attempts`
- `timeout_sec`

exploration 任务额外关注：
- `target_hint`
- `intent`
- `navigation_hint`（可选）
- `expected_signals`（可选）

### `run.json`
用于 `verify` / `report` / `latest` / `status` 回读。

### exploration 输出应关注

- 是否到达目标区域
- 命中的请求数量
- `candidate_keys`
- `likely_noise_keys`
- `navigation_reached`
- `readiness_score`
- `readiness_reasons`
- `recommendation`
- `recommended_page_name`
- `self_proof_blockers`
- `ask_human`（如命中停点）
- `safe_to_claim_stable_capture`

注意：
- `recommended_page_name` 只是弱归因 / 候选页面判断
- 不是“最终主块已确认”
- 不是“页面已正式支持”
- `strong_candidate_evidence` 也不自动等于“已稳定抓到目标主数据”
- 只要 `self_proof_blockers` 非空，就不应对外宣称“已稳定抓到”

---

## 7. 证据与判定规则

以下产物视为事实来源：

- `runs/<task_id>.task.json`
- `runs/<task_id>.json`
- `reports/<task_id>.md`
- `data/raw/<date>.jsonl`
- `data/kaipanla.db`
- `step_events` inside `run.json`

判定规则：

- `capture` 只表示任务执行过，不表示闭环成功
- `verify` 才是最终判定门
- `verify=verified` 才表示闭环成立
- `step_events` 必须完整，才能证明过程真的发生过
- exploration 的价值在于“新证据”，不是“正式支持承诺”
- exploration 结果必须经过 `self-proof gate`
- 只要存在 `self_proof_blockers`，就应降级为“候选证据”，而不是“已稳定抓到”
- `safe_to_claim_stable_capture=true` 时，才允许对外使用“稳定抓到”这一类口径

---

## 8. 对外承诺边界

可以承诺：

1. 已注册页面可稳定抓取与验真
2. exploration 模式可以帮助摸清新页面怎么抓
3. 页面改版后可以先快速重新探路

不应该承诺：

1. 任意页面立即稳定支持
2. 一次 exploration 成功就等于正式支持
3. runtime 自己会理解无限自然语言和无限页面语义
4. bridge 自己会决定 promote
5. 仅凭 `strong_candidate_evidence` 就能对外宣称“已稳定抓到目标主块”

---

## 9. 当前试用口径

按当前实现，建议这样对外使用：

### 已可试用
- registered page capture / verify / report / latest / status
- exploration-first 抓新页面或不稳定页面
- 输出候选证据供 OpenClaw 判断下一步

### 暂不应过度承诺
- 把 exploration 结果直接当正式产品化支持
- 把 `strong_candidate_evidence` 解释为“可以自动 promote”
- 把 runtime 输出当成最终语义判断
- 在 `self_proof_blockers` 未清空前，对外说“已稳定抓到目标页面主数据”

如果 exploration 已经输出清晰证据，但页面是否值得沉淀仍不确定，允许继续停留在 `exploration-first` 状态。

---

## 10. 默认策略

### 明确请求

如果用户已明确指定页面、模块、结果类型，直接执行或回读，不要多问。

### 泛化但可默认

如果用户表达较泛，例如：
- 抓一下开盘啦最新状况
- 看看今天怎么样

且系统存在默认预设任务，可明确告诉用户：
- 先按默认预设执行（例如市场情绪）
- 如果要改成排行、资金、连板、龙虎榜或其他页面，可以直接指定

### 高歧义请求

如果无法判断用户到底想抓哪个方向，只追问一次最关键问题。

推荐追问方式：
- 你这次想抓哪个方向：市场情绪、排行/连板、资金节奏、龙虎榜，还是你指定的页面？

不要连环追问，不要替用户脑补过多。

### exploration 默认闭环

当进入 exploration 时，默认按“有限自动探索 + 到点刹车”的心智处理：

- 默认不是只跑一轮就下结论
- 允许做 2~3 轮最小调整
- 每轮都必须重新检查证据是否增信
- 如果证据没有改善，或 `self_proof_blockers` 持续存在，应触发 `ask_human`
- `ask_human` 的目标是收窄目标范围，而不是继续盲猜

推荐 ask-human 方式：
- 你要锁定的是页面主列表/主块，还是页面内任意相关数据？

不要无限自动 exploration，不要为了避免提问而硬凑结论。

---

## 11. 输出分层

### 状态版

适合快速确认任务是否跑通。

应包含：
- run id / task id
- `status`
- `verify`
- 主要产物路径
- 失败步骤或错误摘要

### 结构化版

适合程序消费或人工复查。

应优先引用：
- JSON 结果
- 模块统计
- `market_summary`
- `day_compare`
- candidate/noise/readiness 证据字段

### 人话版

适合老板直接阅读。

应输出：
- 简洁结论
- 热点 / 资金 / 风险 / 观察点
- 必要时说明“这是 registered 结果”还是“这是 exploration 证据”

原则：

**摘要是结果消费层，不是采集成功定义。**

---

## 12. 覆盖范围

优先处理这些结构化内容：

- A 股行情
- 板块
- 个股
- 打板 / 连板
- 涨停 / 炸板 / 跌停
- 龙虎榜
- 资金流向
- 市场情绪
- 题材 / 热点

可兼容但不作为主目标：

- 全球入口里的可结构化行情信息
- 首页消息 / 资讯中稳定可抽取的行情提示

不纳入边界：

- 交易执行
- 投资建议
- 通用新闻摘要
- 其他 App
- 需要人工解释的大段文本分析

---

## 13. 定位约定

- 首次使用且无法定位仓库时，先向人类确认 xhs-scraper 仓库根目录的绝对路径。
- 确认后，将该路径写入当前 skill 目录下的 `repo-root.txt`（仅一行，不带解释），用于后续持久化。
- launcher 会优先读取 `repo-root.txt`，再读 `OPENCLAW_KPL_REPO_ROOT` / `KPL_REPO_ROOT`，最后才向上搜索当前工作目录。
- launcher 在定位到仓库根目录后会自动切换到该目录再执行命令。
- 如果命令要显式指定仓库根目录，可用 `--repo-root`。
- 除非人类明确说明仓库迁移或 `repo-root.txt` 已失效，否则不要重复询问路径。

---

## 14. 调用方式

将本 skill 目录放入 OpenClaw 可扫描的 `skills/` 目录后直接使用。

优先使用 bundled launcher：

```bash
bash scripts/kpl_bridge.sh capture --task <task.json>
bash scripts/kpl_bridge.sh explore --task <task.json>
bash scripts/kpl_bridge.sh verify --run <run.json>
bash scripts/kpl_bridge.sh report --run <run.json>
bash scripts/kpl_bridge.sh latest
bash scripts/kpl_bridge.sh status
```

也可以直接调用机器可读桥接：

```bash
python3 scripts/kpl_tool.py capture --task <task.json>
python3 scripts/kpl_tool.py explore --task <task.json>
python3 scripts/kpl_tool.py verify --run <run.json>
python3 scripts/kpl_tool.py report --run <run.json>
python3 scripts/kpl_tool.py latest
python3 scripts/kpl_tool.py status
```

`scripts/run_kpl_task.py` 只用于人工或手动触发。

---

## 15. 不要做

- 不要把某一个 preset 误当成整个 skill 的全部能力
- 不要把“摘要输出”当成采集成功证明
- 不要把一次 exploration 成功当成正式支持
- 不要把 `strong_candidate_evidence` 误当成 promote 决策
- 不要跳过 `verify`
- 不要把 `capture` 当成成功证明
- 不要依赖内部类名、函数名或目录结构作为外部协议
- 不要让 runtime 偷做理解/决策层工作
