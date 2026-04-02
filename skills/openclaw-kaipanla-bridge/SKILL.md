---
name: openclaw-kaipanla-bridge
description: "开盘啦执行桥：用于执行、校验、回读和取证式 exploration 的开盘啦 APP 任务。适用于抓市场情绪、排行、连板、资金、题材、个股、板块、龙虎榜，查询最近运行状态，读取已有结果，或按明确任务收集页面证据包。"
---

# 开盘啦执行桥

这个 skill 现在应按**严格边界**理解：

- **OpenClaw / AI**：理解用户意图、决定策略、决定下一步、决定是否 ask human、决定是否 promote、决定如何对外解释
- **Kaipanla bridge / runtime**：像一只“手”一样执行动作、抓包、落盘、回读、校验产物完整性、输出事实证据

一句话：

**bridge 不是裁判，不是分析师，不是路由器；它只是执行工具和证据搬运工。**

---

## 1. 硬边界

### AI / OpenClaw 负责

- 理解自然语言请求
- 判断当前应走：
  - registered capture
  - exploration capture
  - latest
  - report
  - status
  - verify
- 决定页面/目标/轮次策略
- 决定下一步动作
- 决定是否 ask human
- 决定是否把某个页面 promote 为 registered
- 读取证据后做语义判断与对外解释

### bridge / runtime 负责

- 接受明确任务参数
- 执行页面动作
- 启动代理、抓包、解析、落盘
- 生成 task / run / report / raw / db 等产物
- 输出事实型 evidence bundle
- 检查产物是否存在、证据是否成形
- 回读最近一次运行

### bridge 明确不负责

- 开放式自然语言理解
- 替用户猜真实目标
- 页面语义识别
- 判断“是不是目标主块”
- 判断“是不是已经稳定抓到”
- 推荐下一步策略
- ask-human 业务判断
- promote 决策
- 投资判断 / 交易建议 / 复盘观点

如果某个功能更像“理解 / 识别 / 判断 / 决策”，默认就不应属于 bridge。

---

## 2. 当前能力模型

### A. registered

用于**已定义好的执行任务**。

特点：
- 有固定 task/page spec
- 有稳定导航动作
- 有固定落盘产物
- 可以执行 / 回读 / 校验

注意：
- registered 不等于 bridge 有权做复杂语义判断
- registered verify 更接近“产物闭环是否成立”
- 不应把 registered 的 status 误读成 AI 级结论

### B. exploration

exploration 现在应理解成：

**按明确任务收集 evidence bundle 的执行模式**

而不是：
- 半个 registered
- 候选判定器
- 运行时智能探索器

exploration 的目标不是让 runtime 说“更像哪个页面”，而是产出：
- 动作事实
- UI 事实
- 请求事实
- 结构事实
- 产物事实

供 AI 自己判断下一步。

---

## 3. 当前 exploration 输出心智

exploration 只应该输出事实证据，不应该输出结论。

当前重点应关注这些字段：

- `evidence_status`
- `observed_keys`
- `navigation_events`
- `raw_record_count`
- `observed_paths`
- `evidence.action_facts`
- `evidence.ui_facts`
- `evidence.request_facts`
- `evidence.structure_facts`
- `evidence.artifact_facts`

### `evidence_status` 的含义

这里只表示**证据包是否成形**，不表示语义判断是否成立。

- `evidence_complete`：raw + step events 等核心证据存在
- `evidence_partial`：只形成部分证据
- `evidence_insufficient`：证据不足

它**不是**：
- 已进入目标页
- 已识别目标主块
- 已稳定抓到目标数据

---

## 4. 不应再使用的旧心智

以下概念不要再作为 bridge 的当前能力描述：

- `candidate_keys`
- `likely_noise_keys`
- `recommended_page_name`
- `recommendation`
- `self_proof_blockers`
- `ask_human`
- `safe_to_claim_stable_capture`
- `strong_candidate_evidence`
- `ready_to_promote`
- `verify=verified`
- `find_candidate_keys`
- `produce_exploration_summary`
- `exploration_summary`

同样，不要再把这些口径当成当前 bridge 的真实接口：

- `*_reached` 就等于页面已被真实确认进入
- `expected_keys` 命中就等于页面主块已确认
- “页面已抓取完成 / 命中关键字段” 就等于目标已被语义确认

这些都容易把 bridge 重新写回“判断器”。

---

## 5. 推荐使用方式

### 当用户要“执行”

让 AI 先决定：
- 是 registered 任务还是 exploration 任务
- 目标页/目标区域是什么
- 是否需要继续多轮

bridge 只执行。

### 当用户要“看状态 / 校验 / 回读”

bridge 可以做：
- `latest`
- `status`
- `verify`
- `report`

但这些返回值也应优先被理解为：
- 产物状态
- 证据状态
- 执行事实

而不是最终业务结论。

---

## 6. 当前动作层

优先把 bridge 当成明确命令工具来用：

- `capture`
- `explore`
- `verify`
- `report`
- `latest`
- `status`

### `capture`
执行既定任务，输出 run/task/report/raw/db。

### `explore`
执行 evidence-bundle 收集任务。
返回事实证据，不负责解释“像不像目标页”。

### `verify`
检查：
- 产物是否存在
- raw 是否存在
- report 是否存在
- task 是否存在
- evidence 是否完整

### `report`
回读结果。
exploration report 应理解为**证据报告**，不是结论报告。

### `latest`
返回最近一次运行产物。

### `status`
返回最近一次运行及校验信息。

---

## 7. 输入输出契约心智

### task
任务应尽量是明确的、执行导向的。

当前 exploration task 应优先体现：
- `collect_evidence_bundle`
- `persist_exploration_artifacts`
- `runtime_role: execution_only`

### run
run 是执行记录，不是业务结论。

### report
report 是产物消费层，不是任务成功定义本身。

---

## 8. 对外承诺边界

可以承诺：

- bridge 可以执行开盘啦任务并落盘
- bridge 可以输出 evidence bundle
- bridge 可以回读和校验已有运行产物
- bridge 可以作为 AI 的执行工具

不应承诺：

- bridge 自己能理解任意开盘啦页面语义
- bridge 自己能判断是否真正进入目标页主块
- bridge 自己能判断是否已经稳定抓到目标数据
- bridge 自己能决定下一轮怎么探索
- bridge 自己能 ask human
- bridge 自己能 promote 页面

---

## 9. 典型协作方式

正确协作顺序应该是：

1. AI 理解用户要什么
2. AI 生成明确任务
3. bridge 执行动作并产出证据
4. AI 读取 evidence bundle
5. AI 判断当前更接近什么、下一步做什么、是否 ask human、是否停止

而不是：

1. 用户说一句模糊话
2. bridge 自己理解意图
3. bridge 自己判断像哪个页面
4. bridge 自己决定继续还是停
5. AI 只复述 bridge 的弱判断

后者是明确要避免的。

---

## 10. 调用方式

优先使用 bundled launcher：

```bash
bash scripts/kpl_bridge.sh capture --task <task.json>
bash scripts/kpl_bridge.sh explore <target-text> --preset <page>
bash scripts/kpl_bridge.sh verify --run <run.json>
bash scripts/kpl_bridge.sh report --run <run.json>
bash scripts/kpl_bridge.sh latest
bash scripts/kpl_bridge.sh status
```

也可直接调用工具：

```bash
python3 scripts/kpl_tool.py capture --task <task.json>
python3 scripts/kpl_tool.py explore <target-text> --preset <page>
python3 scripts/kpl_tool.py verify --run <run.json>
python3 scripts/kpl_tool.py report --run <run.json>
python3 scripts/kpl_tool.py latest
python3 scripts/kpl_tool.py status
```

注意：
- exploration 现在应尽量显式给 `--preset`
- 不要把 `explore` 当成 runtime 自己“理解你到底想抓什么”的入口
- bridge 当前不再提供 `ask` 子命令作为自然语言路由入口

---

## 11. 不要做

- 不要把 bridge 写成 AI
- 不要把 evidence bundle 写成 candidate judgment
- 不要把 `*_reached` 当成真实页面确认
- 不要把 `expected_keys` 命中当成主块确认
- 不要把 report 当成成功证明
- 不要让 bridge 决定 ask-human / promote / strategy
- 不要在 skill 文档里继续保留已经废弃的 exploration 旧字段和旧状态名

如果要判断“这是不是目标页 / 是否稳定 / 下一轮怎么走”，那一步应该回到 AI。
