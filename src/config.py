"""
全局配置 - 所有模块共享的常量
"""

from __future__ import annotations

import os


def _env_csv(name: str, default: str) -> list[str]:
    value = os.getenv(name, default)
    return [part.strip() for part in value.split(",") if part.strip()]


# ─── 设备 ────────────────────────────────────────────────────
DEVICE_SERIAL = os.getenv("DEVICE_SERIAL") or None
APP_PACKAGE = os.getenv("APP_PACKAGE", "com.xingin.xhs")
APP_ACTIVITY = os.getenv("APP_ACTIVITY", ".activity.SplashActivity")

# ─── 代理 ────────────────────────────────────────────────────
PROXY_PORT = 8080

# 默认仍保留小红书配置，便于老测试继续运行；可通过环境变量覆盖到开盘啦
TARGET_HOSTS = set(
    _env_csv(
        "TARGET_HOSTS",
        "so.xiaohongshu.com,rec.xiaohongshu.com,edith.xiaohongshu.com",
    )
)

TARGET_PATHS = _env_csv(
    "TARGET_PATHS",
    "/api/sns/v10/search/notes,"
    "/api/sns/v6/homefeed,"
    "/api/sns/v1/followings/reddot,"
    "/api/sns/v1/note/detailfeed,"
    "/api/sns/v5/note/comment/list,"
    "/api/sns/v5/note/comment/sub,"
    "/api/sns/v2/user/notes",
)

# 向后兼容：单 host 变量（addon 中同时检查 TARGET_HOSTS）
TARGET_HOST = next(iter(TARGET_HOSTS), "")

# ─── 操作随机化 ───────────────────────────────────────────────
SWIPE_DURATION_RANGE = (0.3, 0.6)     # 滑动持续时间（秒）
CLICK_JITTER = 5                       # 点击坐标抖动（像素）
OP_DELAY_RANGE = (0.5, 1.5)           # 操作间隔延时
READ_PAUSE_PROBABILITY = 0.2           # 长停顿触发概率
READ_PAUSE_RANGE = (2.0, 4.0)         # 长停顿时长（秒）
TYPING_DELAY_RANGE = (0.05, 0.15)     # 每字符输入延时（秒）
SCROLL_DISTANCE_RANGE = (0.3, 0.6)    # 滑动幅度（屏幕高度比例）

# ─── 抓取行为 ─────────────────────────────────────────────────
NOTES_PER_KEYWORD = (15, 25)           # 每关键词采集笔记数
COMMENTS_SCROLL_RANGE = (2, 5)        # 每笔记评论滚动次数
INTER_KEYWORD_DELAY = (30, 90)        # 关键词间隔（秒）
DAILY_NOTE_LIMIT = 500                 # 每日笔记上限

# ─── 会话级反封号 ─────────────────────────────────────────
WORK_HOURS = (8, 23)                   # 模拟人类活跃时段
IDLE_PROBABILITY = 0.05                # 每次操作后"走神"概率
IDLE_DURATION_RANGE = (30, 120)        # 走神时长（秒）
SESSION_MAX_DURATION = 3600            # 单次会话最长时间（秒）
COOLDOWN_AFTER_SESSION = (300, 600)    # 会话间冷却时间（秒）
