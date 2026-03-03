"""
全局配置 - 所有模块共享的常量
"""

# ─── 设备 ────────────────────────────────────────────────────
DEVICE_SERIAL = None          # None = 自动选唯一 USB 设备
APP_PACKAGE = "com.xingin.xhs"
APP_ACTIVITY = ".activity.SplashActivity"

# ─── 代理 ────────────────────────────────────────────────────
PROXY_PORT = 8080

# 实测（v9.19.5）各功能使用的主机和路径
TARGET_HOSTS = {
    "so.xiaohongshu.com",      # 搜索
    "rec.xiaohongshu.com",     # 首页推荐 feed
    "edith.xiaohongshu.com",   # 详情、评论、用户
}

TARGET_PATHS = [
    # 搜索（so.xiaohongshu.com）
    "/api/sns/v10/search/notes",       # 搜索笔记列表
    # 首页推荐（rec.xiaohongshu.com）
    "/api/sns/v6/homefeed",            # 推荐 feed
    "/api/sns/v1/followings/reddot",   # 关注 feed（可选）
    # 笔记详情（edith.xiaohongshu.com）
    "/api/sns/v1/note/detailfeed",     # 帖子详情
    # 评论（edith.xiaohongshu.com）—— 实测 v9.19.5 为 v5
    "/api/sns/v5/note/comment/list",
    "/api/sns/v5/note/comment/sub",
    # 用户笔记（edith.xiaohongshu.com）
    "/api/sns/v2/user/notes",
]

# 向后兼容：单 host 变量（addon 中同时检查 TARGET_HOSTS）
TARGET_HOST = "edith.xiaohongshu.com"

# ─── 操作随机化 ───────────────────────────────────────────────
SWIPE_DURATION_RANGE = (0.3, 0.6)     # 滑动持续时间（秒）
CLICK_JITTER = 5                       # 点击坐标抖动（像素）
OP_DELAY_RANGE = (0.5, 1.5)           # 操作间隔延时
READ_PAUSE_PROBABILITY = 0.2           # 长停顿触发概率
READ_PAUSE_RANGE = (2.0, 4.0)         # 长停顿时长（秒）
TYPING_DELAY_RANGE = (0.05, 0.15)     # 每字符输入延时（秒）
SCROLL_DISTANCE_RANGE = (0.3, 0.6)    # 滑动幅度（屏幕高度比例）

# ─── 抓取行为 ─────────────────────────────────────────────────
NOTES_PER_KEYWORD = (15, 25)          # 每关键词目标笔记数
COMMENTS_SCROLL_RANGE = (2, 5)        # 每笔记评论滚动次数
INTER_KEYWORD_DELAY = (30, 90)        # 关键词间隔（秒）
DAILY_NOTE_LIMIT = 500                 # 每日笔记上限
