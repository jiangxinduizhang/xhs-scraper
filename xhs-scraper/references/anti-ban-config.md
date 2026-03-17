# 反封号配置参数说明

所有参数在 `src/config.py` 中定义。

## 操作随机化

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `SWIPE_DURATION_RANGE` | (0.3, 0.6) | 滑动持续时间（秒） |
| `CLICK_JITTER` | 5 | 点击坐标偏移（像素） |
| `OP_DELAY_RANGE` | (0.5, 1.5) | 操作间隔延时（秒） |
| `READ_PAUSE_PROBABILITY` | 0.2 | 长停顿触发概率 |
| `READ_PAUSE_RANGE` | (2.0, 4.0) | 长停顿时长（秒） |
| `TYPING_DELAY_RANGE` | (0.05, 0.15) | 每字符输入延时（秒） |
| `SCROLL_DISTANCE_RANGE` | (0.3, 0.6) | 滑动距离（屏幕高度比例） |

## 采集行为

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `NOTES_PER_KEYWORD` | (15, 25) | 每关键词采集笔记数 |
| `COMMENTS_SCROLL_RANGE` | (2, 5) | 每笔记评论滚动次数 |
| `INTER_KEYWORD_DELAY` | (30, 90) | 关键词间隔（秒） |
| `DAILY_NOTE_LIMIT` | 500 | 每日笔记上限 |

## 会话级控制

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `WORK_HOURS` | (8, 23) | 活跃时段（24h） |
| `IDLE_PROBABILITY` | 0.05 | 走神概率 |
| `IDLE_DURATION_RANGE` | (30, 120) | 走神时长（秒） |
| `SESSION_MAX_DURATION` | 3600 | 单次会话上限（秒） |
| `COOLDOWN_AFTER_SESSION` | (300, 600) | 会话间冷却（秒） |

## 内置行为模拟（硬编码）

| 行为 | 概率 | 说明 |
|------|------|------|
| 快速略过 | 15% | 进详情后秒退 |
| 随机浏览 | 10% | 详情页额外操作 |

## 调优建议

### 保守模式
```python
NOTES_PER_KEYWORD = (5, 10)
INTER_KEYWORD_DELAY = (60, 180)
IDLE_PROBABILITY = 0.10
DAILY_NOTE_LIMIT = 200
```

### 激进模式（风险较高）
```python
NOTES_PER_KEYWORD = (30, 50)
INTER_KEYWORD_DELAY = (15, 30)
IDLE_PROBABILITY = 0.02
DAILY_NOTE_LIMIT = 1000
```

### 大批量（100 条/关键词）
```python
NOTES_PER_KEYWORD = (100, 100)  # 完成后记得恢复
```
