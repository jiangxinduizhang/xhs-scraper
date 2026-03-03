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
                "type": "normal", "tag_list": [{"name": "测试"}]
            }
        }}}
        notes = parser.parse("/api/sns/v1/note/detailfeed", data)
        assert len(notes) == 1
        assert notes[0].note_id == "detail_note_001"
        assert notes[0].topics == ["测试"]

    def test_preload_path_ignored(self):
        """detailfeed/preload 不应解析"""
        parser = XHSParser()
        result = parser.parse("/api/sns/v1/note/detailfeed/preload", {"data": None})
        assert result == []


# ─── CommentItem 解析 ─────────────────────────────────────────

class TestParseComments:
    def test_returns_comment_items(self, comments_response):
        parser = XHSParser()
        comments = parser.parse("/api/sns/v2/note/comments", comments_response)
        assert all(isinstance(c, CommentItem) for c in comments)

    def test_skips_empty_id(self, comments_response):
        """fixture 中有一条 id='' 的评论，应被跳过"""
        parser = XHSParser()
        comments = parser.parse("/api/sns/v2/note/comments", comments_response)
        assert len(comments) == 3

    def test_comment_fields(self, comments_response):
        parser = XHSParser()
        comment = parser.parse("/api/sns/v2/note/comments", comments_response)[0]
        assert comment.comment_id == "comment_001"
        assert comment.note_id == "6571234567890abcde1"
        assert comment.content == "好好看啊，请问是哪个品牌的？"
        assert comment.liked_count == 45

    def test_reply_has_parent_id(self, comments_response):
        """comment_003 是对 comment_001 的回复"""
        parser = XHSParser()
        comments = parser.parse("/api/sns/v2/note/comments", comments_response)
        reply = next(c for c in comments if c.comment_id == "comment_003")
        assert reply.parent_comment_id == "comment_001"

    def test_top_comment_has_no_parent(self, comments_response):
        parser = XHSParser()
        comments = parser.parse("/api/sns/v2/note/comments", comments_response)
        top = next(c for c in comments if c.comment_id == "comment_001")
        assert top.parent_comment_id is None

    def test_sub_comments_path(self, comments_response):
        """comments/sub 路径也应走评论解析"""
        parser = XHSParser()
        comments = parser.parse("/api/sns/v2/note/comments/sub", comments_response)
        assert len(comments) == 3
