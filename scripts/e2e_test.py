"""
端到端联调测试脚本
逐步验证 orchestrator 的各个环节：
1. 设备连接 + APP 启动
2. 首页滑动 → homefeed 数据抓取
3. 搜索关键词 → search/notes 数据抓取
4. 进入笔记详情 → detailfeed 数据抓取
5. 打开评论 → comments 数据抓取
6. 返回列表
"""
import sys
import os
import time
import logging
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("e2e_test")

DB_PATH = os.getenv("XHS_DB_PATH", "data/test_e2e.db")


def count_db(table: str) -> int:
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute(f"SELECT count(*) FROM {table}")
        n = cur.fetchone()[0]
        conn.close()
        return n
    except Exception:
        return 0


def step(name: str):
    log.info(f"\n{'='*60}")
    log.info(f"  STEP: {name}")
    log.info(f"{'='*60}")


def main():
    from src.controller.device import connect_device, launch_app, preflight_check
    from src.controller.actions import XHSActions
    from src.controller.state import detect_page, PageState, navigate_to_home

    # 代理链路预检
    step("0. 代理预检")
    preflight_check()

    # Step 1: 连接设备
    step("1. 连接设备")
    d = connect_device()
    actions = XHSActions(d)
    log.info(f"屏幕尺寸: {d.window_size()}")

    # Step 2: 启动小红书
    step("2. 启动小红书")
    launch_app(d, fresh_start=True)
    time.sleep(3)
    page = detect_page(d)
    log.info(f"当前页面: {page}")

    # Step 3: 首页滑动，验证 homefeed 抓取
    step("3. 首页滑动 (验证 homefeed)")
    notes_before = count_db("notes")
    log.info(f"数据库笔记数 (before): {notes_before}")

    navigate_to_home(d)
    time.sleep(2)
    actions.scroll_feed(count=3)
    time.sleep(3)

    notes_after = count_db("notes")
    log.info(f"数据库笔记数 (after): {notes_after}")
    log.info(f"新增: {notes_after - notes_before} 条")

    # Step 4: 搜索关键词
    step("4. 搜索关键词 (验证 search/notes)")
    notes_before = count_db("notes")
    actions.search_keyword("咖啡")
    time.sleep(3)

    page = detect_page(d)
    log.info(f"搜索后页面: {page}")

    # 滚动搜索结果
    actions.scroll_feed(count=3)
    time.sleep(3)

    notes_after = count_db("notes")
    log.info(f"搜索后笔记数: {notes_after}, 新增: {notes_after - notes_before}")

    # Step 5: 点击第一个卡片进入详情
    step("5. 进入笔记详情 (验证 detailfeed)")
    if actions.tap_nth_card(0):
        time.sleep(3)
        page = detect_page(d)
        log.info(f"点击卡片后页面: {page}")

        if page in (PageState.NOTE_DETAIL, PageState.COMMENT):
            # Step 6: 打开评论
            step("6. 打开评论 (验证 comments API)")
            comments_before = count_db("comments")

            if page != PageState.COMMENT:
                opened = actions.open_comments()
                log.info(f"评论打开: {opened}")
                time.sleep(2)

            # 滚动评论
            actions.scroll_comments(count=2)
            time.sleep(3)

            comments_after = count_db("comments")
            log.info(f"评论数: {comments_after}, 新增: {comments_after - comments_before}")

            # 返回
            actions.tap_back()  # 关闭评论
            time.sleep(1)

        actions.tap_back()  # 返回列表
        time.sleep(1)
    else:
        log.warning("点击卡片失败！")

    # Step 7: 验证完整 orchestrator 流程（短版本）
    step("7. 验证 orchestrator 短流程")
    page = detect_page(d)
    log.info(f"当前页面: {page}")
    navigate_to_home(d)

    # 汇总
    step("RESULT SUMMARY")
    notes_total = count_db("notes")
    comments_total = count_db("comments")
    log.info(f"总笔记数: {notes_total}")
    log.info(f"总评论数: {comments_total}")

    # 展示部分数据
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT note_id, title, author_name, liked_count, source FROM notes ORDER BY rowid DESC LIMIT 5")
        log.info("最新笔记:")
        for row in cur:
            log.info(f"  [{row['source']}] {row['author_name']} | {row['title'][:30]} | 赞:{row['liked_count']}")

        cur = conn.execute("SELECT comment_id, content, author_name FROM comments LIMIT 5")
        log.info("评论样例:")
        for row in cur:
            log.info(f"  {row['author_name']}: {row['content'][:40]}")
        conn.close()
    except Exception as e:
        log.error(f"查询失败: {e}")

    if notes_total > 0:
        log.info("✅ E2E 测试通过！数据管道正常工作。")
    else:
        log.error("❌ E2E 测试失败：未采集到数据。")

    return notes_total > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
