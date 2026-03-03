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
        self._limit = daily_limit or config.DAILY_NOTE_LIMIT
        launch_app(self.device, fresh_start=True)
        time.sleep(2)

        for keyword in self.keywords:
            if self.daily_count >= self._limit:
                log.info(f"已达每日上限 {self._limit}，停止")
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

        # 按屏幕位置依次点击可见卡片（不依赖 resourceId）
        # 每次滑动后重置 card_index，因为 tap_nth_card 基于当前可视区域
        target = random.randint(*config.NOTES_PER_KEYWORD)
        crawled = 0
        card_index = 0
        max_rounds = target * 2  # 防止死循环

        for _ in range(max_rounds):
            if crawled >= target or self.daily_count >= self._limit:
                break

            success = self._crawl_visible_card(card_index)
            if success:
                crawled += 1
                self.daily_count += 1
                log.debug(f"完成卡片 #{card_index} (关键词: {keyword}, 今日: {self.daily_count})")

            card_index += 1
            # 每处理完一行（2张卡片）后滚动并重置 index
            if card_index >= 2:
                self.actions.swipe_up()
                time.sleep(random.uniform(1.0, 2.0))
                card_index = 0

        self.db.finish_task(task_id, total_notes=crawled)
        log.info(f"完成: {keyword}，采集 {crawled} 条")

    def _crawl_visible_card(self, card_index: int) -> bool:
        """点击第 N 个可见卡片，采集评论后返回。成功返回 True"""
        from src.controller.state import detect_page, PageState

        if not self.actions.tap_nth_card(card_index):
            log.debug(f"卡片 #{card_index} 点击失败")
            return False

        # 验证是否进入详情页（COMMENT 也是详情页内状态）
        page = detect_page(self.device)
        if page not in (PageState.NOTE_DETAIL, PageState.COMMENT):
            log.debug(f"卡片 #{card_index} 未进入详情页 (当前: {page})")
            # 仍在搜索结果页则不 back，避免退出搜索
            if page not in (PageState.SEARCH_RESULT, PageState.SEARCH_INPUT):
                self.actions.tap_back()
            return False

        # 模拟阅读停留
        time.sleep(random.uniform(3.0, 8.0))

        # 如果还没在评论状态，尝试打开评论
        if page != PageState.COMMENT and self.actions.open_comments():
            count = random.randint(*config.COMMENTS_SCROLL_RANGE)
            self.actions.scroll_comments(count)
            self.actions.tap_back()  # 关闭评论
        elif page == PageState.COMMENT:
            # 已经在评论状态，直接滚动采集
            count = random.randint(*config.COMMENTS_SCROLL_RANGE)
            self.actions.scroll_comments(count)

        self.actions.tap_back()  # 返回列表
        time.sleep(random.uniform(0.5, 1.0))
        return True

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
