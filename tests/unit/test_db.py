"""
Database 单元测试 - 使用临时 SQLite 文件，无设备依赖
"""
import csv
import pytest
import tempfile
import os
import json
from pathlib import Path
from src.storage.db import Database
from src.proxy.parser import NoteItem, CommentItem


@pytest.fixture
def db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    database = Database(path)
    yield database
    database.conn.close()
    os.unlink(path)


def make_note(note_id="test_001", liked=100, note_type="normal", keyword="", source="", timestamp=0):
    return NoteItem(
        note_id=note_id,
        title=f"测试笔记 {note_id}",
        desc="这是一条测试笔记内容",
        author_id="author_001",
        author_name="测试用户",
        liked_count=liked,
        collected_count=50,
        comment_count=10,
        cover_url="https://example.com/cover.jpg",
        note_type=note_type,
        timestamp=timestamp,
        topics=["测试", "单元测试"],
        keyword=keyword,
        source=source,
    )


def make_comment(comment_id="cmt_001", note_id="test_001", parent_id=None):
    return CommentItem(
        comment_id=comment_id,
        note_id=note_id,
        content="测试评论内容",
        author_id="commenter_001",
        author_name="评论用户",
        liked_count=5,
        create_time=1705123200000,
        parent_comment_id=parent_id,
    )


# ─── 任务管理 ────────────────────────────────────────────────

class TestCrawlTasks:
    def test_create_task_returns_id(self, db):
        task_id = db.create_task("穿搭")
        assert isinstance(task_id, int)
        assert task_id > 0

    def test_create_task_status_is_running(self, db):
        task_id = db.create_task("美食")
        row = db.conn.execute("SELECT status FROM crawl_tasks WHERE id=?", (task_id,)).fetchone()
        assert row["status"] == "running"

    def test_finish_task_updates_status(self, db):
        task_id = db.create_task("穿搭")
        db.finish_task(task_id, total_notes=15)
        row = db.conn.execute("SELECT status, total_notes FROM crawl_tasks WHERE id=?", (task_id,)).fetchone()
        assert row["status"] == "done"
        assert row["total_notes"] == 15

    def test_get_pending_tasks_empty_when_all_done(self, db):
        task_id = db.create_task("穿搭")
        db.finish_task(task_id, total_notes=5)
        assert db.get_pending_tasks() == []

    def test_get_pending_tasks_resets_interrupted(self, db):
        """中断的 running 任务应被重置为 pending"""
        db.conn.execute("INSERT INTO crawl_tasks (keyword, status) VALUES ('中断任务', 'running')")
        db.conn.commit()
        pending = db.get_pending_tasks()
        assert "中断任务" in pending

    def test_get_pending_tasks_order(self, db):
        """pending 任务按创建顺序返回"""
        db.conn.executemany(
            "INSERT INTO crawl_tasks (keyword, status) VALUES (?, 'pending')",
            [("关键词A",), ("关键词B",), ("关键词C",)]
        )
        db.conn.commit()
        pending = db.get_pending_tasks()
        assert pending == ["关键词A", "关键词B", "关键词C"]


# ─── 笔记存储 ────────────────────────────────────────────────

class TestSaveNotes:
    def test_save_single_note(self, db):
        db.save([make_note()])
        count = db.conn.execute("SELECT count(*) FROM notes").fetchone()[0]
        assert count == 1

    def test_note_fields_saved_correctly(self, db):
        db.save([make_note("field_test", liked=999, timestamp=1765585947)])
        row = db.conn.execute("SELECT * FROM notes WHERE note_id='field_test'").fetchone()
        assert row["title"] == "测试笔记 field_test"
        assert row["liked_count"] == 999
        assert row["author_name"] == "测试用户"
        assert row["note_type"] == "normal"
        assert row["timestamp"] == 1765585947

    def test_timestamp_saved(self, db):
        db.save([make_note("ts_001", timestamp=1772289878)])
        row = db.conn.execute("SELECT timestamp FROM notes WHERE note_id='ts_001'").fetchone()
        assert row["timestamp"] == 1772289878
        # 更新时 timestamp 也应该被覆盖
        db.save([make_note("ts_001", timestamp=1780000000)])
        row = db.conn.execute("SELECT timestamp FROM notes WHERE note_id='ts_001'").fetchone()
        assert row["timestamp"] == 1780000000

    def test_topics_serialized_as_json(self, db):
        db.save([make_note()])
        row = db.conn.execute("SELECT topics FROM notes WHERE note_id='test_001'").fetchone()
        topics = json.loads(row["topics"])
        assert topics == ["测试", "单元测试"]

    def test_upsert_no_duplicate(self, db):
        db.save([make_note()])
        db.save([make_note()])  # 重复插入
        count = db.conn.execute("SELECT count(*) FROM notes").fetchone()[0]
        assert count == 1

    def test_upsert_updates_fields(self, db):
        """重复 note_id 时应更新数据"""
        db.save([make_note(liked=100)])
        db.save([make_note(liked=200)])
        row = db.conn.execute("SELECT liked_count FROM notes WHERE note_id='test_001'").fetchone()
        assert row["liked_count"] == 200

    def test_save_multiple_notes(self, db):
        notes = [make_note(f"note_{i}") for i in range(5)]
        db.save(notes)
        count = db.conn.execute("SELECT count(*) FROM notes").fetchone()[0]
        assert count == 5

    def test_save_mixed_types(self, db):
        """同时保存笔记和评论"""
        db.save([make_note("note_001"), make_comment(note_id="note_001")])
        note_count = db.conn.execute("SELECT count(*) FROM notes").fetchone()[0]
        comment_count = db.conn.execute("SELECT count(*) FROM comments").fetchone()[0]
        assert note_count == 1
        assert comment_count == 1

    def test_keyword_saved(self, db):
        db.save([make_note("kw_001", keyword="穿搭", source="search")])
        row = db.conn.execute("SELECT keyword, source FROM notes WHERE note_id='kw_001'").fetchone()
        assert row["keyword"] == "穿搭"
        assert row["source"] == "search"

    def test_keyword_from_save_param(self, db):
        """save() 的 keyword/source 参数传给没有自带 keyword 的 item"""
        db.save([make_note("kw_002")], keyword="美食", source="homefeed")
        row = db.conn.execute("SELECT keyword, source FROM notes WHERE note_id='kw_002'").fetchone()
        assert row["keyword"] == "美食"
        assert row["source"] == "homefeed"

    def test_item_keyword_overrides_param(self, db):
        """item 自带的 keyword 优先于 save() 参数"""
        db.save([make_note("kw_003", keyword="旅行")], keyword="美食")
        row = db.conn.execute("SELECT keyword FROM notes WHERE note_id='kw_003'").fetchone()
        assert row["keyword"] == "旅行"


# ─── 评论存储 ────────────────────────────────────────────────

class TestSaveComments:
    def test_save_single_comment(self, db):
        db.save([make_comment()])
        count = db.conn.execute("SELECT count(*) FROM comments").fetchone()[0]
        assert count == 1

    def test_comment_fields_saved(self, db):
        db.save([make_comment("cmt_fields", note_id="note_xyz")])
        row = db.conn.execute("SELECT * FROM comments WHERE comment_id='cmt_fields'").fetchone()
        assert row["note_id"] == "note_xyz"
        assert row["content"] == "测试评论内容"
        assert row["liked_count"] == 5

    def test_reply_parent_id_saved(self, db):
        db.save([make_comment("cmt_reply", parent_id="cmt_parent")])
        row = db.conn.execute("SELECT parent_comment_id FROM comments WHERE comment_id='cmt_reply'").fetchone()
        assert row["parent_comment_id"] == "cmt_parent"

    def test_comment_dedup(self, db):
        db.save([make_comment()])
        db.save([make_comment()])
        count = db.conn.execute("SELECT count(*) FROM comments").fetchone()[0]
        assert count == 1


# ─── 待采集笔记查询 ──────────────────────────────────────────

class TestGetUncrawledNotes:
    def test_returns_notes_without_comments(self, db):
        db.save([make_note("note_001", keyword="穿搭"), make_note("note_002", keyword="穿搭")])
        db.save([make_comment(note_id="note_001")])  # 只有 note_001 有评论
        uncrawled = db.get_uncrawled_notes("穿搭", limit=10)
        assert "note_002" in uncrawled
        assert "note_001" not in uncrawled

    def test_limit_respected(self, db):
        db.save([make_note(f"note_{i}", keyword="穿搭") for i in range(10)])
        uncrawled = db.get_uncrawled_notes("穿搭", limit=3)
        assert len(uncrawled) <= 3

    def test_empty_when_all_have_comments(self, db):
        db.save([make_note("note_001", keyword="穿搭")])
        db.save([make_comment(note_id="note_001")])
        uncrawled = db.get_uncrawled_notes("穿搭", limit=10)
        assert uncrawled == []

    def test_returns_empty_when_no_notes(self, db):
        uncrawled = db.get_uncrawled_notes("穿搭", limit=10)
        assert uncrawled == []

    def test_filters_by_keyword(self, db):
        """只返回匹配 keyword 的笔记"""
        db.save([make_note("note_a", keyword="穿搭"), make_note("note_b", keyword="美食")])
        uncrawled = db.get_uncrawled_notes("穿搭", limit=10)
        assert "note_a" in uncrawled
        assert "note_b" not in uncrawled

    def test_different_keyword_returns_different_notes(self, db):
        db.save([make_note("note_a", keyword="穿搭"), make_note("note_b", keyword="美食")])
        assert db.get_uncrawled_notes("穿搭", limit=10) == ["note_a"]
        assert db.get_uncrawled_notes("美食", limit=10) == ["note_b"]


# ─── 数据导出 ─────────────────────────────────────────────────

@pytest.fixture
def tmp_dir():
    """提供临时导出目录，测试结束后自动清理"""
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestExportNotesCsv:
    def test_creates_file(self, db, tmp_dir):
        db.save([make_note()])
        path = os.path.join(tmp_dir, "notes.csv")
        db.export_notes_csv(path)
        assert os.path.exists(path)

    def test_header_row_present(self, db, tmp_dir):
        db.save([make_note()])
        path = os.path.join(tmp_dir, "notes.csv")
        db.export_notes_csv(path)
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assert "note_id" in reader.fieldnames
            assert "title" in reader.fieldnames
            assert "topics" in reader.fieldnames

    def test_row_count(self, db, tmp_dir):
        db.save([make_note("n1"), make_note("n2"), make_note("n3")])
        path = os.path.join(tmp_dir, "notes.csv")
        db.export_notes_csv(path)
        with open(path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 3

    def test_topics_as_comma_separated_string(self, db, tmp_dir):
        """topics 在 CSV 中应为逗号分隔的字符串，而非 JSON"""
        db.save([make_note()])
        path = os.path.join(tmp_dir, "notes.csv")
        db.export_notes_csv(path)
        with open(path, encoding="utf-8") as f:
            row = next(csv.DictReader(f))
        assert row["topics"] == "测试,单元测试"

    def test_empty_table_writes_header_only(self, db, tmp_dir):
        """空表导出只写表头，不报错"""
        path = os.path.join(tmp_dir, "notes.csv")
        db.export_notes_csv(path)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "note_id" in content

    def test_auto_creates_parent_dir(self, db, tmp_dir):
        """自动创建不存在的父目录"""
        path = os.path.join(tmp_dir, "sub", "deep", "notes.csv")
        db.save([make_note()])
        db.export_notes_csv(path)
        assert os.path.exists(path)

    def test_chinese_content_preserved(self, db, tmp_dir):
        """中文字段正常写入和读取"""
        db.save([make_note("cn_001")])
        path = os.path.join(tmp_dir, "notes.csv")
        db.export_notes_csv(path)
        with open(path, encoding="utf-8") as f:
            row = next(csv.DictReader(f))
        assert row["title"] == "测试笔记 cn_001"
        assert row["author_name"] == "测试用户"


class TestExportNotesJson:
    def test_creates_file(self, db, tmp_dir):
        db.save([make_note()])
        path = os.path.join(tmp_dir, "notes.json")
        db.export_notes_json(path)
        assert os.path.exists(path)

    def test_is_valid_json_array(self, db, tmp_dir):
        db.save([make_note("j1"), make_note("j2")])
        path = os.path.join(tmp_dir, "notes.json")
        db.export_notes_json(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_topics_is_list(self, db, tmp_dir):
        """topics 在 JSON 中应为列表，而非字符串"""
        db.save([make_note()])
        path = os.path.join(tmp_dir, "notes.json")
        db.export_notes_json(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data[0]["topics"], list)
        assert data[0]["topics"] == ["测试", "单元测试"]

    def test_empty_table_writes_empty_array(self, db, tmp_dir):
        """空表导出为空 JSON 数组 []"""
        path = os.path.join(tmp_dir, "notes.json")
        db.export_notes_json(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data == []

    def test_chinese_not_escaped(self, db, tmp_dir):
        """ensure_ascii=False：中文直接写入，不转义"""
        db.save([make_note("cn_002")])
        path = os.path.join(tmp_dir, "notes.json")
        db.export_notes_json(path)
        raw = Path(path).read_text(encoding="utf-8")
        assert "测试笔记" in raw
        assert "\\u" not in raw


class TestExportCommentsCsv:
    def test_creates_file(self, db, tmp_dir):
        db.save([make_comment()])
        path = os.path.join(tmp_dir, "comments.csv")
        db.export_comments_csv(path)
        assert os.path.exists(path)

    def test_header_and_row_count(self, db, tmp_dir):
        db.save([make_comment("c1"), make_comment("c2")])
        path = os.path.join(tmp_dir, "comments.csv")
        db.export_comments_csv(path)
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assert "comment_id" in reader.fieldnames
            rows = list(reader)
        assert len(rows) == 2

    def test_empty_table_writes_header_only(self, db, tmp_dir):
        path = os.path.join(tmp_dir, "comments.csv")
        db.export_comments_csv(path)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "comment_id" in content

    def test_content_field_preserved(self, db, tmp_dir):
        db.save([make_comment("c_cn")])
        path = os.path.join(tmp_dir, "comments.csv")
        db.export_comments_csv(path)
        with open(path, encoding="utf-8") as f:
            row = next(csv.DictReader(f))
        assert row["content"] == "测试评论内容"


class TestExportCommentsJson:
    def test_creates_file(self, db, tmp_dir):
        db.save([make_comment()])
        path = os.path.join(tmp_dir, "comments.json")
        db.export_comments_json(path)
        assert os.path.exists(path)

    def test_is_valid_json_array(self, db, tmp_dir):
        db.save([make_comment("j1"), make_comment("j2")])
        path = os.path.join(tmp_dir, "comments.json")
        db.export_comments_json(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_empty_table_writes_empty_array(self, db, tmp_dir):
        path = os.path.join(tmp_dir, "comments.json")
        db.export_comments_json(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data == []

    def test_chinese_not_escaped(self, db, tmp_dir):
        db.save([make_comment("cn_cmt")])
        path = os.path.join(tmp_dir, "comments.json")
        db.export_comments_json(path)
        raw = Path(path).read_text(encoding="utf-8")
        assert "测试评论内容" in raw
        assert "\\u" not in raw

    def test_fields_complete(self, db, tmp_dir):
        """JSON 对象包含所有 comments 表字段"""
        db.save([make_comment("full_c", note_id="note_x", parent_id="parent_c")])
        path = os.path.join(tmp_dir, "comments.json")
        db.export_comments_json(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        obj = data[0]
        assert obj["comment_id"] == "full_c"
        assert obj["note_id"] == "note_x"
        assert obj["parent_comment_id"] == "parent_c"
