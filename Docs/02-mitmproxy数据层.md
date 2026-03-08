# 02 - mitmproxy 数据层

## 代理配置方式

### USB Tunnel 代理（实际使用方式）

手机与 Mac 不在同一子网，必须走 `adb reverse` USB tunnel：

```bash
# ── 启动 ──
# 1. 建立 USB 端口反向代理
adb reverse tcp:8080 tcp:8080

# 2. 设置手机全局代理
adb shell su -c "settings put global http_proxy 127.0.0.1:8080"

# 3. 启动 mitmdump（addon 自动拦截并存入 DB）
XHS_DB_PATH="data/xiaohongshu.db" mitmdump -p 8080 -s src/proxy/addon.py

# ── 停止 ──
# 必须全部执行，否则手机无法上网！
# 1. 先写 :0 再删除（防止残留）
adb shell su -c "settings put global http_proxy :0"
# 2. 删除所有代理相关设置（4条全删）
adb shell su -c "settings delete global http_proxy"
adb shell su -c "settings delete global global_http_proxy_host"
adb shell su -c "settings delete global global_http_proxy_port"
adb shell su -c "settings delete global global_http_proxy_exclusion_list"
# 3. 移除 adb 端口转发
adb reverse --remove-all
# 4. 如仍无法上网，开关飞行模式刷新网络栈
adb shell su -c "settings put global airplane_mode_on 1"
adb shell su -c "am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true"
sleep 2
adb shell su -c "settings put global airplane_mode_on 0"
adb shell su -c "am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false"
```

> **踩坑记录**：仅执行 `settings delete global http_proxy` 不够，Android 会在
> `global_http_proxy_host`、`global_http_proxy_port`、`global_http_proxy_exclusion_list`
> 中残留值，导致代理停止后手机仍尝试连接已关闭的代理端口，表现为"无法上网"。

---

## 目标 API Endpoint 清单

通过抓包分析，小红书主要 API 域名为 `edith.xiaohongshu.com` 和 `www.xiaohongshu.com`。

| 功能 | URL Pattern | 关键字段 |
|------|------------|---------|
| 首页推荐流 | `/api/sns/v3/page/fresh` | `data.items[].note_card` |
| 关键词搜索 | `/api/sns/v10/search/notes` | `data.items[].note_card` |
| 搜索建议 | `/api/sns/v1/search/suggest` | `data.suggests` |
| 帖子详情 | `/api/sns/v3/note/feed` | `data.note_detail_map` |
| 评论列表 | `/api/sns/v2/note/comments` | `data.comments` |
| 评论回复 | `/api/sns/v2/note/comments/sub` | `data.comments` |
| 用户主页 | `/api/sns/v2/user/profile/me` | `data.basicInfo` |
| 用户笔记 | `/api/sns/v2/user/notes` | `data.notes` |

> 注意：API 路径可能随版本变化，需要定期验证。实际抓包以实测为准。

---

## 拦截脚本结构（addon 模式）

### src/proxy/addon.py

```python
"""
mitmproxy addon - 小红书 API 数据拦截
"""
import json
import logging
from mitmproxy import http
from mitmproxy.http import HTTPFlow
from .parser import XHSParser
from ..storage.db import Database

logger = logging.getLogger(__name__)

# 需要拦截的 API 路径前缀
TARGET_PATHS = [
    "/api/sns/v3/page/fresh",         # 首页推荐
    "/api/sns/v10/search/notes",       # 搜索结果
    "/api/sns/v3/note/feed",           # 帖子详情
    "/api/sns/v2/note/comments",       # 评论列表
    "/api/sns/v2/note/comments/sub",   # 评论回复
    "/api/sns/v2/user/notes",          # 用户笔记
]

TARGET_HOST = "edith.xiaohongshu.com"


class XHSAddon:
    def __init__(self):
        self.db = Database()
        self.parser = XHSParser()

    def response(self, flow: HTTPFlow):
        """拦截并处理 API 响应"""
        if not self._is_target(flow):
            return

        try:
            # 解析响应体
            body = flow.response.get_text()
            data = json.loads(body)

            # 解析并存储
            path = flow.request.path.split("?")[0]
            parsed = self.parser.parse(path, data)
            if parsed:
                self.db.save(parsed)
                logger.info(f"已保存: {path} → {len(parsed)} 条")

            # 同时保存原始数据到 JSONL
            self._save_raw(flow, data)

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"处理失败 {flow.request.url}: {e}")

    def _is_target(self, flow: HTTPFlow) -> bool:
        """判断是否为目标请求"""
        if flow.request.host != TARGET_HOST:
            return False
        path = flow.request.path.split("?")[0]
        return any(path.startswith(p) for p in TARGET_PATHS)

    def _save_raw(self, flow: HTTPFlow, data: dict):
        """保存原始数据到 JSONL"""
        import os
        from datetime import datetime
        os.makedirs("data/raw", exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"data/raw/{date_str}.jsonl"
        with open(filename, "a", encoding="utf-8") as f:
            record = {
                "ts": datetime.now().isoformat(),
                "path": flow.request.path.split("?")[0],
                "data": data,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


# mitmproxy 入口
addons = [XHSAddon()]
```

### src/proxy/parser.py

```python
"""
API 响应解析器 - 将小红书 API 数据转换为统一格式
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class NoteItem:
    note_id: str
    title: str
    desc: str
    author_id: str
    author_name: str
    liked_count: int
    collected_count: int
    comment_count: int
    cover_url: str
    note_type: str           # normal / video
    topics: list[str] = field(default_factory=list)
    crawled_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CommentItem:
    comment_id: str
    note_id: str
    content: str
    author_id: str
    author_name: str
    liked_count: int
    create_time: int
    parent_comment_id: Optional[str] = None


class XHSParser:
    def parse(self, path: str, data: dict) -> list:
        """根据 API 路径分发解析"""
        if "search/notes" in path or "page/fresh" in path:
            return self._parse_note_list(data)
        elif "note/feed" in path:
            return self._parse_note_detail(data)
        elif "comments" in path:
            return self._parse_comments(data)
        return []

    def _parse_note_list(self, data: dict) -> list[NoteItem]:
        items = data.get("data", {}).get("items", [])
        result = []
        for item in items:
            card = item.get("note_card", {})
            if not card:
                continue
            note = NoteItem(
                note_id=item.get("id", ""),
                title=card.get("title", ""),
                desc=card.get("desc", ""),
                author_id=card.get("user", {}).get("user_id", ""),
                author_name=card.get("user", {}).get("nickname", ""),
                liked_count=card.get("interact_info", {}).get("liked_count", 0),
                collected_count=card.get("interact_info", {}).get("collected_count", 0),
                comment_count=card.get("interact_info", {}).get("comment_count", 0),
                cover_url=card.get("cover", {}).get("url", ""),
                note_type=card.get("type", "normal"),
                topics=[t.get("name", "") for t in card.get("tag_list", [])],
            )
            result.append(note)
        return result

    def _parse_note_detail(self, data: dict) -> list[NoteItem]:
        """解析帖子详情"""
        detail_map = data.get("data", {}).get("note_detail_map", {})
        return [self._parse_note_list({"data": {"items": [{"id": k, "note_card": v}]}})
                for k, v in detail_map.items()]

    def _parse_comments(self, data: dict) -> list[CommentItem]:
        comments = data.get("data", {}).get("comments", [])
        result = []
        for c in comments:
            comment = CommentItem(
                comment_id=c.get("id", ""),
                note_id=c.get("note_id", ""),
                content=c.get("content", ""),
                author_id=c.get("user_info", {}).get("user_id", ""),
                author_name=c.get("user_info", {}).get("nickname", ""),
                liked_count=c.get("like_count", 0),
                create_time=c.get("create_time", 0),
                parent_comment_id=c.get("target_comment", {}).get("id"),
            )
            result.append(comment)
        return result
```

---

## 数据存储格式

### SQLite 表结构

```sql
-- 笔记表
CREATE TABLE IF NOT EXISTS notes (
    note_id TEXT PRIMARY KEY,
    title TEXT,
    desc TEXT,
    author_id TEXT,
    author_name TEXT,
    liked_count INTEGER DEFAULT 0,
    collected_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    cover_url TEXT,
    note_type TEXT,
    topics TEXT,              -- JSON 数组序列化
    crawled_at TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 评论表
CREATE TABLE IF NOT EXISTS comments (
    comment_id TEXT PRIMARY KEY,
    note_id TEXT,
    content TEXT,
    author_id TEXT,
    author_name TEXT,
    liked_count INTEGER DEFAULT 0,
    create_time INTEGER,
    parent_comment_id TEXT,
    crawled_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (note_id) REFERENCES notes(note_id)
);

-- 抓取任务记录表
CREATE TABLE IF NOT EXISTS crawl_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT,
    status TEXT DEFAULT 'pending',   -- pending / running / done / failed
    total_notes INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    finished_at TEXT
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_notes_author ON notes(author_id);
CREATE INDEX IF NOT EXISTS idx_comments_note ON comments(note_id);
```

### JSON Lines 原始格式

每行一个 JSON 对象，保留完整原始响应：

```jsonl
{"ts": "2024-01-15T10:30:00", "path": "/api/sns/v10/search/notes", "data": {...}}
{"ts": "2024-01-15T10:30:05", "path": "/api/sns/v2/note/comments", "data": {...}}
```

---

## 启动脚本

### scripts/start_proxy.sh

```bash
#!/bin/bash
# 启动 mitmproxy（USB Tunnel 模式）

PROXY_PORT=8080

cleanup() {
    echo "正在清除代理设置..."
    adb shell su -c "settings put global http_proxy :0"
    adb shell su -c "settings delete global http_proxy"
    adb shell su -c "settings delete global global_http_proxy_host"
    adb shell su -c "settings delete global global_http_proxy_port"
    adb shell su -c "settings delete global global_http_proxy_exclusion_list"
    adb reverse --remove-all
    echo "代理已清除"
}
trap cleanup EXIT

# 1. 建立 USB 端口转发
adb reverse tcp:$PROXY_PORT tcp:$PROXY_PORT

# 2. 设置手机代理
adb shell su -c "settings put global http_proxy 127.0.0.1:$PROXY_PORT"

echo "代理已启动 (USB Tunnel → 127.0.0.1:$PROXY_PORT)"
echo "Ctrl+C 退出时会自动清除代理"

# 3. 启动 mitmdump
XHS_DB_PATH="data/xiaohongshu.db" mitmdump -p $PROXY_PORT -s src/proxy/addon.py
```
