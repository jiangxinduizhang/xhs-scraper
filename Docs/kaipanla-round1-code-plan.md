# 开盘啦第一轮代码改造拆解（文件级）

> 目标：把总方案落到可执行的第一轮实现清单。
> 本文档只做拆解，不扩 scope。

---

## 0. 第一轮目标

第一轮只做 4 件事：

1. exploration evidence bundle v2
2. before/after UI + request delta
3. round 化 exploration 输入输出
4. exploration verify/report 改口径

不做：
- 页面语义判断增强
- 自动 promote
- 注册页体系大改
- 更多页面扩展

---

## 1. 文件级拆解

## 1.1 bridge/runtime 层

### A. `src/apps/kaipanla/task.py`

**归属**：bridge/runtime

**P0 改造**：
- 为 exploration task 增加 round 元信息：
  - `round_index`
  - `max_rounds`
  - `session_id`（先可选）
- 增加 action/capture 输入字段：
  - `action_plan`
  - `capture_options`
- 保持 registered 兼容

**为什么属于 bridge**：
- 这是任务契约，不是业务判断

**验收**：
- exploration task json 能稳定带出 round/capture 信息
- registered task 不受影响

---

### B. `src/apps/kaipanla/runner.py`

**归属**：bridge/runtime

**P0 改造**：
- 让 exploration 支持 round 化执行，而不是只跑固定 navigation_steps
- 执行动作前后插入证据采集点：
  - before screenshot
  - after screenshot
  - before ui dump
  - after ui dump
  - before visible text
  - after visible text
  - pre/post request window marker
- step event 改为更事实化：
  - `action_started`
  - `action_finished`
  - `found`
  - `executed`
  - `error`
- 不新增业务结论字段

**P1 改造**：
- request 窗口与动作精确绑定
- 多动作场景的 delta 汇总

**为什么属于 bridge**：
- 这是执行与证据采集能力

**验收**：
- 一轮 exploration 至少能输出一个 before/after 证据对
- step events 能看出动作成功/失败，不混业务判断

---

### C. `src/controller/device.py`

**归属**：bridge/runtime

**P0 改造**：
- 增加最小 UI 证据能力：
  - screenshot
  - dump_hierarchy/ui dump
  - visible text 抽取
- 为动作结果返回结构化状态

**P1 改造**：
- 提供 tap_coord / richer selector 支持
- 提供更明确的元素未找到原因

**验收**：
- 环境支持时，能稳定落 before/after screenshot + ui dump
- 环境不支持时，能优雅降级，不把缺失说成成功

---

### D. `src/apps/kaipanla/exploration.py`

**归属**：bridge/runtime

**P0 改造**：
- 重构为 evidence bundle v2 生成器
- 输出：
  - `action_facts`
  - `ui_facts`
  - `request_facts`
  - `structure_facts`
  - `artifact_facts`
  - `round_index`
  - `max_rounds`
  - `evidence_status`
- 去掉依赖 `_reached` 的伪 post-navigation 逻辑
- 改成基于动作时间点的 pre/post 窗口分析
- `candidate_structures` / `noise_structures` 只保留事实归类

**P1 改造**：
- 增加 first_seen_after_action_ms
- 噪声基线机制

**验收**：
- 生成的新 bundle 不含页面成功结论
- 能正确反映 pre/post 证据差异

---

### E. `src/apps/kaipanla/verify.py`

**归属**：bridge/runtime

**P0 改造**：
- exploration 模式只输出：
  - `evidence_complete`
  - `evidence_partial`
  - `evidence_insufficient`
- selected snapshot 改成 evidence snapshot，不暗示页面成功

**验收**：
- exploration verify 再也不出现 verified/success/reached 语义

---

### F. `src/apps/kaipanla/report.py`

**归属**：bridge/runtime

**P0 改造**：
- exploration report 改成探测报告口径：
  - 做了什么
  - 新增了什么证据
  - 当前主要候选结构
  - 当前主要噪声结构
  - 当前不确定性
- 不写“页面抓取完成”“已进入目标页主块”

**验收**：
- exploration report 是探测报告，不是结果报告

---

### G. `scripts/kpl_tool.py`

**归属**：bridge/runtime 对外 CLI

**P0 改造**：
- expose round/capture_options 参数
- explore 路径支持显式 round 输入
- pretty/help 文案改成新口径

**P1 改造**：
- 若后续 session 化，支持 session id 参数

**验收**：
- CLI 能发起一轮带 round/capture_options 的 exploration

---

## 1.2 AI / OpenClaw 层

> 第一轮主要是逻辑约束，不一定全部写到这个仓库代码里，但必须明确承担。

### A. AI 控制协议（文档/调用逻辑）

**归属**：AI / OpenClaw

**P0**：
- 每轮只解决一个不确定性
- 每轮都要能回答：为什么继续？
- 没有增信理由就不继续
- 只有 AI 决定 ask human / success / reuse

**验收**：
- 在真实探索中，回复里能明确说明继续/停止的理由

---

## 1.3 SKILL 层

### A. `skills/openclaw-kaipanla-bridge/SKILL.md`

**归属**：SKILL

**P0 已补，但需对照实现复核**：
- registered vs exploration 选择规则
- loop 规则
- ask-human 规则
- success 规则
- reuse/promote 规则

**下一步需要做的不是继续扩写，而是确保与实现一致。**

**验收**：
- skill 描述不超前，不虚构 bridge 能力

---

## 2. 建议实施顺序

### Step 1
先改：
- `task.py`
- `device.py`
- `runner.py`

理由：
- 先把“能采到什么证据”补齐

### Step 2
再改：
- `exploration.py`
- `verify.py`
- `report.py`

理由：
- 再把证据组织和口径改对

### Step 3
最后改：
- `scripts/kpl_tool.py`
- tests

理由：
- 最后暴露新接口并锁定行为

---

## 3. 第一轮测试清单

### 单测
- exploration task schema 序列化/反序列化
- evidence bundle v2 必填字段
- exploration verify 新口径
- exploration report 新口径
- pre/post window 差分逻辑

### 真实 run
至少验证一次：
- before/after screenshot（若环境支持）
- before/after ui dump（若环境支持）
- request delta
- evidence_status
- 不出现业务结论字段

---

## 4. 完成定义

第一轮完成，必须同时满足：
- exploration evidence bundle v2 可生成
- before/after UI + request delta 可见
- round 化 exploration 可执行
- exploration verify/report 已去结论化
- SKILL 与实现口径一致

未满足前，不进入：
- 页面特化增强
- 自动 promote
- registered 深度重构
