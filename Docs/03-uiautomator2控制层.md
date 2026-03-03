# 03 - uiautomator2 控制层

## 连接与设备初始化

### 基础连接

```python
# src/controller/device.py
import uiautomator2 as u2
import time
import logging

logger = logging.getLogger(__name__)

APP_PACKAGE = "com.xingin.xhs"
APP_ACTIVITY = ".activity.SplashActivity"


def connect_device(serial: str = None) -> u2.Device:
    """
    连接 ADB 设备
    serial: 设备序列号（多设备时指定），None 则自动选择唯一连接的设备
    """
    if serial:
        d = u2.connect(serial)
    else:
        d = u2.connect_usb()

    # 验证连接
    info = d.device_info
    logger.info(f"已连接设备: {info['brand']} {info['model']} (Android {info['version']})")
    logger.info(f"屏幕分辨率: {d.window_size()}")

    # 基础设置
    d.settings["wait_timeout"] = 10    # 元素等待超时（秒）
    d.settings["operation_delay"] = (0.5, 1.0)  # 操作间隔随机延时

    return d


def launch_app(d: u2.Device, fresh_start: bool = False):
    """启动小红书"""
    if fresh_start:
        d.app_stop(APP_PACKAGE)
        time.sleep(1)

    d.app_start(APP_PACKAGE, use_monkey=False)
    time.sleep(3)  # 等待启动动画

    # 处理启动时可能出现的弹窗
    _dismiss_startup_dialogs(d)


def _dismiss_startup_dialogs(d: u2.Device):
    """处理启动弹窗（更新提示、权限请求等）"""
    dismiss_texts = ["我知道了", "跳过", "允许", "稍后再说", "取消"]
    for text in dismiss_texts:
        if d(text=text).exists(timeout=1):
            d(text=text).click()
            time.sleep(0.5)
```

---

## 核心操作封装

### src/controller/actions.py

```python
"""
核心 UI 操作封装，包含随机化参数
"""
import random
import time
import uiautomator2 as u2
import logging

logger = logging.getLogger(__name__)


class XHSActions:
    def __init__(self, device: u2.Device):
        self.d = device
        self.width, self.height = device.window_size()

    # ─── 滑动操作 ───────────────────────────────────────────

    def swipe_up(self, distance_ratio: float = 0.5):
        """向上滑动（加载更多内容）"""
        # 起点：屏幕下方 70% 处，终点：屏幕上方 30% 处
        cx = self.width // 2 + random.randint(-30, 30)       # 水平中心抖动
        start_y = int(self.height * 0.70) + random.randint(-20, 20)
        end_y = int(self.height * (0.70 - distance_ratio)) + random.randint(-20, 20)

        duration = random.uniform(0.3, 0.6)   # 滑动速度随机化
        self.d.swipe(cx, start_y, cx, end_y, duration=duration)
        time.sleep(random.uniform(0.8, 1.5))   # 滑动后停顿

    def swipe_down(self, distance_ratio: float = 0.4):
        """向下滑动（返回顶部 / 下拉刷新）"""
        cx = self.width // 2 + random.randint(-30, 30)
        start_y = int(self.height * 0.30) + random.randint(-20, 20)
        end_y = int(self.height * (0.30 + distance_ratio)) + random.randint(-20, 20)

        duration = random.uniform(0.3, 0.6)
        self.d.swipe(cx, start_y, cx, end_y, duration=duration)
        time.sleep(random.uniform(0.8, 1.5))

    def scroll_feed(self, count: int = 5):
        """滚动首页/搜索结果列表"""
        for i in range(count):
            self.swipe_up(distance_ratio=random.uniform(0.3, 0.6))
            # 偶尔停顿更长时间（模拟用户查看内容）
            if random.random() < 0.2:
                time.sleep(random.uniform(2.0, 4.0))

    # ─── 点击操作 ───────────────────────────────────────────

    def tap(self, x: int, y: int, jitter: int = 5):
        """点击，带坐标抖动"""
        actual_x = x + random.randint(-jitter, jitter)
        actual_y = y + random.randint(-jitter, jitter)
        self.d.click(actual_x, actual_y)
        time.sleep(random.uniform(0.3, 0.8))

    def tap_element(self, element, timeout: float = 5.0) -> bool:
        """点击 UI 元素，返回是否成功"""
        if element.exists(timeout=timeout):
            element.click()
            time.sleep(random.uniform(0.5, 1.0))
            return True
        return False

    def tap_back(self):
        """返回上一页"""
        self.d.press("back")
        time.sleep(random.uniform(0.5, 1.0))

    # ─── 搜索操作 ───────────────────────────────────────────

    def search_keyword(self, keyword: str):
        """在小红书搜索关键词"""
        # 点击搜索入口
        search_btn = self.d(description="搜索") or self.d(resourceId="com.xingin.xhs:id/search")
        if not self.tap_element(search_btn):
            # 备用：点击顶部搜索栏区域
            self.tap(self.width // 2, int(self.height * 0.06))

        time.sleep(random.uniform(0.5, 1.0))

        # 输入关键词（模拟逐字输入）
        search_input = self.d(focused=True)
        if search_input.exists(timeout=3):
            search_input.clear_text()
            # 逐字符输入，带随机延时
            for char in keyword:
                search_input.set_text(search_input.get_text() + char if search_input.get_text() else char)
                time.sleep(random.uniform(0.05, 0.15))

        time.sleep(random.uniform(0.3, 0.6))
        self.d.press("enter")
        time.sleep(random.uniform(2.0, 3.0))   # 等待搜索结果加载

    # ─── 评论操作 ───────────────────────────────────────────

    def open_comments(self) -> bool:
        """打开评论区"""
        comment_btn = self.d(description="评论") or \
                      self.d(resourceId="com.xingin.xhs:id/comment_icon")
        return self.tap_element(comment_btn)

    def scroll_comments(self, count: int = 3):
        """滚动评论列表"""
        for _ in range(count):
            self.swipe_up(distance_ratio=random.uniform(0.3, 0.5))

    # ─── 等待工具 ───────────────────────────────────────────

    def wait_for_page_load(self, timeout: float = 5.0):
        """等待页面加载完成（通过检测加载动画消失）"""
        # 等待加载指示器消失
        loading = self.d(resourceId="com.xingin.xhs:id/loading")
        if loading.exists(timeout=1):
            loading.wait_gone(timeout=timeout)
        time.sleep(random.uniform(0.5, 1.0))
```

---

## 随机化参数配置

| 参数 | 值范围 | 说明 |
|------|--------|------|
| 点击坐标抖动 | ±5px | 模拟手指点击不精确 |
| 滑动速度 | 0.3~0.6 秒 | 随机滑动时长 |
| 操作间隔 | 0.5~1.5 秒 | 每次操作后随机等待 |
| 阅读停顿 | 2.0~4.0 秒 | 20% 概率触发长停顿 |
| 搜索输入延时 | 50~150 ms/字符 | 模拟人工打字速度 |
| 滑动距离 | 屏幕高度的 30%~60% | 随机滑动幅度 |
| 每批次笔记数 | 15~25 条 | 每次搜索抓取数量随机 |

---

## 页面状态检测

### src/controller/state.py

```python
"""
页面状态检测 - 判断当前停留在哪个页面
"""
import uiautomator2 as u2
from enum import Enum


class PageState(Enum):
    UNKNOWN = "unknown"
    HOME = "home"               # 首页
    SEARCH_INPUT = "search_input"   # 搜索输入页
    SEARCH_RESULT = "search_result" # 搜索结果列表
    NOTE_DETAIL = "note_detail"     # 帖子详情
    COMMENT = "comment"             # 评论页
    USER_PROFILE = "user_profile"   # 用户主页
    LOGIN = "login"                 # 登录页
    CAPTCHA = "captcha"             # 验证码页
    UNKNOWN_DIALOG = "unknown_dialog"  # 未知弹窗


def detect_page(d: u2.Device) -> PageState:
    """检测当前页面状态"""
    # 快速截图分析当前 activity
    current_app = d.app_current()
    if current_app.get("package") != "com.xingin.xhs":
        return PageState.UNKNOWN

    activity = current_app.get("activity", "")

    # 登录页检测
    if "Login" in activity or "login" in activity:
        return PageState.LOGIN

    # 验证码检测（通过截图中的关键元素）
    if _has_captcha(d):
        return PageState.CAPTCHA

    # 评论页（评论弹窗）
    if d(resourceId="com.xingin.xhs:id/comment_input").exists(timeout=0.5):
        return PageState.COMMENT

    # 帖子详情页
    if d(resourceId="com.xingin.xhs:id/note_container").exists(timeout=0.5):
        return PageState.NOTE_DETAIL

    # 搜索结果列表
    if d(resourceId="com.xingin.xhs:id/search_result_list").exists(timeout=0.5):
        return PageState.SEARCH_RESULT

    # 搜索输入页
    if d(focused=True).exists(timeout=0.5):
        return PageState.SEARCH_INPUT

    # 首页
    if d(resourceId="com.xingin.xhs:id/home_tab").exists(timeout=0.5):
        return PageState.HOME

    # 检测未知弹窗
    if _has_dialog(d):
        return PageState.UNKNOWN_DIALOG

    return PageState.UNKNOWN


def _has_captcha(d: u2.Device) -> bool:
    """检测验证码"""
    captcha_indicators = [
        d(textContains="验证"),
        d(textContains="滑动"),
        d(textContains="拼图"),
        d(descriptionContains="验证码"),
    ]
    return any(elem.exists(timeout=0.3) for elem in captcha_indicators)


def _has_dialog(d: u2.Device) -> bool:
    """检测未知弹窗"""
    dialog_indicators = [
        d(className="android.app.Dialog"),
        d(resourceId="com.xingin.xhs:id/dialog_content"),
    ]
    return any(elem.exists(timeout=0.3) for elem in dialog_indicators)


def navigate_to_home(d: u2.Device, max_back: int = 5):
    """通过多次返回回到首页"""
    for _ in range(max_back):
        state = detect_page(d)
        if state == PageState.HOME:
            return True
        d.press("back")
        import time
        time.sleep(0.8)
    return False
```

---

## 设备配置文件

### src/config.py（控制层相关部分）

```python
# 设备配置
DEVICE_SERIAL = None    # None = 自动选择唯一 USB 设备

# 随机化参数
SWIPE_DURATION_RANGE = (0.3, 0.6)      # 滑动持续时间（秒）
CLICK_JITTER = 5                         # 点击坐标抖动（像素）
OP_DELAY_RANGE = (0.5, 1.5)             # 操作间隔延时范围
READ_PAUSE_PROBABILITY = 0.2             # 长停顿触发概率
READ_PAUSE_RANGE = (2.0, 4.0)           # 长停顿时长
TYPING_DELAY_RANGE = (0.05, 0.15)       # 每字符输入延时
SCROLL_DISTANCE_RANGE = (0.3, 0.6)      # 滑动幅度（屏幕高度比例）

# 抓取行为配置
NOTES_PER_KEYWORD = (15, 25)            # 每关键词抓取笔记数（随机范围）
COMMENTS_PER_NOTE = (10, 30)            # 每笔记抓取评论数（随机范围）
INTER_KEYWORD_DELAY = (30, 90)          # 关键词间隔时间（秒）
DAILY_NOTE_LIMIT = 500                  # 每日抓取上限
```
