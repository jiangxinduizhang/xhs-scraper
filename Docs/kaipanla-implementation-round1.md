# 开盘啦桥接器第一轮实施清单

> 本清单服从 `Docs/kaipanla-bridge-architecture.md`。
> 第一轮目标不是让 bridge 更会判断，而是让它产出更完整、可供 AI 判读的事实证据包。

---

## 1. 第一轮目标

第一轮只做两件事：

1. **定义并落地 exploration evidence bundle v2**
2. **定义并落地 AI 消费 evidence bundle 的最小控制协议**

第一轮不做：
- promote
- 页面专属语义识别增强
- 更强 registered 页面判断
- 业务摘要优化
- 通过规则堆叠让 bridge 看起来“更懂页面”

---

## 2. 必须实现

### 2.1 exploration evidence bundle v2

exploration 结果必须至少包含以下五组事实：

#### A. 动作事实
- 本轮动作列表
- 每步动作类型
- 每步动作时间点
- 点击目标
- 点击是否找到文本/元素
- 是否执行点击/等待/滑动

#### B. UI 事实
- 点击前截图路径（如可用）
- 点击后截图路径（如可用）
- 点击前 UI dump 路径（如可用）
- 点击后 UI dump 路径（如可用）
- 是否检测到 UI 变化
- 可见文本变化摘要（最小可为空）

#### C. 请求事实
- 点击前时间窗请求计数
- 点击后时间窗请求计数
- 点击后新增请求列表
- 请求 path 摘要
- 请求 keys/shape 摘要
- 哪些请求只出现在点击后

#### D. 候选结构事实
- candidate_structures
- noise_structures
- 每个结构的 key / kind / shape / repetition
- 每个结构首次出现相对点击事件的时序信息
- 候选结构与噪声结构的事实性理由

#### E. 轮次元信息
- round_index
- max_rounds
- target_hint
- control_directive（本轮 AI 给的控制指令）
- evidence_status

### 2.2 exploration verify 新口径

exploration verify 第一轮只允许输出证据完备度，不允许输出页面成功结论。

允许的口径：
- `evidence_complete`
- `evidence_partial`
- `evidence_insufficient`

不允许的口径：
- `verified`
- `success`
- `reached`
- `stable_capture`
- `ready_to_promote`

### 2.3 exploration report 新口径

exploration report 必须是“探测报告”，至少包含：
- 本轮做了什么
- 本轮新增了什么证据
- 当前主要候选结构
- 当前主要噪声结构
- 当前主要不确定性
- 下一轮建议动作（如果有）
- 是否建议 ask human（如果有）

禁止写成：
- 页面已抓取完成
- 已进入目标页主块
- 已稳定命中目标数据

### 2.4 AI 控制协议 v1

第一轮必须定义一个最小 AI 控制协议，用于驱动下一轮 exploration。

允许的控制动作只包含：
- `continue_same_path`
- `tighten_target_hint`
- `capture_ui_before_after`
- `focus_post_tap_window`
- `stop`
- `ask_human`

AI 控制协议必须能表达：
- 为什么继续/停止
- 下一轮最小动作是什么
- 当前不确定性的核心点是什么

---

## 3. 禁止实现

第一轮明确禁止以下实现：

### 3.1 禁止把识别责任塞进 bridge
- bridge 直接判断“是否进入目标主块”
- bridge 直接判断“这就是龙虎榜数据”
- bridge 直接输出 promote/reached/main_block_found 一类强语义状态

### 3.2 禁止靠页面特化规则止血
- 为 dragon_tiger 单独堆越来越厚的业务规则
- 用 generic key -> 页面成功 的方式继续糊逻辑
- 用更复杂 detector 代替 AI 判读职责

### 3.3 禁止 scope 膨胀
- 不接更多新页面
- 不做自动 promote
- 不做厚重 DSL
- 不做开放式自然语言理解进入 runtime
- 不重写整个 registered 流程

---

## 4. 输入/输出 schema 草案

## 4.1 ExplorationTaskV2（草案）

```json
{
  "mode": "exploration",
  "target_hint": "龙虎榜",
  "round_index": 1,
  "max_rounds": 2,
  "control_directive": {
    "action": "capture_ui_before_after",
    "reason": "需要对比点击前后 UI 与请求变化"
  },
  "navigation_hint": {
    "entry_tab": "行情",
    "entry_text": "龙虎榜"
  },
  "capture_options": {
    "screenshot_before_after": true,
    "ui_dump_before_after": true,
    "focus_post_tap_window": true
  }
}
```

说明：
- `control_directive` 是 AI 给 bridge 的最小控制指令，不是 bridge 自己想出来的决策。
- `navigation_hint` 允许存在，但不等于页面语义已确认。
- `capture_options` 是证据采集选项，不是识别规则。

## 4.2 ExplorationEvidenceBundleV2（草案）

```json
{
  "mode": "exploration",
  "round_index": 1,
  "max_rounds": 2,
  "target_hint": "龙虎榜",
  "control_directive": {
    "action": "capture_ui_before_after",
    "reason": "需要对比点击前后 UI 与请求变化"
  },
  "action_facts": {
    "steps": [
      {
        "type": "tap_text",
        "target": "龙虎榜",
        "timestamp": "2026-04-02T13:00:00+08:00",
        "found": true,
        "executed": true
      }
    ]
  },
  "ui_facts": {
    "screenshot_before": "...",
    "screenshot_after": "...",
    "ui_dump_before": "...",
    "ui_dump_after": "...",
    "ui_changed": true,
    "visible_text_diff": []
  },
  "request_facts": {
    "pre_window_count": 2,
    "post_window_count": 5,
    "new_requests": [
      {
        "path": "/w1/api/index.php",
        "keys": ["List", "Topic"],
        "kind": "dict"
      }
    ],
    "post_navigation_only": []
  },
  "structure_facts": {
    "candidate_structures": [
      {
        "name": "candidate_1",
        "keys": ["List", "Topic"],
        "kind": "dict",
        "repetition": 2,
        "first_seen_after_tap_ms": 320
      }
    ],
    "noise_structures": [
      {
        "name": "noise_1",
        "keys": ["Ad_5", "IndexAd"],
        "kind": "dict",
        "reason": "ad_or_public_block"
      }
    ]
  },
  "evidence_status": "evidence_complete",
  "next_action_suggestion": {
    "action": "focus_post_tap_window",
    "reason": "点击后新增请求仍混有公共块，需收紧时间窗"
  }
}
```

说明：
- `candidate_structures` / `noise_structures` 是事实性归类，不是业务最终判定。
- `next_action_suggestion` 只能是“下一轮探测建议”，不是“页面已经成功”。

---

## 5. 第一轮代码改动范围

第一轮允许改动的模块：
- `src/apps/kaipanla/exploration.py`
- `src/apps/kaipanla/task.py`
- `src/apps/kaipanla/verify.py`
- `src/apps/kaipanla/report.py`
- `scripts/kpl_tool.py`
- 对应 unit tests

第一轮原则：
- 优先改 exploration 路径
- 尽量少碰 registered 逻辑
- 如需兼容旧字段，应明确标注 deprecated / compatibility only

---

## 6. 验收标准

第一轮完成必须满足：

### 6.1 文档验收
- 架构文档与本实施清单一致
- 不存在明显鼓励 bridge 承担识别责任的条目

### 6.2 单测验收
至少覆盖：
- evidence bundle 必填字段
- exploration verify 新口径
- exploration report 新口径
- control_directive 能正确透传
- candidate/noise structures 能结构化输出

### 6.3 真机/真实 run 验收
至少完成 1 个真实 exploration run，并能看到：
- 动作事实
- UI 事实（若环境支持）
- 请求事实
- 候选/噪声结构事实
- 明确的 evidence_status

### 6.4 边界验收
必须确认：
- 输出中没有“页面已成功”“主块已找到”这类 bridge 结论
- 没有把 AI 识别职责偷塞回 runtime

---

## 7. 停止条件

第一轮达到以下条件即停止，不继续扩 scope：
- evidence bundle v2 能稳定产出
- control protocol v1 能跑通
- exploration verify/report 已改口径
- 至少一轮真实 run 可复核
- 单测通过

达到后，下一步才讨论第二轮，不允许继续顺手补：
- promote
- 更多页面特化
- 更强页面识别
- registered 大改

---

## 8. 提交前自检

每次提交前必须回答：

1. 这次改动是在补“事实证据”，还是又在补“业务判断”？
2. 输出字段是事实型，还是结论型？
3. 这次如果只做一半，是否仍是可验证增量？
4. 有没有被现有 reached / verified / ready 一类旧结构带偏？

只要第 1 或第 2 问答案不稳，就先停。
