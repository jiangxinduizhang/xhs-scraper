"""
小红书 API 响应解析器
将 mitmproxy 拦截的 JSON 数据转换为统一的数据类
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


def _parse_count(value) -> int:
    """解析数量字段，兼容 '2.3万' / '1,234' / int 等格式"""
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        value = value.replace(",", "").strip()
        if "万" in value:
            return int(float(value.replace("万", "")) * 10000)
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


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
    note_type: str                          # normal / video
    topics: list = field(default_factory=list)
    keyword: str = ""
    source: str = ""                        # search / homefeed / detailfeed
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
    crawled_at: str = field(default_factory=lambda: datetime.now().isoformat())


class XHSParser:
    def parse(self, path: str, data: dict) -> list:
        """根据 API 路径分发解析，返回 NoteItem 或 CommentItem 列表"""
        if "search/notes" in path:
            return self._parse_search_notes(data)
        elif "homefeed" in path and "categories" not in path:
            return self._parse_homefeed(data)
        elif "detailfeed" in path and "preload" not in path:
            return self._parse_note_detail(data)
        elif "comments" in path:
            return self._parse_comments(data)
        return []

    def _parse_search_notes(self, data: dict) -> list:
        """search/notes: data.data.items[].note（实测 v10 格式）"""
        items = (data.get("data") or {}).get("items", [])
        result = []
        for item in items:
            if item.get("model_type") != "note":
                continue
            note = item.get("note", {})
            note_id = note.get("id", "")
            if not note_id:
                continue
            imgs = note.get("images_list", [])
            cover = imgs[0].get("url", "") if imgs else ""
            result.append(NoteItem(
                note_id=note_id,
                title=note.get("title", ""),
                desc=note.get("desc", ""),
                author_id=note.get("user", {}).get("userid", ""),
                author_name=note.get("user", {}).get("nickname", ""),
                liked_count=_parse_count(note.get("liked_count", 0)),
                collected_count=_parse_count(note.get("collected_count", 0)),
                comment_count=_parse_count(note.get("comments_count", 0)),
                cover_url=cover,
                note_type=note.get("type", "normal"),
                topics=[t.get("name", "") for t in note.get("tag_list", []) if t.get("name")],
            ))
        return result

    def _parse_homefeed(self, data: dict) -> list:
        """homefeed: data.data 是笔记平铺列表（实测 v6 格式）"""
        items = data.get("data", [])
        if not isinstance(items, list):
            return []
        result = []
        for item in items:
            note_id = item.get("id", "")
            if not note_id or item.get("is_ads"):
                continue
            imgs = item.get("images_list", [])
            cover = imgs[0].get("url", "") if imgs else ""
            result.append(NoteItem(
                note_id=note_id,
                title=item.get("title") or item.get("name", ""),
                desc=item.get("desc", ""),
                author_id=item.get("user", {}).get("userid", ""),
                author_name=item.get("user", {}).get("nickname", ""),
                liked_count=_parse_count(item.get("likes", 0)),
                collected_count=0,   # homefeed 不提供
                comment_count=0,     # homefeed 不提供
                cover_url=cover,
                note_type=item.get("type", "normal"),
            ))
        return result

    def _parse_note_detail(self, data: dict) -> list:
        """帖子详情：data.data.note_detail_map 格式"""
        detail_map = data.get("data", {})
        if isinstance(detail_map, dict):
            detail_map = detail_map.get("note_detail_map", {})
        result = []
        for note_id, card in detail_map.items():
            if not isinstance(card, dict):
                continue
            imgs = card.get("images_list", []) or [card.get("cover", {})]
            cover = ""
            if imgs and isinstance(imgs[0], dict):
                cover = imgs[0].get("url", "")
            user = card.get("user", {})
            interact = card.get("interact_info", {})
            result.append(NoteItem(
                note_id=note_id,
                title=card.get("title", ""),
                desc=card.get("desc", ""),
                author_id=user.get("userid") or user.get("user_id", ""),
                author_name=user.get("nickname", ""),
                liked_count=_parse_count(interact.get("liked_count", 0)),
                collected_count=_parse_count(interact.get("collected_count", 0)),
                comment_count=_parse_count(interact.get("comment_count", 0)),
                cover_url=cover,
                note_type=card.get("type", "normal"),
                topics=[t.get("name", "") for t in card.get("tag_list", []) if t.get("name")],
            ))
        return result

    def _parse_comments(self, data: dict) -> list:
        comments_data = (data.get("data") or {}).get("comments", [])
        note_id = (data.get("data") or {}).get("note_id", "")
        result = []
        for c in comments_data:
            comment_id = c.get("id", "")
            if not comment_id:
                continue
            target = c.get("target_comment") or {}
            comment = CommentItem(
                comment_id=comment_id,
                note_id=note_id or c.get("note_id", ""),
                content=c.get("content", ""),
                author_id=c.get("user_info", {}).get("user_id", ""),
                author_name=c.get("user_info", {}).get("nickname", ""),
                liked_count=_parse_count(c.get("like_count", 0)),
                create_time=c.get("create_time", 0),
                parent_comment_id=target.get("id") if target else None,
            )
            result.append(comment)
        return result
