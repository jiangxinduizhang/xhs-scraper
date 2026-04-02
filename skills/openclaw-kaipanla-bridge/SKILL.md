---
name: openclaw-kaipanla-bridge
description: "开盘啦执行桥：用于执行、校验、回读和取证式 exploration 的开盘啦 APP 任务。适用于抓市场情绪、排行、连板、资金、题材、个股、板块、龙虎榜，查询最近运行状态，读取已有结果，或按明确任务收集页面证据包。"
---

# 开盘啦执行桥（AI 使用手册）

这个 skill 不是 bridge 的能力广告，而是：

> **AI 在使用开盘啦 bridge 时必须遵循的操作手册。**

严格边界：
- **AI / OpenClaw**：理解、识别、判断、控制下一步、ask human、对外解释、决定是否成功、决定是否沉淀复用
- **bridge / runtime**：执行动作、抓包、采集 UI/请求/结构事实、落盘、回读、校验产物完整性
- **SKILL**：规定 AI 该怎么用 bridge，什么时候 loop，什么时候停，什么时候 ask human，什么时候才可以告诉 human 成功

一句话：

**bridge 是手和相机；AI 是脑子；SKILL 是操作手册。**

---

## 1. 先判断：registered 还是 exploration

### 走 registered，当且仅当：
- 目标页面已有稳定 preset/page
- 当前任务是复用既定路径，而不是摸索路径
- 你要的是执行与回读，不是探索页面语义

常用命令：
- `capture`
- `verify`
- `report`
- `latest`
- `status`

### 走 exploration，当出现以下任一情况：
- 页面是新的
- 页面可能改版了
- 已知 preset 跑出来的证据不像目标页
- 需要 AI 边看证据边决定下一步动作
- 用户明确要“探索/取证/验证到底抓到了什么”

常用命令：
- `explore`
- 必要时配合 `report` / `verify` / `latest`

注意：
- 不要把 `explore` 当成 runtime 自己理解意图的入口
- exploration task 应该始终是明确的、执行导向的

---

## 2. AI 的核心工作流

### A. 用户要“执行已知任务”
1. AI 判断该任务是否已有稳定 registered preset
2. 若有，调用 `capture`
3. 再读取 `verify` / `report` / `latest`
4. AI 自己判断对外如何解释

### B. 用户要“探索/验证页面”
1. AI 先定义当前轮最小目标
2. 调用 `explore`（或 round 化 exploration 执行接口）
3. 读取 evidence bundle
4. AI 判断：
   - 是否更接近目标
   - 是否继续下一轮
   - 是否 ask human
   - 是否可以宣布成功
5. **当前最小可试用版本：最多自动做 2 轮 exploration，然后必须输出自然语言结果或 ask human**

---

## 3. exploration loop 规则（必须遵守）

### 每轮只解决一个核心不确定性
例如：
- “点击底部龙虎榜后，是否出现新请求？”
- “点击后 UI 是否真的变化？”
- “当前抓到的是公共块还是候选主块？”

不要一轮混进太多目标，例如同时：
- 点多个入口
- 滑很多次
- 切多个 tab
- 既想确认 UI，又想确认多个请求候选块

### 默认 loop 流程
1. 定义本轮最小动作
2. 让 bridge 执行并收集证据
3. 读 evidence bundle
4. 判断是否增信
5. 决定继续 / 停止 / ask human / 宣告成功

### 最小可试用闭环（当前强制规则）
- 默认最多自动执行 **2 轮 exploration**
- 第 2 轮必须显式基于第 1 轮证据生成，不能碰运气重跑
- 第 2 轮后必须二选一：
  - 向用户给出自然语言结果
  - ask human
- 不允许在当前阶段无限 loop

### 什么时候继续 loop
只有当你能明确说出“为什么继续”时才继续，例如：
- 本轮比上轮更接近目标
- 再做一个动作就能显著增信
- 当前冲突证据可通过下一轮澄清
- 仍在合理 max_rounds 内，且不是碰运气

### 什么时候停止 loop
应停止于以下任一情况：
- 当前证据已足够支持结论
- 连续两轮没有增信
- 下一轮动作没有明确目的
- 已到 max_rounds
- 再继续只能靠猜
- 目标定义本身不清

---

## 4. 什么时候必须 ask human

ask human 只能由 AI 发起，bridge 不发起业务 ask human。

### 必须 ask human 的场景
- 用户目标不清：要“主块”还是“相关数据即可”
- UI 证据和请求证据冲突
- 连续两轮主要还是公共块/噪声块
- 下一步只能靠业务语义猜测推进
- 是否接受“半稳定可用路径”需要用户拍板

### ask human 时要问清楚什么
优先问：
- 你要锁定页面主块，还是任意相关数据即可？
- 你要的是完成一次探索，还是沉淀成稳定可复用抓取？
- 当前这种证据强度是否足够作为“成功”？

---

## 5. 什么时候可以告诉 human“探索成功”

只有 AI 可以下这个结论，而且要保守。

### 至少满足以下条件才可说成功
1. **动作证据成立**
   - 已执行目标导航/点击动作
2. **证据差分成立**
   - 动作后出现新的、与目标高度相关的请求 / 结构 / UI 变化
3. **不是公共噪声重复**
   - 不是首页公共块、广告块、缓存块的重复出现
4. **AI 能解释为什么成功**
   - 能清楚说明“做了什么 → 新出现什么 → 为什么这足够支持成功”

### 不允许仅凭这些就宣告成功
- preset 名叫 `dragon_tiger`
- step event 里有 `tap_dragon_tiger_tab`
- report 写了“采集龙虎榜页相关产物”
- 出现几个 generic keys

### 如果证据不够，只能这么说
- “动作已执行，但还不能确认目标页核心数据已抓到”
- “当前只有候选证据，不足以宣布成功”

---

## 6. 什么时候可以沉淀经验复用

AI 可以沉淀经验，但不能把“经验沉淀”混成 bridge 自己会判断。

### 可沉淀为 reusable recipe 的内容
- 点击顺序
- 推荐等待时长
- 进入某页面前后的最佳动作顺序
- 哪些动作不要做
- 哪些噪声块通常会出现
- 哪类证据最能增信

例如：
- 进入行情后先点底部龙虎榜 tab，不要先滑动
- 点击后等待 2~3 秒再抓 post-window 请求
- `Index/MsgTop/DaBanList` 等默认视为公共基线噪声

### 已验证可复用：进入龙虎榜页面（2026-04-02）
适用意图：
- “去开盘啦看最新龙虎榜”
- “进入龙虎榜页面”
- “先切到实时龙虎榜也行”

最小已验证流程：
1. round1 允许按 `dragon_tiger` exploration 收集首页证据
2. 若仍是首页/推荐流，但底部存在 `龙虎榜` 入口，则 round2 下发：
   - `sleep 2s`
   - `tap_text target=龙虎榜`
   - `sleep 2s`
3. runtime 点击策略需支持：
   - `text`
   - `textContains`
   - `description`
   - `descriptionContains`
   - 命中节点后向上寻找可点击祖先
4. 页面成功进入的页面级判定可参考：
   - 仍可见底部 `龙虎榜` 导航锚点
   - UI 不再是首页/推荐流
   - 出现 `今日上榜数`、`股票`、`机构`、`营业部`、`股票名称`
   - 出现 6 位股票代码与股票名列表

注意：
- 这条复用经验当前证明的是“成功进入龙虎榜页面并拿到页面级榜单数据”
- 不自动等价于“已稳定拿到所有龙虎榜主块/机构/营业部完整抓取”

### 环境执行经验（必须先检查）
在当前仓库里，**pytest 可过 ≠ 直接命令行实跑一定可过**。每次准备真实执行前，先检查运行解释器与测试解释器是否一致。

已踩过的坑：
- 直接运行 `python3 scripts/kpl_tool.py ...` 可能落到系统 Python 3.9
- 仓库代码使用了 `@dataclass(slots=True)`，在这条解释器链路下会报：
  - `TypeError: dataclass() got an unexpected keyword argument 'slots'`
- 因此会出现“单测在 3.11 环境通过，但直跑脚本在 3.9 环境失败”的错觉

执行前检查：
1. 先看 `which python3` 与 `python3 --version`
2. 若是 Python 3.9，不要直接把失败归因于 bridge 抓取逻辑
3. 优先切到项目实际测试通过的解释器/虚拟环境，再执行真实抓取
4. 若直跑失败且报 `slots=True`，先按“解释器不匹配”处理，而不是按“页面/抓取失败”处理

已踩过的另一类坑：
- 新增 exploration/agent loop 字段后，测试桩对象可能缺少新字段（例如 `round_index`）
- 这类报错说明的是“测试夹具/接口演化未同步”，不等于真实页面逻辑一定有问题

对外表述规则：
- 如果实跑失败是解释器问题，要明确说“环境/解释器错配”，不要说成“桥接器没抓到数据”
- 如果测试失败是 fake fixture 缺字段，要明确说“测试桩未跟上接口变化”，不要直接夸大为“新版不可用”

### 已验证可复用：从首页顶部进入市场情绪页并拿到请求（2026-04-02）
适用意图：
- “从首页顶部进入市场情绪页”
- “去开盘啦看市场情绪”
- “进入市场情绪页面并拿到请求数据”

最小已验证流程：
1. 以 `market_emotion` preset/exploration 起步
2. 若首页顶部可见 `市场情绪` 文本入口，则执行：
   - `sleep 2s`
   - `tap_text target=市场情绪`
   - `sleep 2s`
3. 页面级成功信号可参考：
   - `市场情绪`
   - `赚钱效应`
   - `综合强度`
   - `涨跌统计`
   - `实际涨停`
   - `实际跌停`
   - `市场量能`
   - `沪深 | 实际量能`
4. 请求级成功信号可参考：
   - run 中 `captured_count > 0`
   - 出现 `market_sentiment` 解析结果
   - 本次成功样本中：`captured_count=5`、`parsed_count=35`、`market_sentiment=27`

本次已验证页面结果（页面级，不等于全部后端结构都已稳定固化）：
- 日期：`2026-04-02`
- 综合强度：`31`
- 市场人气：`一般`
- 实际涨停：`27家`
- 实际跌停：`5家`
- 沪深实际量能：`18430亿`
- 今日预测量能：`18430亿(-8.42%,缩量1695亿)`

注意：
- 这条经验当前可以支持“首页顶部 → 市场情绪页 → 页面结果 + 请求数据”快速复用
- 但还不自动等价于“市场情绪全量后端结构已经完成长期稳定 matcher 固化”
- 下次若 UI 改版，优先复用该 recipe，再根据实际证据微调

### 什么时候只沉淀 reusable recipe，而不 promote
当满足：
- 有一定复用价值
- 但还未足够稳定
- 仍需要 AI 在执行中解释和判断

### 什么时候可以 promote 成 registered
必须由 AI 判断，至少满足：
- 多轮 exploration 路径可复现
- 关键证据结构稳定
- 不再主要依赖人工解释“它大概像”
- 多次 run 都能得到一致闭环

bridge 不得自己决定 promote。

---

## 7. 如何理解 verify / report / status / latest

### registered 下
- `verify`：看产物与既定事实门槛是否完整
- `report`：看执行和结果摘要
- `status/latest`：回读最新产物

### exploration 下
这些输出应理解为：
- 执行事实
- 证据状态
- 产物完整度

不要理解为：
- 已确认进入目标主块
- 已确认拿到目标核心数据

exploration 允许的状态口径：
- `evidence_complete`
- `evidence_partial`
- `evidence_insufficient`

---

## 8. 不要做

- 不要把 bridge 写成判断器
- 不要把 evidence bundle 当最终业务结论
- 不要让 runtime 决定 ask human / success / promote
- 不要没有增信理由就机械重跑
- 不要把 preset 名称 / step 名称 / generic key 命中当作成功
- 不要让 skill 文档暗示 bridge 已拥有不存在的能力

---

## 9. 推荐命令心智

优先使用：

```bash
python3 scripts/kpl_tool.py capture --preset <page>
python3 scripts/kpl_tool.py explore <target-text> --preset <page>
python3 scripts/kpl_tool.py verify --run <run.json>
python3 scripts/kpl_tool.py report --run <run.json>
python3 scripts/kpl_tool.py latest
python3 scripts/kpl_tool.py status
```

注意：
- exploration 时优先显式给 `--preset`
- 不要把 `explore` 当作 bridge 自己理解模糊意图的入口
- 真实结论永远由 AI 在读完证据后给出

---

## 10. 最后的判断准则

每次你想回复用户前，先问自己：

1. 我现在说的是事实，还是结论？
2. 这个结论是 bridge 说的，还是我根据证据判断的？
3. 如果证据不足，我有没有明确说“不足”？
4. 再继续一轮，真的会增信吗？
5. 现在是否已经到了 ask human 的边界？

只要第 2 条答不稳，就不要把 bridge 的输出包装成成功。
