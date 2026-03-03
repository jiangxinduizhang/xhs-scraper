"""
任务调度主控
协调 uiautomator2（UI 控制）和 mitmproxy（数据采集）完成抓取任务
"""
from __future__ import annotations

import random
import time
import logging

from src import config
from src.controller.actions import XHSActions
from src.controller.device import connect_device, launch_app
from src.controller.state import navigate_to_home
from src.storage.db import Database

log = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, keywords: list[str], db_path: str = "data/xiaohongshu.db"):
        self.keywords = keywords
        self.db = Database(db_path)
        self.daily_count = 0
        self._device = None
        self._actions = None

    @property
    def device(self):
        """懒加载：首次访问时连接设备"""
        if self._device is None:
            self._device = connect_device(config.DEVICE_SERIAL)
        return self._device

    @property
    def actions(self) -> XHSActions:
        if self._actions is None:
            self._actions = XHSActions(self.device)
        return self._actions

    # ─── 主运行循环 ──────────────────────────────────────────

    def run(self, daily_limit: int = None):
        """启动抓取，依次处理所有关键词"""
        limit = daily_limit or config.DAILY_NOTE_LIMIT
        launch_app(self.device, fresh_start=True)
        time.sleep(2)

        for keyword in self.keywords:
            if self.daily_count >= limit:
                log.info(f"已达每日上限 {limit}，停止")
                break

            try:
                self._run_keyword(keyword)
            except Exception as e:
                log.error(f"关键词 [{keyword}] 异常: {e}", exc_info=True)
                self._recover()

            delay = random.uniform(*config.INTER_KEYWORD_DELAY)
            log.info(f"等待 {delay:.0f}s 后处理下一个关键词...")
            time.sleep(delay)

    # ─── 关键词任务 ──────────────────────────────────────────

    def _run_keyword(self, keyword: str):
        log.info(f"开始抓取: {keyword}")
        task_id = self.db.create_task(keyword)

        navigate_to_home(self.device)
        self.actions.search_keyword(keyword)
        time.sleep(2)

        # 滚动列表，mitmproxy 在后台自动拦截 API 响应并写入 DB
        scroll_count = random.randint(*config.NOTES_PER_KEYWORD) // 4
        self.actions.scroll_feed(count=scroll_count)
        time.sleep(3)  # 给 mitmproxy 写入缓冲时间

        target = random.randint(*config.NOTES_PER_KEYWORD)
        note_ids = self.db.get_uncrawled_notes(keyword, limit=target)

        for note_id in note_ids:
            if self.daily_count >= config.DAILY_NOTE_LIMIT:
                break
            try:
                self._crawl_note(note_id)
                self.daily_count += 1
                log.debug(f"完成笔记: {note_id} (今日: {self.daily_count})")
            except Exception as e:
                log.warning(f"笔记 {note_id} 失败: {e}")

        self.db.finish_task(task_id, total_notes=len(note_ids))
        log.info(f"完成: {keyword}，采集 {len(note_ids)} 条")

    def _crawl_note(self, note_id: str):
        """进入笔记详情，采集评论后返回列表"""
        note_card = self.device(resourceId=f"com.xingin.xhs:id/note_{note_id}")
        if not note_card.exists(timeout=2):
            log.debug(f"笔记卡片未找到: {note_id}")
            return

        self.actions.tap_element(note_card)
        self.actions.wait_for_page_load()

        # 模拟阅读停留
        time.sleep(random.uniform(3.0, 8.0))

        # 打开评论并滚动采集
        if self.actions.open_comments():
            count = random.randint(*config.COMMENTS_SCROLL_RANGE)
            self.actions.scroll_comments(count)
            self.actions.tap_back()  # 关闭评论

        self.actions.tap_back()  # 返回列表

    # ─── 异常恢复 ────────────────────────────────────────────

    def _recover(self):
        """异常后尝试恢复到首页"""
        log.info("尝试恢复到首页...")
        try:
            navigate_to_home(self.device)
        except Exception:
            try:
                launch_app(self.device, fresh_start=True)
                time.sleep(3)
            except Exception as e:
                log.error(f"恢复失败: {e}")


# ─── CLI 入口 ────────────────────────────────────────────────

def main():
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    parser = argparse.ArgumentParser(description="小红书数据采集")
    parser.add_argument("keywords", nargs="+", help="搜索关键词列表")
    parser.add_argument("--limit", type=int, default=config.DAILY_NOTE_LIMIT, help="每日笔记上限")
    parser.add_argument("--db", default="data/xiaohongshu.db", help="数据库路径")
    args = parser.parse_args()

    orc = Orchestrator(args.keywords, db_path=args.db)
    orc.run(daily_limit=args.limit)


if __name__ == "__main__":
    main()
