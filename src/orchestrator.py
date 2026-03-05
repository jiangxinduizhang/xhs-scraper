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
from src.controller.device import connect_device, launch_app, preflight_check
from src.controller.state import navigate_to_home
from src.storage.db import Database

log = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, keywords: list[str], db_path: str = "data/xiaohongshu.db",
                 sort_type: str = "综合"):
        self.keywords = keywords
        self.db = Database(db_path)
        self.daily_count = 0
        self.sort_type = sort_type
        self._device = None
        self._actions = None
        self._midscene = None

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

    @property
    def midscene(self):
        """懒加载 Midscene 处理器"""
        if self._midscene is None:
            from src.midscene.bridge import MidsceneBridge
            from src.midscene.handlers import MidsceneHandler
            bridge = MidsceneBridge(self.device.serial)
            self._midscene = MidsceneHandler(self.device, bridge)
        return self._midscene

    # ─── 主运行循环 ──────────────────────────────────────────

    def run(self, daily_limit: int = None):
        """启动抓取，依次处理所有关键词"""
        self._limit = daily_limit or config.DAILY_NOTE_LIMIT

        # 检查是否在工作时间窗口内
        self._wait_for_work_hours()

        # 代理链路预检
        preflight_check()

        launch_app(self.device, fresh_start=True)
        time.sleep(2)

        session_start = time.time()

        for keyword in self.keywords:
            if self.daily_count >= self._limit:
                log.info(f"已达每日上限 {self._limit}，停止")
                break

            # 检查是否超过单次会话最大时长
            elapsed = time.time() - session_start
            if elapsed >= config.SESSION_MAX_DURATION:
                log.info(f"会话已达最大时长 {config.SESSION_MAX_DURATION}s，停止本次会话")
                break

            try:
                self._run_keyword(keyword)
            except Exception as e:
                log.error(f"关键词 [{keyword}] 异常: {e}", exc_info=True)
                self._recover()

            delay = random.uniform(*config.INTER_KEYWORD_DELAY)
            log.info(f"等待 {delay:.0f}s 后处理下一个关键词...")
            time.sleep(delay)

    def _wait_for_work_hours(self):
        """若当前不在工作时段则等待到开始时间"""
        import datetime
        start_h, end_h = config.WORK_HOURS
        now = datetime.datetime.now()
        current_h = now.hour
        if current_h < start_h or current_h >= end_h:
            # 计算到下一个工作时段开始的秒数
            if current_h >= end_h:
                # 今天已过工作时段，等到明天
                next_start = now.replace(hour=start_h, minute=0, second=0, microsecond=0)
                next_start += datetime.timedelta(days=1)
            else:
                # 今天还没到工作时段
                next_start = now.replace(hour=start_h, minute=0, second=0, microsecond=0)
            wait_secs = (next_start - now).total_seconds()
            log.info(f"当前不在工作时段 {start_h}:00-{end_h}:00，等待 {wait_secs:.0f}s")
            time.sleep(wait_secs)

    # ─── 关键词任务 ──────────────────────────────────────────

    def _run_keyword(self, keyword: str):
        log.info(f"开始抓取: {keyword}")
        task_id = self.db.create_task(keyword)

        navigate_to_home(self.device)
        self.actions.search_keyword(keyword)
        time.sleep(2)

        # 切换排序（默认"综合"不需要额外操作）
        if self.sort_type != "综合":
            if self.actions.select_sort(self.sort_type):
                log.info(f"已切换排序: {self.sort_type}")
                time.sleep(2)

        # 快速上下翻飞加载列表，mitmproxy 拦截所有分页 API 响应写入 DB
        self.actions.fling_load(rounds=3)
        time.sleep(2)  # 给 mitmproxy 写入缓冲时间

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

            # 走神：有小概率暂停一段时间，模拟用户分心
            if random.random() < config.IDLE_PROBABILITY:
                idle_secs = random.uniform(*config.IDLE_DURATION_RANGE)
                log.info(f"走神中，暂停 {idle_secs:.0f}s...")
                time.sleep(idle_secs)

            card_index += 1
            # 每处理完一行（2张卡片）后滚动并重置 index
            if card_index >= 2:
                self.actions.swipe_up()
                time.sleep(random.uniform(1.0, 2.0))
                card_index = 0

        self.db.finish_task(task_id, total_notes=crawled)
        log.info(f"完成: {keyword}，采集 {crawled} 条")

    def _crawl_visible_card(self, card_index: int) -> bool:
        """点击第 N 个可见卡片，在详情页停留后返回。成功返回 True

        简化逻辑：进入详情页后评论 API 已自动加载，无需显式打开评论区。
        在详情页向下滚动 2-3 次触发更多评论分页加载，然后返回。
        """
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
                # 非标准页面（如问一问），循环 back 直到回到搜索结果
                for _ in range(3):
                    self.actions.tap_back()
                    time.sleep(0.8)
                    page = detect_page(self.device)
                    if page in (PageState.SEARCH_RESULT, PageState.SEARCH_INPUT):
                        break
                if page not in (PageState.SEARCH_RESULT, PageState.SEARCH_INPUT):
                    log.warning(f"卡片 #{card_index} 多次 back 仍未回到搜索页 (当前: {page})")
            return False

        # 偶发非采集行为：有 15% 概率快速返回（模拟"看了一眼不感兴趣"）
        if random.random() < 0.15:
            log.debug(f"卡片 #{card_index} 快速略过（模拟不感兴趣）")
            time.sleep(random.uniform(0.5, 1.5))
            self.actions.tap_back()
            time.sleep(random.uniform(0.5, 1.0))
            return True

        # 偶发非采集行为：有 10% 概率执行随机浏览（模拟"仔细阅读"）
        if random.random() < 0.10:
            log.debug(f"卡片 #{card_index} 触发随机浏览行为")
            self.actions.random_browse()

        # 模拟阅读停留
        time.sleep(random.uniform(3.0, 8.0))

        # 向下滑动触发更多评论加载（评论 API 在进入详情时已自动触发）
        count = random.randint(*config.COMMENTS_SCROLL_RANGE)
        self.actions.scroll_comments(count)

        self.actions.tap_back()  # 返回列表
        time.sleep(random.uniform(0.5, 1.0))
        return True

    # ─── 异常恢复 ────────────────────────────────────────────

    def _recover(self):
        """异常后尝试恢复到首页 (带 Midscene 视觉辅助)"""
        log.info("尝试恢复到首页...")
        try:
            # 1. 视觉异常处理 (验证码、未知弹窗)
            self.midscene.handle()
            
            # 2. 尝试常规导航回首页
            navigate_to_home(self.device)
        except Exception as e:
            log.warning(f"常规恢复失败: {e}，尝试强制重启 APP")
            try:
                launch_app(self.device, fresh_start=True)
                time.sleep(3)
            except Exception as inner_e:
                log.error(f"严重异常：最终恢复失败: {inner_e}")


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
    parser.add_argument("--sort", default="综合", choices=["综合", "最新", "最热"], help="搜索排序方式")
    parser.add_argument("--db", default="data/xiaohongshu.db", help="数据库路径")
    args = parser.parse_args()

    orc = Orchestrator(args.keywords, db_path=args.db, sort_type=args.sort)
    orc.run(daily_limit=args.limit)


if __name__ == "__main__":
    main()
