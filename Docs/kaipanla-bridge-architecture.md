# 开盘啦桥接器 × AI 协同实现方案（重整版）

## 0. 目标

我们要实现的不是“桥接器更聪明”，而是：

- **桥接器负责复杂执行与证据采集组织**
- **AI 负责识别、判断、控制下一步动作**
- **两者形成明确的探索闭环，而不是互相偷懒**

这意味着：
- 不能把 bridge 做成半个 AI
- 也不能让 AI 把 bridge 的弱信号直接转述成成功
- 不要被既有代码中的结论型字段、状态名、历史结构带偏

---

## 1. 总体架构原则

### 1.1 Bridge 的职责

bridge 只负责三类事：

#### A. 执行动作
例如：
- 打开 app
- 导航到某 tab / 某入口
- 点击目标文案/区域
- 截图
- 导出 UI 树
- 抓包
- 记录动作前后时间点
- 再试一次 / 换一个入口 / 等待 / 滑动

#### B. 采集并组织证据
bridge 输出的是**事实证据包**，不是识别结论。
例如：
- 点击前后 UI 是否变化
- 点击前后出现了哪些新请求
- 哪些请求只出现在点击后时间窗
- 哪些结构是候选块
- 哪些结构更像噪声/公共块
- 证据之间的时序关系

#### C. 提供受控执行接口
bridge 应该像一个“受控探测器”：
- 你让它做什么，它就做什么
- 它可以返回复杂证据
- 但它不替 AI 下业务结论

### 1.2 AI 的职责

AI 负责：

#### A. 识别
根据 bridge 的证据判断：
- 这轮是否真的更接近目标页
- 当前抓到的是公共块、候选块，还是更像目标主块
- 当前证据强弱如何

#### B. 控制
决定下一步动作：
- 继续点哪里
- 是否要截图/UI dump
- 是否只取点击后时间窗
- 是否需要换一种操作路径
- 是否该 ask human

#### C. 对外结论
只有 AI 可以输出这类结论：
- 这轮抓偏了
- 当前只有候选证据
- 可以继续探索
- 需要人工澄清
- 值得 promote / 不值得 promote

---

## 2. 设计原则：事实输出 vs 结论输出

### 2.1 bridge 只能输出“事实型字段”

例如允许：
- `tap_attempted`
- `tap_target`
- `tap_found`
- `tap_timestamp`
- `screenshot_before`
- `screenshot_after`
- `ui_dump_before`
- `ui_dump_after`
- `ui_changed`
- `requests_before`
- `requests_after`
- `new_request_count`
- `candidate_structures`
- `noise_structures`
- `time_window_records`

这些都是**客观记录**。

### 2.2 bridge 不应输出“结论型字段”

尤其 exploration 场景里，不应让 bridge 直接输出：
- `dragon_tiger_reached`
- `page_flow_complete`
- `page_verified`
- `stable_capture`
- `main_block_found`
- `ready_to_promote`

这些都已经带有判断和归因意味。

如果必须保留类似信息，也只能改成**弱表述的事实标签**，而不是结论。

---

## 3. 能力分层

### 3.1 Registered Capture

适用于已经证明稳定的页面。

registered 层才允许存在更强的流程封装，但前提是：
- 这个页面已经经过足够 exploration
- AI 已确认它值得沉淀
- 导航和证据链可复现

这一层可以有：
- 稳定任务模板
- 稳定证据抽取
- 稳定 verify
- 稳定 report

但就算是 registered，bridge 也仍应尽量输出事实证据，不应无限膨胀成业务判断器。

### 3.2 Exploration-first Capture

适用于：
- 新页面
- 改版页面
- 入口不稳定
- 目标不完全明确
- 需要 AI 边看边指挥

exploration 的本质不是“弱版 registered”，而是：

> **AI 驱动的多轮证据探索协议**

核心是：
- bridge 跑动作
- bridge 回证据
- AI 判读
- AI 决定下一轮
- 到停点或 ask-human gate 为止

---

## 4. Exploration 的最小闭环协议

### 4.1 单轮 exploration 应输出什么

一轮 exploration 结束后，bridge 至少应回：

#### A. 动作事实
- 本轮做了哪些动作
- 每步动作时间点
- 是否成功找到点击目标
- 是否执行了点击/滑动/等待

#### B. UI 事实
- 点击前截图
- 点击后截图
- 点击前 UI dump
- 点击后 UI dump
- 可见文本变化摘要
- 是否发生明显 UI 变化

#### C. 请求事实
- 点击前时间窗请求数
- 点击后时间窗请求数
- 新出现请求列表
- 新请求的 path / keys / shape 摘要
- 哪些请求是重复稳定出现的

#### D. 候选结构事实
- 可能相关的结构块有哪些
- 每个结构块的 key / shape / repetition
- 每个结构块是在点击前还是点击后出现
- 哪些更像公共块 / 广告 / 噪声

#### E. 执行元信息
- 本轮 target hint
- 本轮输入指令
- 本轮轮次
- 是否已达最大轮数

注意：
这些都还是**事实包**，不是“龙虎榜主块已找到”。

### 4.2 AI 在每轮之后做什么

AI 读完事实包后，只做四类判断：

#### 1. 本轮是否比上轮更接近目标
例如：
- UI 明显变化了
- 点击后新增请求更多
- 新请求更聚焦
- 候选结构更集中

#### 2. 当前最可能的解释是什么
例如：
- 仍停留在首页公共块
- 可能进入了目标区域但没抓到主块
- 已出现更像目标主块的候选结构
- 当前证据冲突，无法判断

#### 3. 下一轮最小动作是什么
例如：
- 再点一次龙虎榜入口
- 改为点击不同位置
- 点击后立即截图并抓 3 秒
- 先不滑动
- 只保留点击后请求

#### 4. 是否要停止
停止条件：
- 证据不再改善
- 已到轮数上限
- 目标不清晰
- 需要用户回答关键问题
- 再继续会逼着 bridge 替 AI 做判断

---

## 5. Ask-human gate

### 5.1 ask-human 的作用

ask-human 不是失败兜底，而是**边界保护机制**：

当 AI 发现再跑下去只能靠猜时，就必须问人。

### 5.2 应触发 ask-human 的情况

例如：
- 连续两轮都主要是首页公共块
- UI 证据和请求证据互相冲突
- 目标是“页面主块”还是“任意相关数据”不清楚
- 再继续探索也不会明显增信
- 下一步只能通过硬编码业务语义来推进

### 5.3 ask-human 的输出

AI 对外应该明确问：
- 你要锁定的是页面主列表/主块，还是页面内任意相关数据？
- 你要的是页面结构摸清，还是已经能稳定复用的 registered 抓取？
- 你更在意导航到位，还是抓到相关请求即可？

ask-human 应由 AI 发起，不是 bridge 自己决定业务问题。

---

## 6. Verify 的重新定义

### 6.1 registered 的 verify

registered verify 只验证：
- 执行动作是否完成
- 产物是否存在
- 证据链是否完整
- 已定义事实条件是否满足

registered verify 不等于“AI 语义理解正确”，但它可以验证 registered 所需的既定事实门槛。

### 6.2 exploration 不应用 registered verify 那套成功语义

exploration 阶段不应该把 verify 做成：
- verified
- success
- reached

更合适的是：
- `evidence_complete`
- `evidence_partial`
- `evidence_insufficient`

也就是只评价**证据包是否可供 AI 判读**，不评价“目标页是否真的成立”。

---

## 7. Report 的重新定义

### 7.1 registered report

registered report 可以是结果导向的：
- 抓到了什么
- 主要字段
- 结果摘要
- 稳定产物路径

但前提是它真的已经是 registered 页面。

### 7.2 exploration report

exploration report 不应该写成“页面抓取完成”。

exploration report 只能写：
- 做了什么动作
- 产生了什么新证据
- 目前最值得 AI 关注的候选结构是什么
- 当前还存在什么不确定性
- 下一轮建议做什么
- 是否需要 ask human

也就是：
**exploration report 是“探测报告”，不是“结果报告”。**

---

## 8. “龙虎榜”案例的落地目标

这里按方案预期写，不顺着现有代码。

### 8.1 第一阶段目标

不是“让桥接器识别龙虎榜主块”，而是：

> **让 bridge 能围绕“点击龙虎榜入口”收集完整的动作 / UI / 请求证据包**

### 8.2 bridge 的最小能力

bridge 应支持：
- 进入行情 tab
- 尝试点击“龙虎榜”入口
- 记录点击前后截图
- 记录点击前后 UI dump
- 记录点击前后请求时间窗
- 输出新增请求及候选结构摘要

这就够了。

### 8.3 AI 的判断目标

AI 判断的不是“bridge 说 reached 没”；
AI 判断的是：
- 点击后 UI 有没有变化
- 新请求是不是比点击前更集中
- 候选结构是不是更像目标页相关
- 当前仍是不是首页公共块主导
- 是否值得继续试下一轮

### 8.4 promote 条件

不是 bridge 决定，也不是单轮 exploration 决定。

promote 至少要满足：
- 多轮 exploration 证据稳定
- AI 多次复核认为进入路径和证据结构可复现
- 候选主结构在不同 run 中稳定出现
- 不再主要依赖人工解释“它大概像”

---

## 9. 最小实现路线图

### Phase 1：bridge 去结论化
目标：
- 把 exploration 输出从“判断型”改成“事实型”

做的事：
- 重构 step / event 语义
- exploration 输出增加动作 / UI / 请求证据
- 删除 / 降级结论型字段

产出：
- exploration evidence bundle v2

### Phase 2：AI 驱动多轮探索
目标：
- 让 AI 真正基于 evidence bundle 决定下一轮

做的事：
- 定义单轮输入 / 输出协议
- 定义轮次控制
- 定义“证据是否改善”的 AI 判读逻辑
- 定义 ask-human gate

产出：
- exploration control loop

### Phase 3：registered promote 机制
目标：
- 只有在 exploration 足够稳定后，才沉淀为 registered page

做的事：
- 定义 promote checklist
- 定义 registered task spec
- 定义 registered verify / report

产出：
- 明确的 promote flow

---

## 10. 当前不该做的事

为了防止再次跑偏，以下条目写死：

- 不要让 bridge 直接判断“是否进入目标主块”
- 不要让 bridge 直接输出带业务语义的成功结论
- 不要靠增加更多页面特化规则来掩盖边界问题
- 不要把 generic key 命中直接解释成页面成功
- 不要把 exploration 写成“半个 registered”
- 不要让 AI 只复述 bridge 的弱信号
- 不要被现有类名、状态名、历史代码结构牵着走

---

## 11. 第一轮实际实施范围

如果按这版方案推进，第一轮实现只做两件事：

### 11.1 定义新的 exploration evidence bundle
只关注：
- 动作事实
- UI 事实
- 请求事实
- 候选结构事实

### 11.2 定义 AI 消费 evidence bundle 的控制协议
只关注：
- 继续
- 收紧
- 停止
- ask human

先不急着碰：
- promote
- registered 精细 verify
- 业务摘要
- 页面专属语义规则

这样最不容易再次滑回“bridge 变聪明”的老路。

---

## 12. 文档清理原则

旧方案文档里凡是容易诱导 bridge 承担以下责任的内容，应精简或移除：
- bridge 做页面语义识别
- bridge 输出 ready / reached / promote 一类强结论
- bridge 用页面专属规则替代 AI 判读
- exploration 成功约等于页面支持成立

保留原则：
- 只保留职责边界清晰、与新协同模型一致的内容
- 所有 implementation note 都要服从“bridge 做证据，AI 做识别”

---

## 13. 当前结论

最合适的边界不是“桥接器支持越来越多 preset”，而是：

- **AI 负责判断怎么抓、何时继续、何时停止、何时 ask human、何时 promote**
- **bridge 负责把探索和注册两类任务都执行成可消费、可复核、可验证的事实证据**

这样才能同时满足：
- 面对新页面时不僵硬
- 面对重复页面时可复用
- 失败时知道问题出在执行层、证据层，还是识别层
