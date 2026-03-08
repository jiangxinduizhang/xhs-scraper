"""
SQLite 数据存储层
"""
import csv
import sqlite3
import json
from datetime import datetime
from pathlib import Path


class Database:
    def __init__(self, path: str = "data/xiaohongshu.db"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
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
                timestamp INTEGER DEFAULT 0,
                topics TEXT,
                crawled_at TEXT,
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS comments (
                comment_id TEXT PRIMARY KEY,
                note_id TEXT,
                content TEXT,
                author_id TEXT,
                author_name TEXT,
                liked_count INTEGER DEFAULT 0,
                create_time INTEGER,
                parent_comment_id TEXT,
                crawled_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS crawl_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT,
                status TEXT DEFAULT 'pending',
                total_notes INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                finished_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_notes_author ON notes(author_id);
            CREATE INDEX IF NOT EXISTS idx_comments_note ON comments(note_id);
        """)
        # 兼容已有数据：增量添加新列
        self._migrate_add_columns()
        self.conn.commit()

    def _migrate_add_columns(self):
        """ALTER TABLE 增量添加新列，已存在则跳过"""
        existing = {
            row[1] for row in
            self.conn.execute("PRAGMA table_info(notes)").fetchall()
        }
        for col, typedef in [
            ("keyword", "TEXT DEFAULT ''"),
            ("source", "TEXT DEFAULT ''"),
            ("timestamp", "INTEGER DEFAULT 0"),
        ]:
            assert col.isidentifier(), f"非法列名: {col}"
            if col not in existing:
                self.conn.execute(f"ALTER TABLE notes ADD COLUMN {col} {typedef}")

    # ─── 任务管理 ────────────────────────────────────────

    def create_task(self, keyword: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO crawl_tasks (keyword, status) VALUES (?, 'running')",
            (keyword,)
        )
        self.conn.commit()
        return cur.lastrowid

    def finish_task(self, task_id: int, total_notes: int):
        self.conn.execute(
            "UPDATE crawl_tasks SET status='done', total_notes=?, finished_at=? WHERE id=?",
            (total_notes, datetime.now().isoformat(), task_id)
        )
        self.conn.commit()

    def get_pending_tasks(self) -> list:
        """获取待执行关键词（将中断的 running 任务重置为 pending）"""
        self.conn.execute(
            "UPDATE crawl_tasks SET status='pending' WHERE status='running'"
        )
        self.conn.commit()
        cur = self.conn.execute(
            "SELECT keyword FROM crawl_tasks WHERE status='pending' ORDER BY id"
        )
        return [row[0] for row in cur.fetchall()]

    def get_uncrawled_notes(self, keyword: str, limit: int = 20) -> list:
        """获取尚未采集评论的笔记 ID（按 keyword 过滤）"""
        cur = self.conn.execute("""
            SELECT note_id FROM notes
            WHERE keyword = ?
              AND note_id NOT IN (SELECT DISTINCT note_id FROM comments)
            LIMIT ?
        """, (keyword, limit))
        return [row[0] for row in cur.fetchall()]

    # ─── 数据存储 ────────────────────────────────────────

    def save(self, items: list, keyword: str = "", source: str = ""):
        """保存 NoteItem 或 CommentItem 列表（使用 duck typing 区分）"""
        for item in items:
            if hasattr(item, 'cover_url'):          # NoteItem
                # 优先使用 item 自带的 keyword/source，其次用参数传入的
                kw = getattr(item, 'keyword', '') or keyword
                src = getattr(item, 'source', '') or source
                self._upsert_note(item, keyword=kw, source=src)
            elif hasattr(item, 'comment_id'):       # CommentItem
                self._upsert_comment(item)
        self.conn.commit()

    def _upsert_note(self, note, keyword: str = "", source: str = ""):
        self.conn.execute("""
            INSERT INTO notes
                (note_id, title, desc, author_id, author_name,
                 liked_count, collected_count, comment_count,
                 cover_url, note_type, timestamp, topics, keyword, source, crawled_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
            ON CONFLICT(note_id) DO UPDATE SET
                title=excluded.title, desc=excluded.desc,
                author_id=excluded.author_id, author_name=excluded.author_name,
                liked_count=excluded.liked_count, collected_count=excluded.collected_count,
                comment_count=excluded.comment_count, cover_url=excluded.cover_url,
                note_type=excluded.note_type, timestamp=excluded.timestamp,
                topics=excluded.topics,
                keyword=excluded.keyword, source=excluded.source,
                updated_at=datetime('now')
        """, (
            note.note_id, note.title, note.desc,
            note.author_id, note.author_name,
            note.liked_count, note.collected_count, note.comment_count,
            note.cover_url, note.note_type,
            getattr(note, 'timestamp', 0),
            json.dumps(note.topics, ensure_ascii=False),
            keyword, source,
            note.crawled_at,
        ))

    def _upsert_comment(self, comment):
        self.conn.execute("""
            INSERT INTO comments
                (comment_id, note_id, content, author_id, author_name,
                 liked_count, create_time, parent_comment_id, crawled_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(comment_id) DO UPDATE SET
                note_id=excluded.note_id,
                content=excluded.content,
                author_id=excluded.author_id,
                author_name=excluded.author_name,
                liked_count=excluded.liked_count,
                create_time=excluded.create_time,
                parent_comment_id=excluded.parent_comment_id
        """, (
            comment.comment_id, comment.note_id, comment.content,
            comment.author_id, comment.author_name,
            comment.liked_count, comment.create_time,
            comment.parent_comment_id,
            comment.crawled_at,
        ))

    # ─── 数据导出 ────────────────────────────────────────

    def _ensure_dir(self, path: str):
        """自动创建目标文件的父目录"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _format_ts(ts) -> str:
        """Unix 时间戳 → 可读时间字符串，0 或无效值返回空串"""
        try:
            ts = int(ts or 0)
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else ""
        except (ValueError, OSError):
            return ""

    def export_notes_csv(self, path: str):
        """导出 notes 表为 CSV，topics 字段展开为逗号分隔字符串"""
        self._ensure_dir(path)
        rows = self.conn.execute("SELECT * FROM notes").fetchall()
        if not rows:
            columns = [desc[1] for desc in self.conn.execute("PRAGMA table_info(notes)").fetchall()]
            columns.append("publish_time")
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
            return
        fieldnames = list(rows[0].keys()) + ["publish_time"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                d = dict(row)
                try:
                    d["topics"] = ",".join(json.loads(d["topics"] or "[]"))
                except (json.JSONDecodeError, TypeError):
                    d["topics"] = d.get("topics") or ""
                d["publish_time"] = self._format_ts(d.get("timestamp"))
                writer.writerow(d)

    def export_notes_json(self, path: str):
        """导出 notes 表为 JSON 数组，topics 保留为数组"""
        self._ensure_dir(path)
        rows = self.conn.execute("SELECT * FROM notes").fetchall()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["topics"] = json.loads(d["topics"] or "[]")
            except (json.JSONDecodeError, TypeError):
                d["topics"] = []
            d["publish_time"] = self._format_ts(d.get("timestamp"))
            result.append(d)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    def export_comments_csv(self, path: str):
        """导出 comments 表为 CSV"""
        self._ensure_dir(path)
        rows = self.conn.execute("SELECT * FROM comments").fetchall()
        if not rows:
            columns = [desc[1] for desc in self.conn.execute("PRAGMA table_info(comments)").fetchall()]
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))

    def export_comments_json(self, path: str):
        """导出 comments 表为 JSON 数组"""
        self._ensure_dir(path)
        rows = self.conn.execute("SELECT * FROM comments").fetchall()
        result = [dict(row) for row in rows]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
