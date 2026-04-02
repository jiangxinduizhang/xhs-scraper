# 开盘啦桥接器能力边界与分层方案

## 目标

把开盘啦桥接器从“若干固定 preset 的采集脚本”升级成一个**分层的采集系统**：

- 第一层：探索抓取（assistant-directed exploration）
- 第二层：沉淀复用（registered reusable pages/tasks）

同时明确：

- **桥接器 runtime 应该负责什么**
- **OpenClaw 应该负责什么**
- 两者之间通过什么协议协作
- 哪些能力不该混在一起

---

## 一句话边界

**OpenClaw 负责理解目标、选择策略、消费结果；桥接器 runtime 负责执行页面动作、抓包解析、产出证据、完成验真。**

如果把职责说得更细：

### OpenClaw 应维持的能力

1. **自然语言理解**
   - 理解用户要抓什么
   - 判断这是执行、回读、状态查询，还是探索新页面

2. **任务策略选择**
   - 决定这次应该：
     - 走已注册页面
     - 走探索模式
     - 走历史结果回读
     - 走局部修复/重试

3. **结果消费与解释**
   - 把结构化结果转成人话
   - 做跨页面对比、跨日对比、交易复盘式总结
   - 决定是否值得沉淀为复用能力

4. **沉淀决策**
   - 判断一个页面/链路是否：
     - 高频复用
     - 结构稳定
     - 可验证
     - 值得产品化

5. **研发编排**
   - 当探索失败时，决定下一步要：
     - 改导航
     - 补字段识别
     - 降低承诺
     - 暂不沉淀

### 桥接器 runtime 应维持的能力

1. **任务执行**
   - 根据任务定义执行 UI 导航
   - 启动代理、抓包、采集 raw
   - 写 run/task/report/db

2. **结构化解析**
   - 把 raw 响应解析成统一结构化记录
   - 提供页面级 summary 所需的基础事实

3. **证据产出**
   - run.json
   - task.json
   - report.md
   - raw jsonl
   - db
   - step_events

4. **验真**
   - 判断这次抓取是否真的闭环成立
   - 区分：
     - capture 发生过
     - verified 闭环成立
     - needs_attention 仅部分成立

5. **探索辅助**
   - 在探索模式下输出：
     - 命中的接口
     - 候选关键字段
     - 页面噪声 vs 主数据判断线索
     - 导航是否稳定

### 不应由桥接器 runtime 负责的能力

1. 不负责完整自然语言对话
2. 不负责替用户做投资判断
3. 不负责“猜用户真正想要什么”
4. 不负责无限泛化到任意 App / 任意站点
5. 不负责在没有证据的前提下宣称“支持某页面”

---

## 两层体系

## Layer 1: 探索抓取层（assistant-directed exploration）

### 目标

让 OpenClaw 可以先说“我要去摸这个页面怎么抓”，而不是先要求 runtime 已经有稳定 page spec。

### 适用场景

- 新页面
- 页面结构发生变化
- 旧页面入口变化
- 已注册页面失效，需要重新探路
- 只需要先判断“能不能抓到”

### 输入

探索任务不要求一开始就有完整 page spec，但至少要有：

- `target_hint`：用户说的目标，如“龙虎榜”“异动”“题材排行”
- `intent`：capture / inspect / compare / discover
- `navigation_hint`：可选，由 OpenClaw 提供的初步导航猜测
- `expected_signals`：可选，OpenClaw 认为可能命中的 key / endpoint 线索

### 输出

探索任务应该输出一类独立结果，例如 `exploration_summary`，至少包含：

- 导航是否到达目标区域
- 过程中命中的请求数量
- 命中的候选页面 key
- 候选主字段
- 噪声字段
- 是否建议沉淀
- 建议沉淀时的初始 page spec 草案

### 判定标准

探索成功不等于页面正式支持。

探索层应有自己的状态：

- `explored`
- `explored_with_noise`
- `navigation_failed`
- `request_not_found`
- `candidate_found`
- `ready_to_promote`

也就是说，**探索模式的成功定义是“获得可行动的新证据”，不是“对用户承诺稳定可复用”。**

---

## Layer 2: 沉淀复用层（registered reusable pages/tasks）

### 目标

把高频、稳定、可验证的抓取行为变成正式能力。

### 当前已有雏形

- page registry
- generic runner
- page-specific verify
- page-specific report
- ask route

### 进入沉淀层的条件

一个页面或任务只有满足多数条件时才应该被沉淀：

1. 至少多次成功抓取
2. 页面入口相对稳定
3. 关键字段可稳定识别
4. 能定义出 verify 规则
5. 输出对用户长期有价值

### 沉淀层产物

- 注册页面 / 任务 spec
- 稳定导航步骤
- expected keys / verification rule
- report / summary strategy
- ask routing alias

### 判定标准

沉淀层的成功标准是：

- `capture` 有结果
- `verify=verified`
- 报告可读
- 页面语义清晰
- 可重复执行

---

## OpenClaw 与桥接器的协作协议

## 1. OpenClaw 发起意图判定

OpenClaw 先判定用户请求属于：

- `capture_registered`
- `capture_exploratory`
- `read_latest`
- `read_report`
- `status`
- `verify`
- `promote_candidate`

## 2. 桥接器只接稳定协议，不接开放式对话

桥接器 CLI / machine-readable bridge 应接收明确动作，比如：

- `capture`
- `verify`
- `report`
- `latest`
- `status`
- `explore`
- `promote`（可后续再做）

而不是让 runtime 自己理解无限自然语言。

## 3. OpenClaw 基于结果做解释与决策

例如：

- 这次只探索成功，先不给用户承诺稳定支持
- 这次已经 ready_to_promote，可以开始注册页面
- 这次疑似页面改版，需要调整导航步骤

---

## 建议的桥接器内部模块边界

## A. task/contracts

负责定义任务结构。

建议区分两类 task：

1. `RegisteredTaskSpec`
2. `ExplorationTaskSpec`

至少在字段语义上区分，而不是所有任务都假装是 page preset。

## B. navigation executor

继续保留通用导航执行器，但允许：

- 探索任务使用更宽松的 navigation steps
- 记录“导航命中证据”
- 记录点击失败 / fallback 情况

## C. parser / signal detector

在已有 parser 基础上新增候选信号检测能力：

- 输出本次 raw 中高频 key
- 输出可能属于目标页面的数据块
- 标记疑似广告/首页混入

## D. verify

verify 应拆为三类：

1. **runtime verify**
   - task/run/report/raw/db/step_events 是否齐全
2. **page verify**
   - 对已注册页面检查关键字段是否命中
3. **exploration verify**
   - 是否发现候选页面证据，是否达到可沉淀阈值

## E. report

report 也应拆层：

1. registered report
2. exploration report
3. promotion recommendation

---

## 为什么不能把“探索”直接塞进现有 registered page 模型

因为两者成功定义完全不同：

- registered page 追求稳定、可验真、可重复
- exploration 追求发现证据、快速迭代、允许不稳定

如果强行混成一个模型，会出现这些问题：

1. 为了探索而污染 verify 规则
2. 把一次性成功误当成长期支持
3. ask 路由过早承诺“已经支持某页面”
4. runtime 越来越像一堆 if/else 补丁

所以桥接器内部最好承认：

**探索任务不是半成品 preset，而是另一类正式的一等公民。**

---

## 对当前代码基线的改造建议

## 第一阶段：先把方案落地成协议

优先做这些：

1. 新增 `explore` 命令
2. 新增 `ExplorationTaskSpec`
3. 新增 exploration summary / verification
4. 在 skill 文档中把“三层能力”改成：
   - registered
   - composite
   - exploration
   并明确 exploration 是 assistant-directed

这一阶段先不追求 fully automatic promote。

## 第二阶段：补探索结果结构化

1. 自动总结 raw 高价值 keys
2. 自动给出候选 expected_keys
3. 自动输出 page spec 草案
4. 输出“是否建议沉淀”的 recommendation

## 第三阶段：再做 promote flow

让 OpenClaw 可以在确认后，把 exploration 结果转成 registered page 初稿。

注意：这一步可以半自动，不要一开始追求全自动写代码。

---

## skill 需要同步的变化

当前 skill 文档里已有一个正确方向：

- OpenClaw 负责理解与路由
- runtime 负责执行与验证
- exploration 已经被提到

但还不够明确的地方是：

1. exploration 目前像“内部研发附加项”，还不是一等协议
2. 没明确说明 registered 与 exploration 的成功定义不同
3. 没强调“是否沉淀”应由 OpenClaw 决策，而不是 runtime 自作主张

所以 skill 应补充：

- exploration mode 的正式输入输出
- assistant-directed capture 的边界
- promote/reuse 的判断原则
- 对用户承诺时的措辞边界

---

## 对外承诺边界

桥接器未来可以对外承诺的是：

1. 已注册页面：稳定抓取与验真
2. 探索模式：帮忙摸清新页面怎么抓
3. 对已变化页面：快速重新识别与修复

不应该对外承诺的是：

1. 任意页面立即稳定支持
2. 一次探索成功就等于正式支持
3. runtime 自己会理解无限自然语言和无限页面语义

---

## 推荐实施顺序

1. 在桥接器仓库补 architecture 文档（本文件）
2. 修改 skill 文档，统一心智
3. 在 CLI 增加 `explore` 原型命令
4. 定义 exploration result schema
5. 再决定是否以龙虎榜为第一个完整样板

---

## 当前结论

最合适的边界不是“桥接器支持越来越多 preset”，而是：

- **OpenClaw 负责判断怎么抓、何时探索、何时沉淀**
- **桥接器负责把探索和注册两类任务都执行成可验证证据**

这样才能同时满足：

- 面对新页面时不僵硬
- 面对重复页面时可复用
- 失败时知道问题出在理解层、策略层，还是 runtime 层
