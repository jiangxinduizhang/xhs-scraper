# 开盘啦 bridge 第一轮实施清单（对齐合并版总方案）

> 本清单服从 `Docs/kaipanla-bridge-architecture.md`。
> 第一轮目标不是让 bridge 更聪明，而是补齐形成闭环所需的**最小执行与证据能力**。

---

## 0. 第一轮的边界

第一轮只解决：

1. bridge 是否能支持 AI 做多轮 exploration loop
2. evidence bundle 是否足够支撑 AI 判断继续/停止/ask human
3. exploration verify/report 是否去结论化

第一轮不解决：
- 页面语义识别增强
- 自动 promote
- 页面业务摘要优化
- 大量新页面扩展
- bridge 自己做策略建议

---

## 1. 按对象拆分的实施项

## 1.1 bridge / runtime：必须实现

### P0-1. exploration round schema
bridge 必须支持 round 化执行，而不只是一次性 preset 跑完退出。

最小需要：
- `round_index`
- `max_rounds`
- `action_plan`
- `capture_options`
- `session_id`（如已支持会话）

### P0-2. step-level action execution
bridge 必须支持这些最小动作：
- `tap_text`
- `tap_text_or_fallback`
- `tap_coord`
- `wait`
- `back`
- `swipe`
- `screenshot`
- `dump_ui`
- `visible_text`
- `capture_request_window`

### P0-3. before/after evidence
bridge 必须为关键动作输出：
- screenshot_before / after
- ui_dump_before / after
- visible_text_before / after
- request pre_window / post_window
- new_paths / new_keys / new_records
- first_seen_after_action_ms

### P0-4. exploration evidence bundle v2
至少包含：
- `action_facts`
- `ui_facts`
- `request_facts`
- `structure_facts`
- `artifact_facts`
- `round_index`
- `max_rounds`
- `evidence_status`

### P0-5. exploration verify/report 新口径
只允许输出：
- `evidence_complete`
- `evidence_partial`
- `evidence_insufficient`

禁止输出：
- `verified`
- `page_success`
- `main_block_found`
- `ready_to_promote`

### P1：应该实现
- 动作失败原因结构化
- UI 差分摘要
- 请求噪声基线
- 多动作时间窗差分

### P2：后续实现
- 持久 session 恢复
- 更强 UI 证据能力
- recipe/promote 挂载接口

---

## 1.2 AI / OpenClaw：必须承担

这些不是 bridge 任务，必须由 AI 承担：

### P0
- 定义每轮探索目标
- 判断证据是否足够
- 判断是否继续下一轮
- 判断是否 ask human
- 判断是否可以对外宣告成功
- 判断是否值得沉淀 reusable recipe

### P1
- 比较多轮证据的改善情况
- 解释冲突证据
- 在 registered 失效时回退到 exploration

### 禁止
- 把 preset 名称当成功证据
- 把 `page_flow_complete` 当页面语义成功
- 把 key 命中直接解释为目标主块

---

## 1.3 SKILL：必须补充

SKILL 必须写成“AI 的使用逻辑手册”，而不是 bridge 能力广告。

### 必须补：
- 什么时候走 registered，什么时候走 exploration
- exploration loop 如何做
- 什么时候继续
- 什么时候停
- 什么时候 ask human
- 什么时候可以告诉 human 成功
- 什么时候可以沉淀 reusable recipe
- 什么时候可以 promote 成 registered

### 必须明确：
- bridge 输出的是事实，不是最终业务结论
- AI 必须自己承担成功/失败/不确定性的解释

---

## 2. ExplorationEvidenceBundleV2 草案

```json
{
  "mode": "exploration",
  "session_id": "optional",
  "round_index": 1,
  "max_rounds": 3,
  "target_hint": "龙虎榜",
  "action_facts": {
    "steps": [
      {
        "type": "tap_text",
        "target": "龙虎榜",
        "timestamp": "2026-04-02T16:30:00+08:00",
        "found": true,
        "executed": true,
        "error": ""
      }
    ]
  },
  "ui_facts": {
    "screenshot_before": "...",
    "screenshot_after": "...",
    "ui_dump_before": "...",
    "ui_dump_after": "...",
    "visible_text_before": [],
    "visible_text_after": [],
    "visible_text_diff": [],
    "ui_changed": true
  },
  "request_facts": {
    "pre_window_count": 2,
    "post_window_count": 5,
    "new_paths": ["/w1/api/index.php"],
    "new_keys": ["List", "Topic"],
    "new_requests": [
      {
        "path": "/w1/api/index.php",
        "keys": ["List", "Topic"],
        "first_seen_after_action_ms": 320
      }
    ]
  },
  "structure_facts": {
    "observed_keys": ["List", "Topic"],
    "candidate_structures": [],
    "noise_structures": []
  },
  "artifact_facts": {
    "raw_paths": ["..."],
    "report_path": "...",
    "db_path": "..."
  },
  "evidence_status": "evidence_complete"
}
```

说明：
- 允许有 `candidate_structures`，但它只能是事实归类，不是业务结论。
- 不允许出现“龙虎榜已确认”这种 bridge 结论字段。

---

## 3. 第一轮验收

## 3.1 bridge/runtime 验收
必须能看到：
- 至少一轮真实 exploration 输出 before/after 证据
- request delta 是动作相关的，不是全量模糊回读
- verify/report 已改为 evidence 口径

## 3.2 AI/Skill 验收
必须能说明：
- 为什么继续下一轮
- 为什么停止
- 为什么 ask human
- 为什么当前还不能宣告成功

## 3.3 边界验收
必须确认：
- 没有把判断责任塞回 bridge
- 没有把 skill 写成 bridge 能力幻想说明书
- 没有把 AI 的弱推测包装成成功

---

## 4. 第一轮完成即停

第一轮达到以下条件即停止，不扩 scope：
- round 化 exploration 可以跑
- evidence bundle v2 可消费
- exploration verify/report 改口径
- SKILL 已明确 loop / stop / ask-human / success / reuse 规则
- 至少一个真实 run 可复核

达到后再进入第二轮，不顺手补：
- 自动 promote
- 更多页面特化
- bridge 业务识别增强
- 注册页体系大改
