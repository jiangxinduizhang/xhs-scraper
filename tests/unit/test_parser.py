"""
Parser 单元测试 - 无设备依赖，纯 Python
"""
import json
import pytest
from pathlib import Path
from src.proxy.parser import XHSParser, NoteItem, CommentItem, _parse_count

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def search_response():
    return json.loads((FIXTURES / "search_notes_response.json").read_text())


@pytest.fixture
def comments_response():
    return json.loads((FIXTURES / "comments_response.json").read_text())


# ─── _parse_count ────────────────────────────────────────────

class TestParseCount:
    def test_int_passthrough(self):
        assert _parse_count(1000) == 1000

    def test_string_integer(self):
        assert _parse_count("234") == 234

    def test_wan_format(self):
        assert _parse_count("1.2万") == 12000

    def test_wan_format_large(self):
        assert _parse_count("23万") == 230000

    def test_comma_format(self):
        assert _parse_count("1,234") == 1234

    def test_zero(self):
        assert _parse_count(0) == 0

    def test_invalid_string(self):
        assert _parse_count("N/A") == 0

    def test_none_like(self):
        assert _parse_count(None) == 0


# ─── NoteItem 解析（搜索）────────────────────────────────────

class TestParseSearchNotes:
    def test_returns_note_items(self, search_response):
        parser = XHSParser()
        notes = parser.parse("/api/sns/v10/search/notes", search_response)
        assert all(isinstance(n, NoteItem) for n in notes)

    def test_skips_empty_id(self, search_response):
        """fixture 中有一条 id='' 的条目，应被跳过"""
        parser = XHSParser()
        notes = parser.parse("/api/sns/v10/search/notes", search_response)
        assert len(notes) == 3
        assert all(n.note_id for n in notes)

    def test_note_fields_populated(self, search_response):
        parser = XHSParser()
        note = parser.parse("/api/sns/v10/search/notes", search_response)[0]
        assert note.note_id == "6571234567890abcde1"
        assert note.title == "今日穿搭分享｜小个子也能穿出高级感"
        assert note.author_id == "user_abc001"
        assert note.author_name == "时尚小达人"
        assert note.liked_count == 23000
        assert note.note_type == "normal"
        assert note.timestamp == 1765585947

    def test_wan_count_parsed(self, search_response):
        """第二条笔记 liked_count 是 '1.2万' 字符串"""
        parser = XHSParser()
        notes = parser.parse("/api/sns/v10/search/notes", search_response)
        assert notes[1].liked_count == 12000

    def test_topics_list(self, search_response):
        parser = XHSParser()
        notes = parser.parse("/api/sns/v10/search/notes", search_response)
        assert notes[0].topics == ["穿搭", "小个子穿搭", "日常穿搭"]

    def test_video_type(self, search_response):
        parser = XHSParser()
        notes = parser.parse("/api/sns/v10/search/notes", search_response)
        assert notes[2].note_type == "video"

    def test_skips_non_note_model_type(self):
        """model_type != 'note' 的条目应跳过"""
        parser = XHSParser()
        data = {"data": {"items": [
            {"model_type": "ad", "note": {"id": "ad_001", "title": "广告"}},
            {"model_type": "note", "note": {
                "id": "note_001", "title": "笔记", "desc": "",
                "liked_count": 10, "collected_count": 5, "comments_count": 1,
                "type": "normal",
                "user": {"userid": "u1", "nickname": "用户"},
                "images_list": [], "tag_list": []
            }}
        ]}}
        notes = parser.parse("/api/sns/v10/search/notes", data)
        assert len(notes) == 1
        assert notes[0].note_id == "note_001"

    def test_empty_items(self):
        parser = XHSParser()
        result = parser.parse("/api/sns/v10/search/notes", {"data": {"items": []}})
        assert result == []

    def test_unknown_path_returns_empty(self):
        parser = XHSParser()
        result = parser.parse("/api/sns/v1/unknown/endpoint", {"data": {}})
        assert result == []


# ─── NoteItem 解析（首页 Feed）────────────────────────────────

class TestParseHomefeed:
    def test_parses_flat_list(self):
        """homefeed: data.data 是笔记列表（平铺）"""
        parser = XHSParser()
        data = {"data": [
            {
                "id": "hf_001", "title": "推荐内容", "desc": "desc",
                "likes": 500, "type": "normal",
                "timestamp": 1772289878,
                "user": {"userid": "u1", "nickname": "用户1"},
                "images_list": [{"url": "https://example.com/img.jpg"}],
                "is_ads": False
            }
        ]}
        notes = parser.parse("/api/sns/v6/homefeed", data)
        assert len(notes) == 1
        assert notes[0].note_id == "hf_001"
        assert notes[0].liked_count == 500
        assert notes[0].cover_url == "https://example.com/img.jpg"
        assert notes[0].author_id == "u1"
        assert notes[0].timestamp == 1772289878

    def test_timestamp_defaults_to_zero(self):
        """homefeed item 没有 timestamp 字段时，默认为 0"""
        parser = XHSParser()
        data = {"data": [
            {
                "id": "hf_no_ts", "title": "无时间戳", "desc": "",
                "likes": 0, "type": "normal",
                "user": {"userid": "u1", "nickname": "用户1"},
                "images_list": []
            }
        ]}
        notes = parser.parse("/api/sns/v6/homefeed", data)
        assert notes[0].timestamp == 0

    def test_skips_ads(self):
        """is_ads=True 的条目应跳过"""
        parser = XHSParser()
        data = {"data": [
            {"id": "ad_001", "is_ads": True, "type": "normal",
             "user": {}, "images_list": [], "title": "广告", "desc": ""},
            {"id": "note_001", "is_ads": False, "type": "normal", "likes": 10,
             "user": {"userid": "u1", "nickname": "用户"},
             "images_list": [], "title": "笔记", "desc": ""}
        ]}
        notes = parser.parse("/api/sns/v6/homefeed", data)
        assert len(notes) == 1
        assert notes[0].note_id == "note_001"

    def test_categories_path_ignored(self):
        """homefeed/categories 不应解析为笔记"""
        parser = XHSParser()
        result = parser.parse("/api/sns/v6/homefeed/categories", {"data": []})
        assert result == []

    def test_uses_name_fallback(self):
        """title 为空时使用 name 字段"""
        parser = XHSParser()
        data = {"data": [
            {"id": "hf_002", "name": "名称字段", "title": None, "desc": "",
             "likes": 0, "type": "normal",
             "user": {"userid": "u2", "nickname": "用户2"},
             "images_list": []}
        ]}
        notes = parser.parse("/api/sns/v6/homefeed", data)
        assert notes[0].title == "名称字段"


# ─── NoteDetail 解析 ─────────────────────────────────────────

class TestParseNoteDetail:
    def test_parses_detail_map(self):
        parser = XHSParser()
        data = {"data": {"note_detail_map": {
            "detail_note_001": {
                "title": "详情帖子", "desc": "内容",
                "user": {"user_id": "u1", "nickname": "用户"},
                "interact_info": {"liked_count": 500, "collected_count": 200, "comment_count": 30},
                "cover": {"url": "https://example.com/img.jpg"},
                "type": "normal", "tag_list": [{"name": "测试"}],
                "timestamp": 1770000000
            }
        }}}
        notes = parser.parse("/api/sns/v1/note/detailfeed", data)
        assert len(notes) == 1
        assert notes[0].note_id == "detail_note_001"
        assert notes[0].topics == ["测试"]
        assert notes[0].timestamp == 1770000000

    def test_preload_path_ignored(self):
        """detailfeed/preload 不应解析"""
        parser = XHSParser()
        result = parser.parse("/api/sns/v1/note/detailfeed/preload", {"data": None})
        assert result == []


# ─── CommentItem 解析 ─────────────────────────────────────────

class TestParseComments:
    def test_returns_comment_items(self, comments_response):
        parser = XHSParser()
        comments = parser.parse("/api/sns/v5/note/comment/list", comments_response)
        assert all(isinstance(c, CommentItem) for c in comments)

    def test_skips_empty_id(self, comments_response):
        """fixture 中有一条 id='' 的评论，应被跳过"""
        parser = XHSParser()
        comments = parser.parse("/api/sns/v5/note/comment/list", comments_response)
        assert len(comments) == 3

    def test_comment_fields(self, comments_response):
        parser = XHSParser()
        comment = parser.parse("/api/sns/v5/note/comment/list", comments_response)[0]
        assert comment.comment_id == "comment_001"
        assert comment.note_id == "6571234567890abcde1"
        assert comment.content == "好好看啊，请问是哪个品牌的？"
        assert comment.liked_count == 45

    def test_reply_has_parent_id(self, comments_response):
        """comment_003 是对 comment_001 的回复"""
        parser = XHSParser()
        comments = parser.parse("/api/sns/v5/note/comment/list", comments_response)
        reply = next(c for c in comments if c.comment_id == "comment_003")
        assert reply.parent_comment_id == "comment_001"

    def test_top_comment_has_no_parent(self, comments_response):
        parser = XHSParser()
        comments = parser.parse("/api/sns/v5/note/comment/list", comments_response)
        top = next(c for c in comments if c.comment_id == "comment_001")
        assert top.parent_comment_id is None

    def test_sub_comments_path(self, comments_response):
        """comment/sub 路径也应走评论解析"""
        parser = XHSParser()
        comments = parser.parse("/api/sns/v5/note/comment/sub", comments_response)
        assert len(comments) == 3

    def test_v5_user_field(self):
        """v5 格式用 user 字段（而非 user_info），time 字段（而非 create_time）"""
        parser = XHSParser()
        data = {"data": {"comments": [{
            "id": "cmt_v5", "content": "v5评论",
            "note_id": "note_v5",
            "user": {"userid": "uid_v5", "nickname": "v5用户"},
            "like_count": 10,
            "time": 1766446738,
            "target_comment": None
        }]}}
        comments = parser.parse("/api/sns/v5/note/comment/list", data)
        assert len(comments) == 1
        assert comments[0].author_id == "uid_v5"
        assert comments[0].author_name == "v5用户"
        assert comments[0].create_time == 1766446738
        assert comments[0].note_id == "note_v5"


class TestParseKaipanlaIndex:
    def test_parses_msgtop_and_tcop_items(self):
        parser = XHSParser()
        data = {
            "MsgTop": {
                "List": [
                    {
                        "ID": "40627",
                        "Title": "涨价榜",
                        "ZhaiYao": "解读机会",
                        "AID": "180",
                        "Account": "财联社",
                        "Like": 0,
                        "CreateTime": "1774944155",
                        "img": {"List": ["https://example.com/a.jpg"], "Type": 3},
                        "Stock": [["801649", "两轮车", "1.63"]],
                    }
                ]
            },
            "TCop": {
                "List": [
                    {
                        "CID": 7608,
                        "Title": "力箭二号",
                        "Source": "开盘啦",
                        "Kword": "中科宇航",
                        "TimeStamp": 1774881241,
                        "Stocks": [{"Code": "002361", "Name": "神剑股份", "Rate": 10}],
                    }
                ]
            },
        }

        items = parser.parse("/w1/api/index.php", data)

        assert len(items) == 2
        assert items[0].note_id == "msgtop:40627"
        assert items[0].title == "涨价榜"
        assert items[0].author_name == "财联社"
        assert items[0].cover_url == "https://example.com/a.jpg"
        assert items[0].topics == ["两轮车"]

        assert items[1].note_id == "tcop:7608"
        assert items[1].title == "力箭二号"
        assert items[1].author_name == "开盘啦"
        assert items[1].comment_count == 1
        assert items[1].topics == ["神剑股份"]


class TestParseKaipanlaMarketSentiment:
    def test_parses_market_sentiment_sections(self):
        parser = XHSParser()
        data = {
            "DaBanList": {
                "ZHQD": 35,
                "tZhangTing": 53,
                "tDieTing": 1,
                "tFengBan": 75.7143,
                "lZhangTing": 62,
            },
            "CWeatherVaneList": {
                "SZ": [["000720", "新能泰山", 10.08, "电气设备"]],
                "XD": [["002310", "东方新能", -10, "风电"]],
            },
            "BaceFaceList": [["两轮车", "1.63", 801649]],
            "FKYDSixList": [{"StockID": "601012", "StockName": "隆基绿能", "zhangfu": "-2.34%"}],
            "PHBList": [["002361", "神剑股份", 10, 0, "4连板", "商业航天", "商业航天;2|4连板;1"]],
            "JJXTList": [["000592", "平潭发展", 3.79, 214172478, "海峡两岸"]],
            "ZQFKList": [["601138", "工业富联", 5340, 4.44, "海峡两岸、机器人概念、年报增长"]],
            "ZDJKList": [{"StockID": "605255", "StockName": "天普股份"}],
            "PLZList": [["000890", "法尔胜", 1, "连续30个交易日内涨幅偏离值累计达到 200%", 0, 28, 191.14, "涨幅达到3.11%将触发严重异动", 3.11, 191.14, "0000-00-00", 15.91, "未达到严重异动条件"]],
            "ZLSCList": [["002594", "比亚迪", "801199", "汽车零部件", 105.25, -0.75, 1719883800, "趋势锁仓", -56.86, "新能源汽车龙头：6月新能源汽车销量341658辆，去年同期253046辆。", 0]],
        }

        items = parser.parse("/w1/api/index.php", data)

        assert len(items) == 11
        assert items[0].note_id == "market:summary:unknown"
        assert items[0].note_type == "market_emotion_summary"
        assert items[0].title == "市场情绪总览"
        assert items[0].source == "market_sentiment"
        assert items[0].desc == "综合强度35，涨停53，跌停1，炸板率75.7143，连板率62"
        assert any(item.note_id == "market:weather:SZ:unknown" for item in items)
        assert any(item.note_id == "market:weather:XD:unknown" for item in items)
        assert any(item.note_id == "market:baceface:801649" and item.title == "两轮车" for item in items)

        assert any(item.note_id == "market:phb:002361" for item in items)
        assert any(item.note_id == "market:jjxt:000592" for item in items)
        assert any(item.note_id == "market:zqfk:601138" for item in items)
        assert any(item.note_id == "market:plz:000890" for item in items)
        assert any(item.note_id == "market:zlsc:002594" for item in items)
        assert any(item.note_id == "market:zdjk:605255" for item in items)
