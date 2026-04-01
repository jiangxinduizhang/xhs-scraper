# 开盘啦迁移接续页

当前状态：

- 仓库远程：`origin = git@github.com:jiangxinduizhang/xhs-scraper.git`
- 当前分支：`dev-kpl`
- 开发方式：Mac mini 单机开发 + 真机验证
- 当前目标：在保留已打通最小闭环的前提下，把 OpenClaw skill 从“单一页面 demo”升级为“通用采集桥”
- 开盘啦正式适配包：`src/apps/kaipanla/`
- OpenClaw skill：`skills/openclaw-kaipanla-bridge/`

## 一句话结论

这不是直接复用小红书业务逻辑，而是复用“UI 控制 + 抓包 + 入库 + 异常兜底”的框架骨架，再为 `开盘啦` 重写适配层。

同时，OpenClaw 侧现在不应再把它理解成“固定抓市场情绪页的 skill”，而应理解成：

**一个由人类指定采集目标、由 skill 负责执行/校验/回读/解读的通用采集桥。**

## 当前已确认的关键点

1. `xhs-scraper` 对小红书是强绑定实现，不能直接拿来抓别的 App。
2. `Mac mini + 已 root 的 OnePlus` 足以作为唯一执行环境。
3. 迁移时最容易踩坑的是：
   - 误把小红书 host/path/package 迁移过去
   - 先大改框架而不是先做最小验证
   - 在没有抓包证据前硬写 parser
   - 忘记清理代理，导致手机断网
4. OpenClaw skill 接入已经打通：
   - repo root 可通过 `repo-root.txt` 持久化
   - launcher 会优先使用 venv / Python 3.11+
   - OpenClaw 可自然语言触发 `status/latest/report/capture`
5. 当前 `market_emotion` 流程只是一个**已打通预设任务**，不是 skill 的全部能力边界。

## 必须记住的闭坑点

1. 不要用 resourceId 做小红书式迁移假设，目标 App 的页面结构要重新确认。
2. 不要先写大量代码，先验证能否看到真实请求。
3. 不要假设 `mitmproxy` 一定能解密，先确认证书链路和 pinning。
4. 不要假设目标 App 是内容流，金融类 App 常常是行情、图表、WebSocket、加密协议。
5. 不要忘记代理退出流程，否则手机可能会“看起来像断网”。
6. 不要把某一个预设任务（例如 `market_emotion`）误当成整个 skill 的产品定义。
7. 不要把“人话摘要”当成采集闭环是否成立的判定标准；最终判定门仍然是 `verify`。

## 迁移方案顺序

1. Mac mini 环境就绪检查
2. 目标 App 画像确认
3. 抓包可见性验证
4. UI 可控性验证
5. 最小闭环打通
6. 再扩字段和页面
7. 最后再做更好的任务抽象、交互和总结层

## 最小闭环定义

必须至少完成以下链路：

1. 启动 App
2. 进入一个目标页面
3. 触发一个真实请求
4. `mitmproxy` 拦截到响应
5. parser 解析出结构化记录
6. 写入 SQLite
7. 导出成功
8. `verify=verified`

## OpenClaw skill 新定位（当前建议）

## 架构职责边界（当前定稿）

### 一句话原则

**OpenClaw 负责意图，Kaipanla runtime 负责能力。**

### Kaipanla runtime 的职责

Kaipanla runtime 应逐步升级为一个“面向开盘啦的通用采集执行器”，负责：

- 定义可执行任务协议
- 执行导航 / 抓取 / 解析 / 落盘
- 产出 run / report / raw / db / verification
- 将可稳定复用的能力沉淀为 preset 或组合任务能力

它不负责：

- 多轮自然语言对话
- 猜测用户的模糊意图
- 代替上层做复杂解释和交互
- 假装底层已经支持 App 内所有页面

### OpenClaw 的职责

OpenClaw 是这个 runtime 的自然语言入口和调度层，负责：

- 理解人类自然语言
- 判断意图是 capture / status / read
- 高歧义时只追问一次最关键问题
- 把自然语言映射成 preset / task spec / output preference
- 调用 runtime 并读取结果
- 将结构化结果解释为人话版 / trader-style / 对比版输出

它不负责：

- 把底层采集能力硬编码在自己身上
- 用 prompt 假装支持尚未实现的页面/模块
- 把“自然语言理解”误当成“底层能力已存在”

### 关于“是否能采集这个 App 的所有信息”

结论：**理论上可以逐步逼近，但不应作为默认产品承诺。**

原因：

1. 已知且稳定的页面/模块，适合沉淀为 preset/task，这是主线能力。
2. 需要翻页、切 tab、点详情、特定时段出现的数据，属于条件性能力，应逐项扩展。
3. 临时入口、深层链路、弹窗、权限态页面等，属于探索型能力，不能直接承诺“全量采集”。

因此，正确目标不是“采集开盘啦全部信息”，而是：

**支持越来越多明确可定义、可验证的开盘啦采集任务。**

### 能力分层（当前建议）

#### 1. 预设模式

- 适合高频、稳定、已知任务
- 例如：`market_emotion`、后续的 `money_flow`、`ranking_focus`
- 是当前产品化主线

#### 2. 组合任务模式

- 适合在已知能力集合里做组合
- 例如：热点 + 资金 + 排行 + 跨日对比
- 仍然属于“已定义能力组合”，不是开放世界探索

#### 3. 探索模式

- 用于发现新页面、新链路、新模块
- 不承诺稳定，不默认对外暴露
- 更像研发/探索流程，而不是成熟产品能力

当前阶段优先级：**先把预设模式和少量组合任务模式做扎实，再考虑探索模式产品化。**

### skill 身份

`openclaw-kaipanla-bridge` 应被视为：

**开盘啦通用采集桥（Kaipanla Capture Bridge）**

职责是：

- 接收人类指定的开盘啦采集目标
- 将目标转成预设任务或近似任务
- 执行采集并产出 run / report / raw / db
- 校验结果是否成立
- 在需要时读取或解读已有结果

### 三类用户意图

#### 1. 执行采集
例如：
- 抓一下开盘啦今天的市场情绪
- 采集排行和资金节奏
- 更新一下今天的数据

处理原则：
- 目标明确就直接执行
- 能稳定映射到预设任务就直接执行
- 表达泛化但系统有默认预设时，可以明确说明“先按默认预设执行”
- 高歧义时只追问一次最关键问题

#### 2. 查询状态
例如：
- 看最近一次运行状态
- 最近一次成功没
- 最新 run 怎么样

处理原则：
- 优先返回 `status` / `verify`
- 说清是否成功、卡点在哪、产物在哪

#### 3. 读取或解读结果
例如：
- 看看今天的市场情况
- 读一下最新报告
- 对比今天和昨天
- 给我人话版总结

处理原则：
- 优先读取最近一次成功且可校验的 run
- 按需求返回状态版、结构化版、人话版、对比版

## 任务模型（设计稿）

当前建议把所有自然语言请求，尽量映射成统一 task spec。

### 建议字段

- `task_id`
- `app`
- `page`
- `modules`
- `goal`
- `output`
- `compare`
- `interpretation_style`
- `success_criteria`
- `max_attempts`
- `timeout_sec`

### 设计意图

- `page`：采哪个页面
- `modules`：采哪些模块
- `goal`：本次任务目的
- `output`：要 raw / json / report / summary 哪些输出
- `compare`：是否做跨日或跨 run 对比
- `interpretation_style`：是否要 trader 风格 / 人话总结

## 预设任务与自定义任务（设计稿）

### 预设任务

适合高频、已知、执行稳定的任务。

当前建议：

- `market_emotion`：当前已打通的默认预设
- `ranking_focus`：后续候选
- `money_flow`：后续候选
- `strong_stocks`：后续候选

### 自定义任务

适合用户直接描述自己的目标，而不是引用预设名称。

例如：

- 抓行情页里的排行、资金、风口异动
- 只采情绪页，不用做人话总结
- 抓今天盘面，并和上个交易日比较

如果暂时还不能完整支持自定义任务，也要明确告诉用户：当前先按哪个预设或近似任务执行，不要假装系统已经完全理解。

## 默认策略（设计稿）

### 明确请求

用户已经说清页面、模块或结果类型时：
- 直接执行或回读
- 不要多问

### 泛化但可默认

例如：
- 抓一下开盘啦最新状况
- 看看今天怎么样

处理方式：
- 可以先按默认预设执行（当前通常是 `market_emotion`）
- 但要明确告诉用户这是默认预设，不是唯一理解

### 高歧义请求

如果无法判断采集目标，就只追问一次最关键问题，例如：

- 你这次想抓哪个方向：市场情绪、排行/连板、资金节奏，还是你指定的页面？

## 输出分层（设计稿）

### 1. 状态版

适合快速确认是否跑通。

应包含：
- run id / task id
- `status`
- `verify`
- 主要产物路径
- 错误摘要（如失败）

### 2. 结构化版

适合程序消费或人工复查。

应优先引用：
- JSON 结果
- counts
- `market_summary`
- `day_compare`

### 3. 人话版

适合老板直接阅读。

应包含：
- 简洁结论
- 热点 / 资金 / 风险 / 观察点
- 已实现时可用 trader-style / 复盘口吻

原则：

**摘要属于结果消费层，不是采集成功定义。**

## Mac mini 侧需要验证的物料

- `git`
- `Python`
- `Node.js`
- `adb`
- `mitmproxy`
- `uiautomator2`
- 已 root 手机
- USB 数据线
- 可用的证书信任链

## 当前文档入口

- [总览索引](Docs/00-%E6%80%BB%E8%A7%88%E7%B4%A2%E5%BC%95.md)
- [单机方案](Docs/07-开盘啦迁移方案.md)
- [Mac mini 物料与验证清单](Docs/08-Mac-mini物料与验证清单.md)
- [AI 自动闭环方案 - 项目内部建设](Docs/09-AI自动闭环方案.md)
- [AI 对外暴露与工具接入方案](Docs/10-AI对外暴露与工具接入方案.md)
- [开盘啦适配说明](Docs/kaipanla/README.md)
- [OpenClaw skill 入口](skills/openclaw-kaipanla-bridge/SKILL.md)

后续所有项目内部建设，优先按 [Docs/09-AI自动闭环方案.md](Docs/09-AI%E8%87%AA%E5%8A%A8%E9%97%AD%E7%8E%AF%E6%96%B9%E6%A1%88.md) 中的“验收标准 / 反省标准”执行。

外部 AI Agent 的接入方式按 [Docs/10-AI对外暴露与工具接入方案.md](Docs/10-AI%E5%AF%B9%E5%A4%96%E6%9A%B4%E9%9C%B2%E4%B8%8E%E5%B7%A5%E5%85%B7%E6%8E%A5%E5%85%A5%E6%96%B9%E6%A1%88.md) 执行，只通过 skill / tool / script / 产物交互，不读取仓库源码作为接入前提。

OpenClaw skill 的 live 使用方式：

- 将 `skills/openclaw-kaipanla-bridge/` 同步到 OpenClaw 可扫描的 `skills/` 目录
- 不再依赖 `scripts/install_openclaw_skill.sh`
- 通过 `repo-root.txt` 或环境变量持久化仓库根目录

## 下次接续时优先看这些文件

- [KPL_HANDOFF.md](KPL_HANDOFF.md)
- [skills/openclaw-kaipanla-bridge/SKILL.md](skills/openclaw-kaipanla-bridge/SKILL.md)
- [Docs/07-开盘啦迁移方案.md](Docs/07-%E5%BC%80%E7%9B%98%E5%95%A6%E8%BF%81%E7%A7%BB%E6%96%B9%E6%A1%88.md)
- [Docs/08-Mac-mini物料与验证清单.md](Docs/08-Mac-mini%E7%89%A9%E6%96%99%E4%B8%8E%E9%AA%8C%E8%AF%81%E6%B8%85%E5%8D%95.md)
