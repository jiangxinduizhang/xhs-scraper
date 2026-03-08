"""
数据导出 CLI

用法：
    python scripts/export_data.py --db data/xiaohongshu.db --format csv --output data/export/
    python scripts/export_data.py --db data/xiaohongshu.db --format json --output data/export/
"""
import argparse
import os
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，使 src 包可被导入
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.db import Database


def main():
    parser = argparse.ArgumentParser(description="小红书数据导出工具")
    parser.add_argument("--db", required=True, help="SQLite 数据库路径，例如 data/xiaohongshu.db")
    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        required=True,
        help="导出格式：csv 或 json",
    )
    parser.add_argument("--output", required=True, help="输出目录，例如 data/export/")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"[错误] 数据库文件不存在：{args.db}", file=sys.stderr)
        sys.exit(1)

    # 自动创建输出目录
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    db = Database(args.db)

    fmt = args.format
    notes_path = str(output_dir / f"notes.{fmt}")
    comments_path = str(output_dir / f"comments.{fmt}")

    if fmt == "csv":
        db.export_notes_csv(notes_path)
        db.export_comments_csv(comments_path)
    else:
        db.export_notes_json(notes_path)
        db.export_comments_json(comments_path)

    db.conn.close()
    print(f"[完成] notes    → {notes_path}")
    print(f"[完成] comments → {comments_path}")


if __name__ == "__main__":
    main()
