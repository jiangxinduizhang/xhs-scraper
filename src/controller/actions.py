"""
核心 UI 操作封装
所有操作均包含随机化参数，模拟真实用户行为
"""
from __future__ import annotations

import random
import time
import logging
from typing import TYPE_CHECKING

from src import config

if TYPE_CHECKING:
    import uiautomator2 as u2

log = logging.getLogger(__name__)


class XHSActions:
    def __init__(self, device):
        self.d = device
        self.width, self.height = device.window_size()

    # ─── 滑动 ────────────────────────────────────────────────

    def swipe_up(self, distance_ratio: float = None):
        """向上滑动（加载更多内容）"""
        ratio = distance_ratio if distance_ratio is not None else random.uniform(*config.SCROLL_DISTANCE_RANGE)
        cx = self.width // 2 + random.randint(-30, 30)
        start_y = int(self.height * 0.70) + random.randint(-20, 20)
        end_y = int(self.height * (0.70 - ratio)) + random.randint(-20, 20)
        duration = random.uniform(*config.SWIPE_DURATION_RANGE)
        self.d.swipe(cx, start_y, cx, end_y, duration=duration)
        time.sleep(random.uniform(*config.OP_DELAY_RANGE))

    def swipe_down(self, distance_ratio: float = None):
        """向下滑动（下拉刷新 / 返回顶部）"""
        ratio = distance_ratio if distance_ratio is not None else random.uniform(*config.SCROLL_DISTANCE_RANGE)
        cx = self.width // 2 + random.randint(-30, 30)
        start_y = int(self.height * 0.30) + random.randint(-20, 20)
        end_y = int(self.height * (0.30 + ratio)) + random.randint(-20, 20)
        duration = random.uniform(*config.SWIPE_DURATION_RANGE)
        self.d.swipe(cx, start_y, cx, end_y, duration=duration)
        time.sleep(random.uniform(*config.OP_DELAY_RANGE))

    def scroll_feed(self, count: int = 5):
        """滚动列表，混入回滚/停顿/变速等人类行为避免触发反爬"""
        for i in range(count):
            self.swipe_up()

            # 每 3~6 次滑动：回滚一小段再继续（模拟"往回看了一眼"）
            if i > 0 and i % random.randint(3, 6) == 0:
                time.sleep(random.uniform(0.3, 0.8))
                self.swipe_down(distance_ratio=random.uniform(0.1, 0.25))
                time.sleep(random.uniform(0.5, 1.5))
                self.swipe_up(distance_ratio=random.uniform(0.15, 0.3))

            # 每 8~12 次滑动：快速滚到顶部再滑回来（破 loading 卡住）
            if i > 0 and i % random.randint(8, 12) == 0:
                log.debug("scroll_feed: 回到顶部再滑下来")
                for _ in range(3):
                    self.swipe_down(distance_ratio=random.uniform(0.5, 0.7))
                    time.sleep(random.uniform(0.2, 0.4))
                time.sleep(random.uniform(1.0, 2.0))
                for _ in range(3):
                    self.swipe_up(distance_ratio=random.uniform(0.5, 0.7))
                    time.sleep(random.uniform(0.2, 0.4))

            # 随机长停顿（模拟阅读）
            if random.random() < config.READ_PAUSE_PROBABILITY:
                time.sleep(random.uniform(*config.READ_PAUSE_RANGE))

    def scroll_comments(self, count: int = 3):
        """滚动评论列表"""
        for _ in range(count):
            self.swipe_up(distance_ratio=random.uniform(0.3, 0.5))

    def fling_load(self, rounds: int = 3):
        """快速上下翻飞加载列表，触发尽可能多的 API 分页请求

        每轮：快速 fling 到底 → 短暂停留 → fling 回顶部 → 短暂停留
        mitmproxy 在后台拦截所有 search/notes 分页响应并写入 DB。
        """
        cx = self.width // 2

        def _fling_down(n: int):
            for _ in range(n):
                jx = cx + random.randint(-20, 20)
                self.d.swipe(jx, int(self.height * 0.80), jx, int(self.height * 0.15),
                             duration=random.uniform(0.15, 0.25))
                # 每次 fling 后等一下让 API 加载触发
                time.sleep(random.uniform(0.8, 1.5))

        def _fling_up(n: int):
            for _ in range(n):
                jx = cx + random.randint(-20, 20)
                self.d.swipe(jx, int(self.height * 0.15), jx, int(self.height * 0.80),
                             duration=random.uniform(0.15, 0.25))
                time.sleep(random.uniform(0.3, 0.6))

        for r in range(rounds):
            flings = random.randint(5, 8)
            log.info(f"fling_load: 第 {r+1}/{rounds} 轮，向下 {flings} 次")
            _fling_down(flings)
            time.sleep(random.uniform(1.0, 2.0))

            flings_back = random.randint(4, 7)
            log.info(f"fling_load: 回顶 {flings_back} 次")
            _fling_up(flings_back)
            time.sleep(random.uniform(1.0, 2.5))

        # 最后回到列表顶部
        _fling_up(random.randint(6, 10))
        time.sleep(1)
        log.info("fling_load: 完成，已回到顶部")

    # ─── 点击 ────────────────────────────────────────────────

    def tap(self, x: int, y: int, jitter: int = None):
        """带坐标抖动的点击"""
        j = jitter if jitter is not None else config.CLICK_JITTER
        actual_x = x + random.randint(-j, j)
        actual_y = y + random.randint(-j, j)
        self.d.click(actual_x, actual_y)
        time.sleep(random.uniform(*config.OP_DELAY_RANGE))

    def tap_element(self, element, timeout: float = 5.0) -> bool:
        """点击 UI 元素，找不到则返回 False"""
        if element.exists(timeout=timeout):
            element.click()
            time.sleep(random.uniform(*config.OP_DELAY_RANGE))
            return True
        return False

    def tap_back(self):
        """返回上一页"""
        self.d.press("back")
        time.sleep(random.uniform(*config.OP_DELAY_RANGE))

    # ─── 卡片定位 ──────────────────────────────────────────────

    def tap_nth_card(self, index: int) -> bool:
        """点击搜索结果页第 N 个可见卡片（双列瀑布流，基于坐标定位）

        布局假设：双列瀑布流，左列 x=25%，右列 x=75%
        第一行 y 从屏幕 25% 开始，行高约 35% 屏幕高度
        """
        col = index % 2          # 0=左列, 1=右列
        row = index // 2         # 第几行

        # 左列存在"相关搜索"卡片时跳过，避免跳转到不相关搜索
        if col == 0 and self.d(text="相关搜索").exists(timeout=0.5):
            log.debug("左列检测到'相关搜索'卡片，跳过")
            return False

        x = int(self.width * (0.25 if col == 0 else 0.75))
        # 首行 y=35%，每行递增 35%（但超出屏幕的行需要先滚动）
        y = int(self.height * (0.35 + row * 0.35))

        if y >= self.height * 0.85:
            # 超出可视区域
            return False

        self.tap(x, y, jitter=10)
        time.sleep(random.uniform(1.0, 2.0))
        return True

    # ─── 搜索 ────────────────────────────────────────────────

    def search_keyword(self, keyword: str):
        """点击搜索入口 → 逐字输入 → 回车"""
        # 小红书搜索按钮 content-desc="搜索"
        search_btn = self.d(description="搜索")
        if not self.tap_element(search_btn, timeout=3):
            # 备用：点击顶部搜索栏区域（约屏幕 6% 高度）
            self.tap(self.width // 2, int(self.height * 0.06))
        time.sleep(random.uniform(0.5, 1.0))

        # 点击输入框确保聚焦（搜索页可能默认不聚焦）
        search_input = self.d(className="android.widget.EditText")
        if search_input.exists(timeout=3):
            search_input.click()
            time.sleep(0.3)
            search_input.clear_text()
            time.sleep(0.2)

            # 逐字输入模拟人工打字
            current = ""
            for char in keyword:
                current += char
                search_input.set_text(current)
                time.sleep(random.uniform(*config.TYPING_DELAY_RANGE))

            # 验证输入内容（get_text 可能含 hint 前缀如 "搜索, "）
            time.sleep(0.2)
            actual = search_input.get_text()
            if keyword not in actual:
                log.warning(f"搜索输入不匹配: 期望={keyword!r}, 实际={actual!r}，强制修正")
                search_input.set_text(keyword)
                time.sleep(0.3)

        time.sleep(random.uniform(0.3, 0.6))
        self.d.press("enter")
        time.sleep(random.uniform(2.0, 3.0))

    def select_sort(self, sort_type: str = "最新") -> bool:
        """在搜索结果页切换排序方式（综合/最新/最热）"""
        tab = self.d(text=sort_type)
        return self.tap_element(tab, timeout=3)

    # ─── 评论 ────────────────────────────────────────────────

    def open_comments(self) -> bool:
        """打开评论区，返回是否成功
        详情页底部评论按钮的 description 格式为 '评论 75'（带数量）
        """
        # 先找带数量的评论按钮（如 '评论 75'）
        comment_btn = self.d(descriptionMatches="评论 \\d+")
        if not comment_btn.exists(timeout=2):
            # 备用：纯"评论"描述
            comment_btn = self.d(description="评论")
        return self.tap_element(comment_btn, timeout=3)

    # ─── 等待 ────────────────────────────────────────────────

    def wait_for_page_load(self, timeout: float = 5.0):
        """等待加载动画消失（不用 resourceId，XHS 已混淆）"""
        loading = self.d(className="android.widget.ProgressBar")
        if loading.exists(timeout=1):
            loading.wait_gone(timeout=timeout)
        time.sleep(random.uniform(0.5, 1.0))

    # ─── 随机浏览 ────────────────────────────────────────────

    def random_browse(self):
        """偶尔执行非采集操作增加真实感"""
        action = random.choice(["swipe_down_then_up", "long_read", "skip"])
        if action == "swipe_down_then_up":
            # 小幅下滑再上滑，模拟"往回看了一下"
            self.swipe_down(distance_ratio=0.2)
            time.sleep(random.uniform(0.5, 1.0))
            self.swipe_up(distance_ratio=0.2)
        elif action == "long_read":
            # 长时间停留，模拟"仔细阅读"
            time.sleep(random.uniform(5.0, 15.0))
        # skip = do nothing
