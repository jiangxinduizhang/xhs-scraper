"""
页面状态检测单元测试 - 使用 MagicMock 模拟设备，无实际 ADB 连接
"""
from unittest.mock import MagicMock, patch
from src.controller.state import detect_page, PageState, _has_captcha, _has_dialog


def make_device(package="com.xingin.xhs", activity="MainActivity"):
    """创建模拟设备，默认所有元素不存在"""
    mock_d = MagicMock()
    mock_d.app_current.return_value = {"package": package, "activity": activity}
    mock_d.return_value.exists.return_value = False
    return mock_d


# ─── _has_captcha ────────────────────────────────────────────

class TestHasCaptcha:
    def test_returns_true_when_element_exists(self):
        mock_d = MagicMock()
        mock_d.return_value.exists.return_value = True
        assert _has_captcha(mock_d) is True

    def test_returns_false_when_no_elements(self):
        mock_d = MagicMock()
        mock_d.return_value.exists.return_value = False
        assert _has_captcha(mock_d) is False


# ─── _has_dialog ─────────────────────────────────────────────

class TestHasDialog:
    def test_returns_true_when_dialog_exists(self):
        mock_d = MagicMock()
        mock_d.return_value.exists.return_value = True
        assert _has_dialog(mock_d) is True

    def test_returns_false_when_no_dialog(self):
        mock_d = MagicMock()
        mock_d.return_value.exists.return_value = False
        assert _has_dialog(mock_d) is False


# ─── detect_page ─────────────────────────────────────────────

class TestDetectPage:
    def test_wrong_package_returns_unknown(self):
        mock_d = make_device(package="com.other.app")
        assert detect_page(mock_d) == PageState.UNKNOWN

    def test_login_activity_returns_login(self):
        """登录页检测，函数在 _has_captcha 之前返回，不需要 patch"""
        mock_d = make_device(activity="LoginActivity")
        assert detect_page(mock_d) == PageState.LOGIN

    def test_login_lowercase_activity(self):
        mock_d = make_device(activity="com.xingin.xhs.login.LoginActivity")
        assert detect_page(mock_d) == PageState.LOGIN

    def test_captcha_detected(self):
        mock_d = make_device()
        with patch("src.controller.state._has_captcha", return_value=True), \
             patch("src.controller.state._has_dialog", return_value=False):
            assert detect_page(mock_d) == PageState.CAPTCHA

    def test_unknown_dialog_detected(self):
        mock_d = make_device()
        with patch("src.controller.state._has_captcha", return_value=False), \
             patch("src.controller.state._has_dialog", return_value=True):
            assert detect_page(mock_d) == PageState.UNKNOWN_DIALOG

    def test_captcha_takes_priority_over_dialog(self):
        """captcha 检测优先于 dialog 检测"""
        mock_d = make_device()
        with patch("src.controller.state._has_captcha", return_value=True), \
             patch("src.controller.state._has_dialog", return_value=True):
            assert detect_page(mock_d) == PageState.CAPTCHA

    def test_home_page_detected(self):
        """首页通过 description='首页' 和 '发现' 同时存在来判断"""
        mock_d = make_device()

        def mock_selector(*args, **kwargs):
            m = MagicMock()
            desc = kwargs.get("description", "")
            # 首页同时有"首页"和"发现"的 description
            m.exists.return_value = desc in ("首页", "发现")
            return m

        mock_d.side_effect = mock_selector

        with patch("src.controller.state._has_captcha", return_value=False), \
             patch("src.controller.state._has_dialog", return_value=False):
            assert detect_page(mock_d) == PageState.HOME

    def test_comment_page_detected(self):
        """评论页：在 NoteDetail activity 内，检测到 '发布评论' 元素则判断为 COMMENT"""
        mock_d = make_device(activity="NoteDetailActivity")

        def mock_selector(*args, **kwargs):
            m = MagicMock()
            desc_contains = kwargs.get("descriptionContains", "")
            m.exists.return_value = "发布评论" in desc_contains
            m.count = 0
            return m

        mock_d.side_effect = mock_selector

        with patch("src.controller.state._has_captcha", return_value=False), \
             patch("src.controller.state._has_dialog", return_value=False):
            assert detect_page(mock_d) == PageState.COMMENT

    def test_unknown_when_no_elements_match(self):
        mock_d = make_device()
        with patch("src.controller.state._has_captcha", return_value=False), \
             patch("src.controller.state._has_dialog", return_value=False):
            assert detect_page(mock_d) == PageState.UNKNOWN
