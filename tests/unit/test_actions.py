"""
XHSActions 单元测试
mock 设备对象，验证 UI 操作的行为和方向正确性
"""
import pytest
from unittest.mock import MagicMock, patch, call
from src.controller.actions import XHSActions

SCREEN_W, SCREEN_H = 1080, 2400


@pytest.fixture
def device():
    mock_d = MagicMock()
    mock_d.window_size.return_value = (SCREEN_W, SCREEN_H)
    return mock_d


@pytest.fixture
def actions(device):
    return XHSActions(device)


# ─── 初始化 ──────────────────────────────────────────────────

class TestInit:
    def test_reads_window_size(self, device):
        a = XHSActions(device)
        assert a.width == SCREEN_W
        assert a.height == SCREEN_H


# ─── swipe_up ────────────────────────────────────────────────

class TestSwipeUp:
    def test_calls_swipe(self, actions, device):
        with patch("time.sleep"):
            actions.swipe_up(distance_ratio=0.4)
        assert device.swipe.call_count == 1

    def test_direction_is_upward(self, actions, device):
        """start_y > end_y 才是向上滑动（duration 是 kwarg，只解包 4 个位置参数）"""
        with patch("time.sleep"):
            actions.swipe_up(distance_ratio=0.4)
        cx, start_y, cx2, end_y = device.swipe.call_args[0]
        assert start_y > end_y, f"期望 start_y({start_y}) > end_y({end_y})"

    def test_x_is_near_center(self, actions, device):
        with patch("time.sleep"):
            actions.swipe_up(distance_ratio=0.4)
        cx, start_y, cx2, end_y = device.swipe.call_args[0]
        assert SCREEN_W // 2 - 60 < cx < SCREEN_W // 2 + 60

    def test_y_coords_within_screen(self, actions, device):
        with patch("time.sleep"):
            actions.swipe_up(distance_ratio=0.4)
        cx, start_y, cx2, end_y = device.swipe.call_args[0]
        assert 0 < start_y < SCREEN_H
        assert 0 < end_y < SCREEN_H


# ─── swipe_down ──────────────────────────────────────────────

class TestSwipeDown:
    def test_direction_is_downward(self, actions, device):
        """start_y < end_y 才是向下滑动"""
        with patch("time.sleep"):
            actions.swipe_down(distance_ratio=0.4)
        cx, start_y, cx2, end_y = device.swipe.call_args[0]
        assert start_y < end_y, f"期望 start_y({start_y}) < end_y({end_y})"


# ─── scroll_feed ─────────────────────────────────────────────

class TestScrollFeed:
    def test_calls_swipe_n_times(self, actions, device):
        with patch("time.sleep"), patch("random.random", return_value=1.0):
            actions.scroll_feed(count=4)
        assert device.swipe.call_count == 4

    def test_long_pause_triggered_by_probability(self, actions, device):
        sleep_calls = []
        with patch("random.random", return_value=0.0), \
             patch("time.sleep", side_effect=lambda t: sleep_calls.append(t)):
            actions.scroll_feed(count=1)
        # 应该有至少两次 sleep：操作间隔 + 长停顿
        assert len(sleep_calls) >= 2


# ─── tap ─────────────────────────────────────────────────────

class TestTap:
    def test_calls_click(self, actions, device):
        with patch("time.sleep"):
            actions.tap(500, 600, jitter=0)
        device.click.assert_called_once_with(500, 600)

    def test_zero_jitter_is_exact(self, actions, device):
        with patch("time.sleep"):
            actions.tap(300, 400, jitter=0)
        device.click.assert_called_once_with(300, 400)

    def test_nonzero_jitter_stays_near_target(self, actions, device):
        with patch("time.sleep"):
            actions.tap(500, 600, jitter=10)
        actual_x, actual_y = device.click.call_args[0]
        assert 490 <= actual_x <= 510
        assert 590 <= actual_y <= 610


# ─── tap_element ─────────────────────────────────────────────

class TestTapElement:
    def test_returns_true_and_clicks_when_found(self, actions):
        element = MagicMock()
        element.exists.return_value = True
        with patch("time.sleep"):
            result = actions.tap_element(element, timeout=3)
        assert result is True
        element.click.assert_called_once()

    def test_returns_false_and_no_click_when_not_found(self, actions):
        element = MagicMock()
        element.exists.return_value = False
        with patch("time.sleep"):
            result = actions.tap_element(element, timeout=3)
        assert result is False
        element.click.assert_not_called()


# ─── tap_back ────────────────────────────────────────────────

class TestTapBack:
    def test_presses_back_key(self, actions, device):
        with patch("time.sleep"):
            actions.tap_back()
        device.press.assert_called_once_with("back")


# ─── open_comments ───────────────────────────────────────────

class TestOpenComments:
    def test_returns_true_when_button_found(self, actions, device):
        mock_btn = MagicMock()
        mock_btn.exists.return_value = True
        device.return_value = mock_btn

        with patch("time.sleep"):
            result = actions.open_comments()
        assert result is True

    def test_returns_false_when_button_not_found(self, actions, device):
        mock_btn = MagicMock()
        mock_btn.exists.return_value = False
        device.return_value = mock_btn

        with patch("time.sleep"):
            result = actions.open_comments()
        assert result is False


# ─── scroll_comments ─────────────────────────────────────────

class TestScrollComments:
    def test_calls_swipe_n_times(self, actions, device):
        with patch("time.sleep"):
            actions.scroll_comments(count=3)
        assert device.swipe.call_count == 3
