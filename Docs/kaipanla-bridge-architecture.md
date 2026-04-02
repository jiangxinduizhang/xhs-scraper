# 开盘啦 bridge × AI × SKILL 协同总方案（合并修订版）

> 本文档是当前唯一主方案。
> 目标：在**严格边界**下，把“开盘啦任务探索 → 证据判断 → 继续执行 → ask human / 宣告成功 / 沉淀复用”的完整闭环说清楚。
>
> 三层对象必须严格区分：
>
> - **AI / OpenClaw**：理解、识别、判断、控制、对外解释
> - **SKILL**：AI 使用 bridge 时必须遵循的操作手册与停机规则
> - **bridge / runtime**：执行动作、采集证据、落盘、回读

---

## 0. 先给最终结论

当前问题的根不是“某次是否点到了龙虎榜”，而是：

**系统是否有能力形成任务闭环。**

所谓闭环，指的是：

1. AI 明确任务目标
2. AI 让 bridge 执行动作并收集证据
3. bridge 返回事实证据包
4. AI 判断证据是否足够
5. 若不足，AI 决定下一轮动作
6. 重复，直到：
   - 成功
   - ask human
   - 明确停止
7. 若成功路径可复现，再沉淀为 registered/可复用经验

当前已有：
- 初步边界定义
- 单次执行 + 落盘 + 回读
- exploration evidence bundle 雏形

当前缺少：
- 真正可持续的多轮控制闭环
- step-level 证据差分
- UI 证据
- AI 可控的继续/停止协议
- ask-human / success / reuse 的明确规则

---

## 1. 三层职责边界（必须写死）

## 1.1 AI / OpenClaw 负责什么

AI 负责所有“理解 / 识别 / 判断 / 决策 / 对外解释”。

### AI 负责：
- 理解用户要完成的真实任务
- 判断当前是 registered 还是 exploration
- 决定本轮目标是什么
- 读 evidence bundle，并判断：
  - 当前是否更接近目标
  - 当前证据是否足够
  - 当前是否需要继续探索
  - 当前是否需要 ask human
  - 当前是否可以告诉 human “探索成功”
- 决定下一轮动作
- 决定是否把一次探索经验沉淀为 registered / reusable recipe
- 对外解释结果、风险和不确定性

### AI 明确不负责：
- 直接替代 bridge 做设备动作执行
- 把“没有证据的猜测”包装成成功结论
- 用自然语言要求 bridge 自己理解开放式意图并自主探索

---

## 1.2 SKILL 负责什么

SKILL 不是 bridge，也不是 AI 本体。

SKILL 是：

> **AI 在使用 bridge 时必须遵循的操作逻辑手册。**

### SKILL 负责：
- 规定 AI 如何选择 `capture / explore / verify / report / latest / status`
- 规定 AI 在 exploration 中如何 loop
- 规定什么情况下应继续、停止、ask human
- 规定什么情况下允许对 human 宣告“探索成功”
- 规定什么情况下可以把探索经验沉淀为 registered/reusable recipe
- 规定哪些结论绝不能由 bridge 输出
- 规定哪些字段只能被理解为“事实”，不能被理解为“成功”

### SKILL 明确不负责：
- 直接替代 runtime 提供执行能力
- 替 bridge 凭空发明不存在的接口
- 替 AI 做实际判断

一句话：

**SKILL 负责“AI 应该怎么用”，不负责“系统底层能力从哪里来”。**

---

## 1.3 bridge / runtime 负责什么

bridge 是执行器与证据采集器，不是判断器。

### bridge 负责：
- 启 app / 连设备 / 配代理 / 清理环境
- 点击 / 滑动 / 返回 / 等待 / 截图 / dump UI / 抓包
- 记录每步动作的时间点和执行结果
- 记录动作前后请求与 UI 事实
- 生成 run/task/report/raw/db/evidence bundle
- 回读 latest/status/report/verify
- 在 exploration 或 registered 模式下，按照明确参数执行

### bridge 明确不负责：
- 判断“是否进入目标主块”
- 判断“这是不是龙虎榜核心数据”
- 判断“是否值得继续探索”
- 判断“是否 ask human”
- 判断“是否可以告诉用户成功”
- 判断“是否值得 promote/reuse”
- 开放式自然语言理解

一句话：

**bridge 只做手和相机，不做脑子。**

---

## 2. 严格区分两类输出：事实 vs 结论

## 2.1 bridge 只能输出事实型字段

允许：
- `action_facts`
- `ui_facts`
- `request_facts`
- `structure_facts`
- `artifact_facts`
- `raw_record_count`
- `observed_paths`
- `observed_keys`
- `round_index`
- `max_rounds`
- `tap_found`
- `tap_executed`
- `ui_changed`
- `new_requests`
- `candidate_structures`
- `noise_structures`
- `evidence_status`

这些都是事实、计数、结构、时序。

## 2.2 bridge 不应输出结论型字段

禁止把这些当 bridge 当前能力口径：
- `page_verified`
- `main_block_found`
- `dragon_tiger_reached`
- `stable_capture`
- `ready_to_promote`
- `exploration_success`
- `page_grabbed`
- `目标页已确认`
- `核心数据已抓到`

如果历史兼容必须保留类似字段，也只能：
- 标记 deprecated
- 明确说明“只是旧兼容字段，不可当业务结论”

---

## 3. 两种工作模式

## 3.1 registered

适用于：
- 已验证稳定的页面
- 已有可复现导航路径
- 已有可复现证据链
- 已沉淀为固定任务模板

### registered 的特点
- 可以有固定 preset / task spec
- 可以有固定 verify/report
- 可以复用既定导航动作
- 可以对产物完整性做较强校验

### 但 registered 仍然不能意味着：
- bridge 可以自己做业务结论
- bridge 可以自己判断“页面语义已确认”

---

## 3.2 exploration

适用于：
- 新页面
- 页面改版
- 入口位置不稳
- 目标还未摸清
- 需要 AI 多轮指挥

### exploration 的本质

不是“弱版 registered”，而是：

> **AI 驱动的多轮证据探索协议**

流程是：
- AI 发明确任务
- bridge 执行并收集事实证据
- AI 读证据
- AI 判断是否继续
- 继续则进入下一轮
- 直到 ask human / success / stop

---

## 4. 最小闭环协议（必须落地）

## 4.1 一轮 exploration 的最小输入

一轮 exploration 输入必须是明确、执行导向的，不是开放式意图。

至少应包含：
- `target_hint`
- `round_index`
- `max_rounds`
- `navigation_hint`（可选）
- `capture_options`
- 本轮动作列表 / 本轮最小动作目标

例如：
- 进入行情 tab
- 点击“龙虎榜”
- 点击后等待 2 秒
- 采集点击前后 screenshot / UI dump / request delta

### 谁负责定义？
- **AI 负责决定要做什么**
- **bridge 负责执行这个明确动作集**
- **SKILL 负责约束 AI 不要一次塞太多混合目标**

---

## 4.2 一轮 exploration 的最小输出

一轮结束后，bridge 至少要输出以下 5 组事实。

### A. action_facts（bridge 负责生成）
- 本轮动作列表
- 每步动作类型
- 每步动作时间点
- 点击目标
- 点击是否找到
- 点击是否执行
- 等待/滑动/返回是否执行
- 是否出现异常/回退

### B. ui_facts（bridge 负责生成）
- screenshot_before
- screenshot_after
- ui_dump_before
- ui_dump_after
- visible_text_before
- visible_text_after
- visible_text_diff
- ui_changed

### C. request_facts（bridge 负责生成）
- pre_window_count
- post_window_count
- pre_window_paths
- post_window_paths
- new_requests
- new_paths
- new_keys
- path_counts
- 请求记录与动作时间点的对应关系

### D. structure_facts（bridge 负责生成）
- observed_keys
- candidate_structures
- noise_structures
- key/shape/repetition
- first_seen_after_action_ms
- 该结构来自哪些请求

### E. artifact/meta facts（bridge 负责生成）
- raw_paths
- report_path
- db_path
- round_index
- max_rounds
- evidence_status
- task_id / run_id

### 谁解释这些？
- **只有 AI 负责解释这些事实意味着什么**

---

## 4.3 AI 每轮之后必须做的 4 类判断

### 1. 当前是否更接近目标
AI 判断：
- UI 是否变化
- 新请求是否集中在点击后
- 是否出现新的结构块
- 候选结构是否比前一轮更聚焦
- 是否仍然主要是首页公共块/缓存块

### 2. 当前最可能解释是什么
例如：
- 仍停留在公共行情数据
- 可能切到目标页但主块未触发
- 可能点错元素
- UI 变化存在但请求无新证据
- 请求变化明显但 UI 无法确认

### 3. 下一轮最小动作是什么
例如：
- 再点一次目标 tab
- 改点击不同位置/不同文案
- 先不滑动
- 增加停留时间
- 增加 UI dump
- 只聚焦动作后 3 秒窗口

### 4. 是否应该停止
停止原因只允许由 AI 给出：
- 证据已足够
- 到达最大轮数
- 证据不再改善
- 目标不清晰
- 再继续只能靠猜
- 需要 human 提供关键澄清

---

## 5. Loop 规则（SKILL 必须写清）

## 5.1 exploration loop 的默认原则

AI 使用 skill 时，默认应采用：

1. 明确当前轮目标
2. 只要求 bridge 做最小必要动作
3. 回读 evidence bundle
4. 判断证据是否改善
5. 若改善且仍不足，则继续下一轮
6. 若不改善或已到边界，则 ask human / stop

### loop 原则
- 一轮只解决一个核心不确定性
- 不要一轮里混入太多动作
- 每轮都要有“为什么继续”的理由
- 没有清晰增信理由时，不要机械重跑

---

## 5.2 什么时候继续 loop

由 AI 判断继续，仅当满足以下至少一类：
- 新一轮有明确更小的验证问题
- 上一轮证据比前一轮更接近目标
- 可以通过一个额外动作显著增信
- 当前冲突证据可以通过下一轮被澄清
- 仍未到 max_rounds，且继续不是纯碰运气

---

## 5.3 什么时候停止 loop

AI 应停止，而不是为了“多跑几轮”而继续。

停止条件包括：
- evidence 已足够支持对外结论
- 连续两轮没有增信
- 下一轮动作没有明确目的
- 目标定义本身不清晰
- 当前环境限制导致再跑无意义
- 已到 max_rounds

---

## 6. Ask-human gate（只能由 AI 触发）

ask human 是边界保护机制，不是失败借口。

## 6.1 必须 ask human 的情况

### A. 目标不清
例如：
- 用户要的是“页面主块”，还是“任意相关数据”
- 用户要的是“能进去看见页面”，还是“能稳定复用抓数据”

### B. 证据冲突
例如：
- UI 看起来切页了，但请求仍是公共块
- 请求变了，但 UI 看不到明显变化
- 两轮动作都拿到不同候选块，无法判断哪一个才是目标

### C. 再继续只能靠猜
例如：
- 没有新的动作可做
- 没有新的证据项可增加
- 下一步只能靠 bridge 自己“理解页面语义”

### D. 需要人工提供业务偏好
例如：
- 是否接受“相关数据即可”
- 是否一定要锁定主列表主块
- 是否允许先沉淀半稳定路径

## 6.2 ask human 由谁发起
- **AI 发起**
- **SKILL 规定问法与触发规则**
- **bridge 不发起业务 ask human**

---

## 7. 什么时候可以告诉 human“探索成功”

这个判断只能由 AI 做，而且必须保守。

## 7.1 可以宣告“探索成功”的最小条件

至少满足：

### 条件 1：导航证据成立
- 有明确动作证据表明已执行目标路径
- 若有 UI 证据，UI 与目标区域一致

### 条件 2：请求/结构证据成立
- 点击/动作后出现新的、与目标高度相关的请求或结构
- 新证据不是首页公共块/广告块/缓存块的重复

### 条件 3：证据链可解释
- AI 能清楚说明：
  - 做了什么
  - 出现了什么新证据
  - 为什么这些证据足以支持“目标已抓到/已进入”

### 条件 4：不依赖“桥接器弱信号复述”
不能仅凭：
- preset 名叫 dragon_tiger
- step 里记录了 tap_dragon_tiger_tab
- report 写了采集龙虎榜页相关产物

就宣告成功。

## 7.2 允许的成功口径
AI 可以说：
- “已完成导航并收集到与目标高度一致的新请求证据”
- “当前可以高置信度认为已抓到目标页面相关核心数据”
- “这条探索路径已形成可复核闭环”

但如果证据只到一半，只能说：
- “动作已执行，但语义成功尚未确认”
- “拿到候选证据，但还不足以宣告成功”

---

## 8. 经验沉淀 / 复用机制（非常重要）

“复用经验”不是 bridge 自己决定的，而是 AI 在完成探索后做的沉淀。

## 8.1 什么可以沉淀

可以沉淀的不是“业务结论”，而是：
- 导航 recipe
- 点击顺序
- 等待时长
- 哪些步骤必须做
- 哪些步骤不要做
- 哪种动作后最容易触发目标请求
- 哪些路径是稳定噪声
- 哪些证据最有用

例如：
- 进入行情后先点底部龙虎榜 tab，不要先滑动
- 点击后等待 2.5 秒再抓 post-window 请求
- 首页公共 `Index/MsgTop/DaBanList` 应当视为默认噪声基线

## 8.2 沉淀成什么形式

分两层：

### A. reusable recipe（AI/SKILL 层）
适用于：
- 还没达到 fully registered
- 但已有可复用探索经验

内容包括：
- 推荐导航顺序
- 推荐 capture_options
- 典型噪声模式
- 典型 ask-human 触发点

### B. registered preset/page（bridge/runtime 层）
适用于：
- 多轮验证稳定
- 路径可复现
- 证据结构稳定
- AI 认为值得固化

此时才允许沉淀为：
- 固定 page spec
- 固定 verify/report
- 固定 recipe

## 8.3 谁决定沉淀
- **AI 决定“是否值得沉淀”**
- **SKILL 规定沉淀 checklist**
- **bridge 只负责承载被沉淀后的执行模板**

bridge 不得自己决定 promote。

---

## 9. 改造方案：按对象拆分，不混责任

## 9.1 bridge / runtime 必须改造的内容

这些是 bridge 真正该补的能力，不是 skill 文案可以替代的。

### P0：必须有

#### 1. session 化执行模型
当前一次 run 完即退出，不足以支撑闭环。
需要支持：
- start_session
- execute_round / execute_actions
- collect_evidence
- continue_session
- finish_session

#### 2. step-level action schema
至少支持：
- tap_text
- tap_coord
- tap_text_or_fallback
- wait
- back
- swipe
- screenshot
- dump_ui
- visible_text
- capture_request_window

#### 3. 动作前后差分证据
必须能输出：
- before/after screenshot
- before/after UI dump
- before/after visible text
- pre/post request window
- new paths / new keys / new records
- first_seen_after_action_ms

#### 4. exploration evidence bundle v2
当前 evidence 太弱，必须提升为可驱动 AI loop 的 bundle。

#### 5. verify/report 改口径
exploration 只能输出：
- evidence_complete
- evidence_partial
- evidence_insufficient

禁止输出页面语义成功。

### P1：应该有
- step 执行失败原因结构化
- 动作与请求记录的精确时间窗绑定
- 基线噪声视图（公共块/广告块）
- 对同一轮多动作的增量证据聚合

### P2：后续可补
- 会话恢复
- 更丰富的 UI 采集能力
- 更标准化的 recipe/promote 挂载接口

---

## 9.2 AI / OpenClaw 必须承担的内容

这些不能再偷塞给 bridge。

### AI 必须做：
- 定义本轮探索目标
- 判断 evidence 是否足够
- 判断是否继续 loop
- 判断是否 ask human
- 判断是否成功
- 判断是否沉淀为 reusable recipe / registered
- 对外解释“为什么成功/为什么没成功”

### AI 不得做：
- 把 bridge 的 preset 名称当成成功证据
- 把 `page_flow_complete` 当成语义成功
- 把 observed_keys 命中当成主块确认
- 没有增信理由时机械重跑

---

## 9.3 SKILL 必须补充的内容

SKILL 应明确写出 AI 使用规则。

### SKILL 必须补：

#### 1. 命令选择规则
- 什么时候用 registered capture
- 什么时候用 explore
- 什么时候用 latest/status/verify/report

#### 2. loop 规则
- 每轮只解决一个不确定性
- 何时继续
- 何时停
- 何时 ask human

#### 3. success 规则
- 什么证据下才能告诉 human 成功
- 什么情况下只能说“动作做了但未确认成功”

#### 4. 沉淀规则
- 什么时候只记为 reusable recipe
- 什么时候可 promote 为 registered
- recipe 与 registered 的区别

#### 5. 严禁口径
- 不得把 bridge 输出当最终业务结论
- 不得让 runtime 自己理解开放式任务并制定策略

---

## 10. 推荐的闭环流程

## 10.1 exploration 闭环

1. 用户提出目标
2. AI 判断为 exploration
3. AI 生成 round-1 明确任务
4. bridge 执行 round-1，输出 evidence bundle
5. AI 判读：
   - 更接近 / 不更接近 / 冲突 / 不足
6. AI 决定：
   - round-2
   - ask human
   - stop
   - declare success
7. 若多轮稳定，AI 决定是否沉淀 recipe 或 registered

## 10.2 registered 闭环

1. 用户提出已知稳定任务
2. AI 直接使用 registered capture
3. bridge 执行
4. bridge 回产物与事实
5. AI 对外解释结果
6. 若 registered 失效，则回退到 exploration

---

## 11. “龙虎榜”这个案例下的具体口径

## 11.1 不能再说的话
不能说：
- “我已经抓到了龙虎榜页面数据”
- “因为我点击了龙虎榜所以就是龙虎榜数据”
- “报告里写 dragon_tiger 所以任务成功”

## 11.2 允许说的话
可以说：
- “我已经执行了进入行情并点击底部龙虎榜菜单的动作”
- “当前产物完整，但最新 raw 仍更像公共行情/情绪数据，尚不足以证明已抓到龙虎榜核心数据”
- “下一步需要针对点击后的 UI / 请求差分继续取证”

这就是严格边界下的正确口径。

---

## 12. 改造阶段建议

## Phase 1：补齐闭环最小执行能力
目标：让 bridge 成为可持续的受控执行器，而不是一次性 runner。

必须完成：
- session 化
- round 化
- step-level action schema
- before/after 差分证据
- exploration evidence bundle v2
- exploration verify/report 新口径

## Phase 2：补齐 SKILL 控制逻辑
目标：让 AI 真能按 skill 规则做 loop。

必须完成：
- loop 规则
- ask-human gate
- success gate
- reusable recipe gate
- fallback to exploration / fallback to registered 规则

## Phase 3：沉淀 registered / reuse 机制
目标：只把真正稳定的路径固化。

必须完成：
- recipe schema
- promote checklist
- registered preset 生成/维护流程
- 失效回退机制

---

## 13. 明确的“不要做”

为了避免再次混责任，写死如下：

- 不要让 bridge 直接判断页面语义
- 不要让 bridge 输出 main block / success / promote 结论
- 不要用更多页面专属规则掩盖闭环不足
- 不要把“跑完一次 preset”当作“完成探索”
- 不要让 SKILL 文档暗示 runtime 已经拥有不存在的能力
- 不要让 AI 把弱信号包装成强结论

---

## 14. 当前唯一正确的协同心智

### bridge
执行动作 + 采集证据 + 落盘 + 回读

### AI
读证据 + 做判断 + 控 loop + 做 ask-human / success / reuse 决策

### SKILL
规定 AI 在这个系统里应该如何安全、严格、可复核地工作

一句话收束：

**闭环的关键不是让 bridge 更像 AI，而是让 bridge 足够可控、证据足够完整、AI 足够克制且明确地承担自己的判断责任。**
