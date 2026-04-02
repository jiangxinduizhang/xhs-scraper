# 开盘啦 Round2 实施方案（AI 驱动多轮 exploration 闭环）

> Round2 目标：让 OpenClaw 能把用户自然语言意图转成 exploration loop，并完成 continue / stop / ask-human / success 的 AI 控制闭环。

---

## 0. 目标

Round2 只解决一件事：

**用户通过自然语言提出探索型任务后，AI 能驱动 bridge 多轮调用，并对用户自然语言交付结果。**

---

## 1. 范围

### 要做
1. 自然语言意图分流：registered vs exploration
2. exploration loop controller
3. round-to-round evidence comparison
4. ask-human gate
5. 自然语言结果交付模板
6. 基于真实任务的 2+ 轮闭环验证

### 不做
- promote 成 registered
- 页面业务语义增强
- 更多页面扩展
- bridge 自己做判断

---

## 2. P0 实施项

### P0-1. 自然语言 → 模式选择
AI 必须能判断：
- 已知稳定任务 → registered
- 未知/需验证/证据不足 → exploration

### P0-2. exploration loop controller
AI 每轮必须输出：
- 本轮目标
- 本轮最小动作
- 为什么做这一轮
- 何时停止

### P0-3. round 对比
每轮后必须比较：
- UI 是否更接近目标
- 请求是否更聚焦
- 结构是否更强
- 是否仍主要是公共噪声

### P0-4. ask-human gate
满足以下任一触发 ask human：
- 成功标准不清
- 连续两轮无增信
- 证据冲突
- 下一轮只能靠猜

### P0-5. 对外自然语言交付
回复用户时必须包含：
- 做了什么
- 当前看到什么证据
- 为什么继续/停止
- 是否达成目标
- 若未达成，差在哪

---

## 3. 改造对象

### SKILL
- 更新 `skills/openclaw-kaipanla-bridge/SKILL.md`
- 强化自然语言任务入口、loop 规则、ask-human 模板

### AI 调用逻辑
- 固化探索型任务的调用顺序
- 形成“理解 → 调用 → 回读 → 决策 → 回复”的模板

### 文档/案例
- 补至少一个真实 2+ 轮案例

---

## 4. 验收

Round2 完成必须同时满足：
1. 用户一句自然语言可触发 exploration
2. AI 能解释为什么走 exploration
3. 至少一个真实任务完成 2+ 轮 loop
4. AI 能解释继续/停止原因
5. AI 能 ask human
6. AI 输出的是自然语言结果，不是内部 artifact
