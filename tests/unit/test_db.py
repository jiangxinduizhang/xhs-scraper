"""
Database 单元测试 - 使用临时 SQLite 文件，无设备依赖
"""
import pytest
import tempfile
import os
import json
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


def make_note(note_id="test_001", liked=100, note_type="normal"):
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
        topics=["测试", "单元测试"],
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
        db.save([make_note("field_test", liked=999)])
        row = db.conn.execute("SELECT * FROM notes WHERE note_id='field_test'").fetchone()
        assert row["title"] == "测试笔记 field_test"
        assert row["liked_count"] == 999
        assert row["author_name"] == "测试用户"
        assert row["note_type"] == "normal"

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
        db.save([make_note("note_001"), make_note("note_002")])
        db.save([make_comment(note_id="note_001")])  # 只有 note_001 有评论
        uncrawled = db.get_uncrawled_notes("穿搭", limit=10)
        assert "note_002" in uncrawled
        assert "note_001" not in uncrawled

    def test_limit_respected(self, db):
        db.save([make_note(f"note_{i}") for i in range(10)])
        uncrawled = db.get_uncrawled_notes("穿搭", limit=3)
        assert len(uncrawled) <= 3

    def test_empty_when_all_have_comments(self, db):
        db.save([make_note("note_001")])
        db.save([make_comment(note_id="note_001")])
        uncrawled = db.get_uncrawled_notes("穿搭", limit=10)
        assert uncrawled == []

    def test_returns_empty_when_no_notes(self, db):
        uncrawled = db.get_uncrawled_notes("穿搭", limit=10)
        assert uncrawled == []
