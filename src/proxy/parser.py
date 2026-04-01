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
    timestamp: int = 0
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
        if "/w1/api/index.php" in path:
            if isinstance(data, dict) and "BaceFaceList" in data:
                return self._parse_market_sentiment(data)
            return self._parse_index_feed(data)
        if "search/notes" in path:
            return self._parse_search_notes(data)
        elif "homefeed" in path and "categories" not in path:
            return self._parse_homefeed(data)
        elif "detailfeed" in path and "preload" not in path:
            return self._parse_note_detail(data)
        elif "comment" in path:
            return self._parse_comments(data)
        return []

    def _get_user_info(self, obj: dict) -> tuple[str, str]:
        """统一提取作者 ID 和昵称"""
        # 有时是 user，有时是 user_info
        user = obj.get("user") or obj.get("user_info") or {}
        # 有时是 userid，有时是 user_id
        author_id = user.get("userid") or user.get("user_id") or ""
        author_name = user.get("nickname") or user.get("name") or ""
        return author_id, author_name

    @staticmethod
    def _first_image_url(obj: dict) -> str:
        """从多种图片字段里提取第一张封面图。"""
        for key in ("images_list", "imgList", "img", "image", "cover"):
            value = obj.get(key)
            if isinstance(value, dict):
                items = value.get("List") or value.get("list") or []
                if items:
                    return items[0] or ""
                url = value.get("url") or value.get("ImageUrl") or value.get("imageUrl")
                if url:
                    return url
            elif isinstance(value, list) and value:
                first = value[0]
                if isinstance(first, dict):
                    url = first.get("url") or first.get("ImageUrl") or first.get("imageUrl")
                    if url:
                        return url
                elif isinstance(first, str):
                    return first
        return ""

    def _parse_index_feed(self, data: dict) -> list:
        """开盘啦首页响应：优先抽取 MsgTop / TCop 作为结构化记录。"""
        result = []

        msg_top = (data.get("MsgTop") or {}).get("List", [])
        for item in msg_top:
            note_id = item.get("ID") or item.get("Cid") or ""
            if not note_id:
                continue
            author_id = str(item.get("AID") or item.get("CID") or "")
            author_name = item.get("Account") or item.get("Source") or ""
            topics = []
            for stock in item.get("Stock", []) or []:
                if isinstance(stock, (list, tuple)) and len(stock) >= 2 and stock[1]:
                    topics.append(str(stock[1]))
            result.append(NoteItem(
                note_id=f"msgtop:{note_id}",
                title=item.get("Title", ""),
                desc=item.get("ZhaiYao", "") or item.get("Title", ""),
                author_id=author_id,
                author_name=author_name,
                liked_count=_parse_count(item.get("Like", 0)),
                collected_count=0,
                comment_count=0,
                cover_url=self._first_image_url(item),
                note_type="msg_top",
                timestamp=_parse_count(item.get("CreateTime", 0)),
                topics=topics,
            ))

        tcop = (data.get("TCop") or {}).get("List", [])
        for item in tcop:
            note_id = item.get("CID") or item.get("ID") or ""
            if not note_id:
                continue
            topics = []
            for stock in item.get("Stocks", []) or []:
                if isinstance(stock, dict) and stock.get("Name"):
                    topics.append(str(stock["Name"]))
            result.append(NoteItem(
                note_id=f"tcop:{note_id}",
                title=item.get("Title", ""),
                desc=item.get("Kword", "") or item.get("Title", ""),
                author_id=str(item.get("CID") or ""),
                author_name=item.get("Source") or "",
                liked_count=0,
                collected_count=0,
                comment_count=len(item.get("Stocks", []) or []),
                cover_url=self._first_image_url(item),
                note_type="tcop",
                timestamp=_parse_count(item.get("TimeStamp", 0)),
                topics=topics,
            ))

        return result

    def _parse_market_sentiment(self, data: dict) -> list:
        """开盘啦市场情绪页：抽取题材、风向、连板、龙虎榜等聚合块。"""
        result = []

        def _join_items(items: list, limit: int = 3) -> str:
            parts: list[str] = []
            for item in items[:limit]:
                if isinstance(item, list):
                    parts.append(" ".join(str(x) for x in item if x not in ("", None)))
                elif isinstance(item, dict):
                    parts.append(" ".join(str(v) for v in item.values() if v not in ("", None)))
                else:
                    parts.append(str(item))
            return " | ".join(parts)

        da_ban = data.get("DaBanList")
        if isinstance(da_ban, dict) and da_ban:
            result.append(NoteItem(
                note_id=f"market:summary:{data.get('Day', '') or 'unknown'}",
                title="市场情绪总览",
                desc=(
                    f"综合强度{da_ban.get('ZHQD', '')}，"
                    f"涨停{da_ban.get('tZhangTing', '')}，"
                    f"跌停{da_ban.get('tDieTing', '')}，"
                    f"炸板率{da_ban.get('tFengBan', '')}，"
                    f"连板率{da_ban.get('lZhangTing', '')}"
                ),
                author_id="DaBanList",
                author_name="开盘啦",
                liked_count=_parse_count(da_ban.get("ZHQD", 0)),
                collected_count=_parse_count(da_ban.get("tZhangTing", 0)),
                comment_count=_parse_count(da_ban.get("tDieTing", 0)),
                cover_url="",
                note_type="market_emotion_summary",
                timestamp=_parse_count(data.get("Time", 0)),
                topics=["市场情绪"],
                source="market_sentiment",
            ))

        weather = data.get("CWeatherVaneList")
        if isinstance(weather, dict) and weather:
            for side, items in weather.items():
                if not isinstance(items, list) or not items:
                    continue
                result.append(NoteItem(
                    note_id=f"market:weather:{side}:{data.get('Day', '') or 'unknown'}",
                    title=f"{side} 风向标",
                    desc=_join_items(items, limit=3),
                    author_id=f"CWeatherVaneList:{side}",
                    author_name="开盘啦",
                    liked_count=len(items),
                    collected_count=0,
                    comment_count=0,
                    cover_url="",
                    note_type=f"market_weather_{side.lower()}",
                    timestamp=_parse_count(data.get("Time", 0)),
                    topics=[side],
                    source="market_sentiment",
                ))

        for rank, item in enumerate(data.get("BaceFaceList", []) or [], start=1):
            if not isinstance(item, list) or len(item) < 3:
                continue
            name, rate, stock_id = item[0], item[1], item[2]
            result.append(NoteItem(
                note_id=f"market:baceface:{stock_id}",
                title=str(name),
                desc=f"题材涨幅: {rate}",
                author_id=str(stock_id),
                author_name="BaceFaceList",
                liked_count=0,
                collected_count=0,
                comment_count=rank,
                cover_url="",
                note_type="market_baceface",
                timestamp=0,
                topics=[str(name)],
                source="market_sentiment",
            ))

        for item in data.get("FKYDSixList", []) or []:
            if not isinstance(item, dict):
                continue
            stock_id = item.get("StockID", "")
            if not stock_id:
                continue
            result.append(NoteItem(
                note_id=f"market:fkyd:{stock_id}",
                title=item.get("StockName", ""),
                desc=f"涨幅: {item.get('zhangfu', '')}",
                author_id=stock_id,
                author_name="FKYDSixList",
                liked_count=0,
                collected_count=0,
                comment_count=0,
                cover_url="",
                note_type="market_fkyd",
                timestamp=0,
                topics=[item.get("StockName", "")] if item.get("StockName") else [],
                source="market_sentiment",
            ))

        for item in data.get("PHBList", []) or []:
            if not isinstance(item, list) or len(item) < 7:
                continue
            stock_id, stock_name, increase, board_count, reason, topic, tags = item[:7]
            result.append(NoteItem(
                note_id=f"market:phb:{stock_id}",
                title=str(stock_name),
                desc=f"{reason} | {topic}",
                author_id=str(stock_id),
                author_name="PHBList",
                liked_count=_parse_count(increase),
                collected_count=board_count if isinstance(board_count, int) else _parse_count(board_count),
                comment_count=0,
                cover_url="",
                note_type="market_phb",
                timestamp=0,
                topics=[str(topic)] if topic else [],
                source="market_sentiment",
            ))

        for item in data.get("JJXTList", []) or []:
            if not isinstance(item, list) or len(item) < 5:
                continue
            stock_id, stock_name, increase, money, topic = item[:5]
            result.append(NoteItem(
                note_id=f"market:jjxt:{stock_id}",
                title=str(stock_name),
                desc=f"金额: {money} | 主题: {topic}",
                author_id=str(stock_id),
                author_name="JJXTList",
                liked_count=_parse_count(increase),
                collected_count=_parse_count(money),
                comment_count=0,
                cover_url="",
                note_type="market_jjxt",
                timestamp=0,
                topics=[str(topic)] if topic else [],
                source="market_sentiment",
            ))

        for item in data.get("ZQFKList", []) or []:
            if not isinstance(item, list) or len(item) < 5:
                continue
            stock_id, stock_name, amount, rate, topic = item[:5]
            result.append(NoteItem(
                note_id=f"market:zqfk:{stock_id}",
                title=str(stock_name),
                desc=f"资金: {amount} | 涨幅: {rate}",
                author_id=str(stock_id),
                author_name="ZQFKList",
                liked_count=_parse_count(rate),
                collected_count=_parse_count(amount),
                comment_count=0,
                cover_url="",
                note_type="market_zqfk",
                timestamp=0,
                topics=[str(topic)] if topic else [],
                source="market_sentiment",
            ))

        for item in data.get("PLZList", []) or []:
            if not isinstance(item, list) or len(item) < 13:
                continue
            stock_id, stock_name = item[0], item[1]
            reason = item[3]
            result.append(NoteItem(
                note_id=f"market:plz:{stock_id}",
                title=str(stock_name),
                desc=str(reason),
                author_id=str(stock_id),
                author_name="PLZList",
                liked_count=0,
                collected_count=0,
                comment_count=0,
                cover_url="",
                note_type="market_plz",
                timestamp=0,
                topics=[str(reason)] if reason else [],
                source="market_sentiment",
            ))

        for item in data.get("ZLSCList", []) or []:
            if not isinstance(item, list) or len(item) < 10:
                continue
            stock_id, stock_name = item[0], item[1]
            theme = item[3]
            result.append(NoteItem(
                note_id=f"market:zlsc:{stock_id}",
                title=str(stock_name),
                desc=f"{theme} | {item[8] if len(item) > 8 else ''}",
                author_id=str(stock_id),
                author_name="ZLSCList",
                liked_count=0,
                collected_count=0,
                comment_count=0,
                cover_url="",
                note_type="market_zlsc",
                timestamp=_parse_count(item[6]) if len(item) > 6 else 0,
                topics=[str(theme)] if theme else [],
                source="market_sentiment",
            ))

        for item in data.get("ZDJKList", []) or []:
            if not isinstance(item, dict):
                continue
            stock_id = item.get("StockID", "")
            if not stock_id:
                continue
            result.append(NoteItem(
                note_id=f"market:zdjk:{stock_id}",
                title=item.get("StockName", ""),
                desc="重点监控",
                author_id=stock_id,
                author_name="ZDJKList",
                liked_count=0,
                collected_count=0,
                comment_count=0,
                cover_url="",
                note_type="market_zdjk",
                timestamp=_parse_count(data.get("Time", 0)),
                topics=[item.get("StockName", "")] if item.get("StockName") else [],
                source="market_sentiment",
            ))

        return result

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
            author_id, author_name = self._get_user_info(note)
            result.append(NoteItem(
                note_id=note_id,
                title=note.get("title", ""),
                desc=note.get("desc", ""),
                author_id=author_id,
                author_name=author_name,
                liked_count=_parse_count(note.get("liked_count", 0)),
                collected_count=_parse_count(note.get("collected_count", 0)),
                comment_count=_parse_count(note.get("comments_count", 0)),
                cover_url=cover,
                note_type=note.get("type", "normal"),
                timestamp=note.get("timestamp", 0),
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
            author_id, author_name = self._get_user_info(item)
            result.append(NoteItem(
                note_id=note_id,
                title=item.get("title") or item.get("name", ""),
                desc=item.get("desc", ""),
                author_id=author_id,
                author_name=author_name,
                liked_count=_parse_count(item.get("likes", 0)),
                collected_count=0,   # homefeed 不提供
                comment_count=0,     # homefeed 不提供
                cover_url=cover,
                note_type=item.get("type", "normal"),
                timestamp=item.get("timestamp", 0),
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
            author_id, author_name = self._get_user_info(card)
            interact = card.get("interact_info", {})
            result.append(NoteItem(
                note_id=note_id,
                title=card.get("title", ""),
                desc=card.get("desc", ""),
                author_id=author_id,
                author_name=author_name,
                liked_count=_parse_count(interact.get("liked_count", 0)),
                collected_count=_parse_count(interact.get("collected_count", 0)),
                comment_count=_parse_count(interact.get("comment_count", 0)),
                cover_url=cover,
                note_type=card.get("type", "normal"),
                timestamp=card.get("timestamp", 0) or card.get("time", 0),
                topics=[t.get("name", "") for t in card.get("tag_list", []) if t.get("name")],
            ))
        return result

    def _parse_comments(self, data: dict) -> list:
        """评论列表（实测 v5: /api/sns/v5/note/comment/list）"""
        comments_data = (data.get("data") or {}).get("comments", [])
        note_id = (data.get("data") or {}).get("note_id", "")
        result = []
        for c in comments_data:
            comment_id = c.get("id", "")
            if not comment_id:
                continue
            author_id, author_name = self._get_user_info(c)
            target = c.get("target_comment") or {}
            comment = CommentItem(
                comment_id=comment_id,
                note_id=c.get("note_id", "") or note_id,
                content=c.get("content", ""),
                author_id=author_id,
                author_name=author_name,
                liked_count=_parse_count(c.get("like_count", 0)),
                create_time=c.get("time") or c.get("create_time", 0),
                parent_comment_id=target.get("id") if target else None,
            )
            result.append(comment)
        return result
