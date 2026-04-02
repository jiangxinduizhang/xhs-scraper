# 开盘啦落地改造总实施方案（面向最终自然语言闭环）

> 本文档补全“最新落地改造方案”的实施全貌。
> 它不是重复 round1 文档，而是把 **Round1 / Round2 / Round3** 串成一个完整交付路径。
>
> 最终目标只有一个：
>
> **用户通过 OpenClaw 提出自然语言意图，AI 能理解该意图，选择合适桥接模式，驱动 bridge 多轮调用，必要时 ask human，最终达成任务或明确说明未达成。**

---

## 0. 最终目标（唯一验收口径）

最终不是验收“某个 CLI 命令能跑”，也不是验收“某个 run.json 更完整”。

最终验收口径是：

1. 用户以自然语言表达任务意图
2. OpenClaw/AI 能正确理解意图类型
3. AI 能判断应走 registered 还是 exploration
4. AI 能驱动 bridge 执行一轮或多轮任务
5. bridge 能返回足够事实证据
6. AI 能基于证据决定：
   - 继续下一轮
   - 停止
   - ask human
   - 宣告成功
7. 最终对用户输出自然语言结果，而不是内部实现细节

一句话：

**验收的是“自然语言任务闭环”，不是“底层能力片段”。**

---

## 1. 分轮实施总览

## Round1：最小执行与证据底座

目标：
- 让 bridge 不再只会“一次跑完就退出”
- 让 exploration 有 round 化输入
- 让 bridge 返回事实型 evidence bundle v2
- 让 verify/report 去结论化

产出：
- round schema
- action-level evidence
- before/after UI evidence
- request/structure/artifact facts
- exploration verify/report 新口径
- CLI 暴露 round/control 输入

一句话：

**Round1 解决“AI 有没有材料继续判断”。**

状态：**已完成**

---

## Round2：AI 驱动多轮 exploration 闭环

目标：
- 让 OpenClaw 能把用户自然语言意图转换成 exploration 控制循环
- 让 AI 在每轮后基于 evidence bundle 决定下一步
- 让 ask-human / continue / stop / success 有明确协议
- 让 exploration 不再只是“一轮工具调用”，而是“AI 主导的多轮任务控制”

产出：
- 自然语言意图 → exploration plan 的调用逻辑
- exploration loop controller
- round-to-round 比较与增信判断
- ask-human gate
- success/stop 判定模板
- 对外自然语言结果生成规则

一句话：

**Round2 解决“AI 能不能真正把 exploration 跑成闭环”。**

状态：**未完成，需立即补齐文档与实施**

---

## Round3：registered promote 与稳定任务交付

目标：
- 把已验证稳定的 exploration 路径沉淀成 registered 任务
- 让高频任务不必每次重新探索
- 让“抓龙虎榜/情绪/板块/个股”等任务逐步变成稳定自然语言交付能力

产出：
- promote 条件
- reusable recipe 到 registered 的迁移流程
- registered 验证门槛
- registered 失败时回退 exploration 的策略

一句话：

**Round3 解决“怎么从探索走向稳定交付”。**

状态：**未完成**

---

## 2. 为什么 Round1 完成了，最终目标还没完成

因为 Round1 完成的是：

- bridge 会执行
- bridge 会取证
- exploration bundle 能被回读
- verify/report 不乱下结论

但最终目标还要求：

- 自然语言意图理解
- AI 自动选择工作模式
- AI 自动决定下一轮
- AI 自动 ask human
- AI 对外交付自然语言结果

所以：

- **Round1 完成 = 底座完成**
- **最终自然语言任务闭环完成 = 至少还需要 Round2，通常还要 Round3**

---

## 3. Round2：详细实施方案

## 3.1 Round2 的唯一目标

让下面这类用户意图真正可执行：

- “去开盘啦帮我看最新龙虎榜”
- “帮我判断现在到底有没有抓到龙虎榜主块”
- “如果没到目标页你就继续探索，必要时再问我”

Round2 不要求一开始就“稳定抓到所有页面”，但必须让 OpenClaw：

- 能理解这些自然语言意图
- 能把它们变成可控的 exploration loop
- 能自然语言汇报当前状态与下一步

---

## 3.2 Round2 的职责边界

### AI / OpenClaw 负责新增实现

必须新增：
- 意图分流：registered vs exploration
- 最小轮次计划生成
- 每轮后的 evidence 解读
- 下一轮动作决策
- ask-human gate
- stop/success 判定
- 自然语言交付封装

### bridge / runtime 保持职责不变

仍然只负责：
- 执行动作
- 采集证据
- 落盘/回读

bridge 不新增：
- 页面语义判断
- ask-human 业务判断
- success/promote 判定

### SKILL 负责补齐操作手册

必须把以下规则写成稳定使用规范：
- 哪些自然语言任务默认走 registered
- 哪些默认走 exploration
- exploration 每轮目标如何收敛
- 连续多少轮无增信必须停止或 ask human
- 什么时候允许向用户说“成功”

---

## 3.3 Round2 必须落地的能力

### P0-1. 自然语言意图分流

输入：用户自然语言
输出：
- `mode=registered`
- 或 `mode=exploration`
- 以及原因说明

最小要求：
- 对“已知稳定任务”优先走 registered
- 对“未知页面 / 需要验证 / 已知 preset 证据不对”优先走 exploration
- 不允许把模糊自然语言直接原样丢给 bridge

验收：
- AI 能清楚解释“为什么这次走 exploration/registered”

---

### P0-2. exploration loop controller

AI 必须能基于一轮 evidence bundle 自动决定：
- 下一轮目标
- 下一轮最小动作
- 是否继续
- 是否停止
- 是否 ask human

最小要求：
- 每轮只解决一个核心不确定性
- 连续两轮无增信要触发 stop/ask-human 判断
- 到 max_rounds 必须停止，不得机械重跑

验收：
- 存在至少一个真实任务，从自然语言触发后走完 2+ 轮 exploration

---

### P0-3. round-to-round evidence comparison

AI 必须显式比较：
- UI 是否变化
- 新请求是否比上一轮更聚焦
- 新结构是否更接近目标
- 当前是否仍然主要是公共噪声

最小要求：
- 不再只看单轮结果
- 每轮都要能回答“为什么继续/为什么不继续”

验收：
- 回复中能清楚解释“与上一轮相比，哪里增信/没增信”

---

### P0-4. ask-human gate

AI 必须在这些场景主动 ask human：
- 用户成功标准不清
- 连续两轮无增信
- UI 和请求证据冲突
- 下一轮只能靠业务猜测
- 是否接受半稳定结果需要用户拍板

验收：
- ask human 是 AI 基于证据触发，不是 bridge 输出字段触发

---

### P0-5. 自然语言结果交付

AI 对用户的输出必须是：
- 当前做了什么
- 看到了什么证据
- 为什么继续 / 为什么停止
- 是否达成目标
- 如果未达成，差在哪

禁止交付为：
- 纯 task json
- 纯 run json
- 纯命令说明
- 纯内部字段罗列

验收：
- 用户能不看底层 artifact，也能理解当前状态

---

## 3.4 Round2 推荐改造对象

### A. `skills/openclaw-kaipanla-bridge/SKILL.md`

P0：补成“自然语言 → AI loop”手册，至少增加：
- 意图分流规则
- exploration loop 模板
- 每轮结果解释模板
- ask-human 模板
- success/stop 模板

### B. OpenClaw 调用逻辑（AI 层）

P0：落实以下使用协议：
- 先理解用户意图
- 再决定 mode
- 若 exploration，则生成最小 round plan
- 调 bridge
- 回读 evidence
- 判断下一轮
- 最后自然语言回复用户

> 这部分不一定都落在当前仓库代码里，但必须有清晰实施说明与验收案例。

### C. 需要补的实施文档

新增：
- `Docs/kaipanla-implementation-round2.md`

内容至少要有：
- scope
- 不做什么
- 文件/层级责任
- loop 协议
- ask-human 规则
- 完成定义

---

## 3.5 Round2 完成定义

Round2 完成，必须同时满足：

1. 用户自然语言可触发 exploration
2. AI 能解释为什么走 exploration
3. 至少一个真实任务跑过 2+ 轮 loop
4. AI 能在每轮后解释继续/停止原因
5. AI 能在必要时 ask human
6. AI 能自然语言交付结果，而不是只回内部 artifact

未满足前，不得宣称：
- “自然语言任务闭环已完成”
- “用户已经可以稳定通过 OpenClaw 完成该类任务”

---

## 4. Round3：详细实施方案

## 4.1 Round3 的唯一目标

把已验证稳定的探索路径沉淀成 registered 能力，让高频任务从“探索驱动”升级为“稳定交付”。

---

## 4.2 Round3 必须落地的能力

### P0-1. promote 判定标准

必须明确：只有同时满足以下条件，才可 promote 为 registered：
- 多轮 exploration 路径可复现
- 关键证据结构稳定
- 成功不再主要依赖人工解释
- 多次 run 结果一致

### P0-2. reusable recipe → registered 流程

要把以下内容沉淀：
- 稳定动作顺序
- 推荐等待时长
- 常见噪声基线
- 关键证据模式
- registered verify 门槛

### P0-3. registered 回退 exploration

若 registered 失效，AI 必须能：
- 识别当前结果不像既定目标
- 回退到 exploration
- 继续自然语言闭环，而不是直接失败退出

---

## 4.3 Round3 完成定义

Round3 完成，必须同时满足：

1. 至少一个页面从 exploration 成功 promote 为 registered
2. 用户可用自然语言稳定触发该 registered 任务
3. 任务失败时可自动回退 exploration
4. 结果仍由 AI 自然语言解释

完成后，才可以开始宣称：

**OpenClaw 已能对部分开盘啦任务提供稳定自然语言交付。**

---

## 5. 总体进度（截至当前）

## 文档
- `Docs/kaipanla-bridge-architecture.md`：已完成
- `Docs/kaipanla-implementation-round1.md`：已完成
- `Docs/kaipanla-round1-code-plan.md`：已完成
- `Docs/kaipanla-implementation-master-plan.md`：本文档，新增
- `Docs/kaipanla-implementation-round2.md`：**未完成，待补**
- `Docs/kaipanla-implementation-round3.md`：**未完成，待补**

## 实现
- Round1 Step1：已完成
- Round1 Step2：已完成
- Round1 Step3：已完成
- Round2：未开始系统化实施
- Round3：未开始

---

## 6. 下一步执行顺序（不发散）

### 立即要做
1. 补 `Docs/kaipanla-implementation-round2.md`
2. 补 `Docs/kaipanla-implementation-round3.md`
3. 更新 `SKILL.md`，使其直接面向“自然语言任务闭环”
4. 再进入 Round2 实施

### 暂不做
- 页面特化增强
- 自动业务识别增强
- 大规模新增页面
- 过早优化 registered 细节

---

## 7. 最终判断口径

以后回答“完成没有”时，必须先说清是在问哪一层：

### 若问 Round1 文档是否完成
答：**已完成**

### 若问最终用户意图是否完成
答：**未完成，至少还需要 Round2，通常还需要 Round3**

这是本方案之后的唯一统一口径。
