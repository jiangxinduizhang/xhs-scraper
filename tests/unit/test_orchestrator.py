"""
Orchestrator 单元测试
mock 设备、actions、db、midscene，验证调度逻辑
"""
import datetime
import pytest
from unittest.mock import MagicMock, patch

from src.orchestrator import Orchestrator
from src.controller.state import PageState


@pytest.fixture
def mock_db():
    with patch("src.orchestrator.Database") as DB:
        db = DB.return_value
        db.create_task.return_value = 1
        yield db


@pytest.fixture
def mock_device():
    return MagicMock()


@pytest.fixture
def mock_actions():
    actions = MagicMock()
    actions.tap_nth_card.return_value = True
    actions.select_sort.return_value = True
    return actions


@pytest.fixture
def mock_midscene():
    return MagicMock()


@pytest.fixture
def orc(mock_db, mock_device, mock_actions, mock_midscene):
    """创建一个所有外部依赖都已 mock 的 Orchestrator"""
    with patch("src.orchestrator.Database", return_value=mock_db):
        o = Orchestrator(["咖啡", "奶茶"], db_path=":memory:", sort_type="最新")
    o._device = mock_device
    o._actions = mock_actions
    o._midscene = mock_midscene
    return o


# ─── test_run_stops_at_daily_limit ────────────────────────────

class TestRunStopsAtDailyLimit:
    def test_stops_processing_keywords_when_limit_reached(self, orc):
        """daily_count 达到 limit 后不再处理后续关键词"""
        call_log = []

        def fake_run_keyword(kw):
            call_log.append(kw)
            orc.daily_count = orc._limit  # 第一个关键词就达到上限

        with patch.object(orc, "_run_keyword", side_effect=fake_run_keyword), \
             patch.object(orc, "_wait_for_work_hours"), \
             patch("src.orchestrator.preflight_check"), \
             patch("src.orchestrator.launch_app"), \
             patch("time.sleep"), \
             patch("random.uniform", return_value=0):
            orc.run(daily_limit=5)

        assert call_log == ["咖啡"], "达到 limit 后应跳过第二个关键词"


# ─── test_run_stops_at_session_timeout ────────────────────────

class TestRunStopsAtSessionTimeout:
    def test_stops_when_session_exceeds_max_duration(self, orc):
        """会话超过 SESSION_MAX_DURATION 后停止"""
        # time.time() 调用顺序: session_start=100, 循环第一次检查=100+3601
        time_values = iter([100.0, 100.0 + 3601])
        run_keyword_mock = MagicMock()

        with patch.object(orc, "_run_keyword", run_keyword_mock), \
             patch.object(orc, "_wait_for_work_hours"), \
             patch("src.orchestrator.preflight_check"), \
             patch("src.orchestrator.launch_app"), \
             patch("time.sleep"), \
             patch("time.time", side_effect=time_values), \
             patch("random.uniform", return_value=0):
            orc.run(daily_limit=100)

        run_keyword_mock.assert_not_called()


# ─── test_run_keyword_search_and_sort ─────────────────────────

class TestRunKeywordSearchAndSort:
    def test_search_called_and_sort_selected(self, orc, mock_actions):
        """sort_type != '综合' 时 select_sort 应被调用"""
        with patch("time.sleep"), \
             patch("random.randint", return_value=0), \
             patch("src.orchestrator.navigate_to_home"):
            orc._limit = 100
            orc._run_keyword("咖啡")

        mock_actions.search_keyword.assert_called_once_with("咖啡")
        mock_actions.select_sort.assert_called_once_with("最新")
        mock_actions.fling_load.assert_called_once_with(rounds=3)

    def test_sort_not_called_when_zonghe(self, mock_db, mock_device, mock_actions, mock_midscene):
        """sort_type == '综合' 时 select_sort 不应被调用"""
        with patch("src.orchestrator.Database", return_value=mock_db):
            o = Orchestrator(["咖啡"], db_path=":memory:", sort_type="综合")
        o._device = mock_device
        o._actions = mock_actions
        o._midscene = mock_midscene
        o._limit = 100

        with patch("time.sleep"), \
             patch("random.randint", return_value=0), \
             patch("src.orchestrator.navigate_to_home"):
            o._run_keyword("咖啡")

        mock_actions.select_sort.assert_not_called()


# ─── test_crawl_visible_card_success ──────────────────────────

class TestCrawlVisibleCardSuccess:
    def test_returns_true_on_detail_page(self, orc, mock_actions):
        """tap_nth_card 成功 + detect_page 返回 NOTE_DETAIL → 返回 True"""
        with patch("src.controller.state.detect_page", return_value=PageState.NOTE_DETAIL), \
             patch("time.sleep"), \
             patch("random.random", return_value=0.99), \
             patch("random.uniform", return_value=5.0), \
             patch("random.randint", return_value=3):
            result = orc._crawl_visible_card(0)

        assert result is True
        mock_actions.tap_nth_card.assert_called_once_with(0)
        mock_actions.scroll_comments.assert_called_once_with(3)
        mock_actions.tap_back.assert_called_once()

    def test_returns_false_when_tap_fails(self, orc, mock_actions):
        """tap_nth_card 返回 False → 直接返回 False"""
        mock_actions.tap_nth_card.return_value = False

        result = orc._crawl_visible_card(0)

        assert result is False


# ─── test_crawl_visible_card_skip ─────────────────────────────

class TestCrawlVisibleCardSkip:
    def test_quick_skip_returns_true(self, orc, mock_actions):
        """random < 0.15 触发快速略过，仍然返回 True"""
        with patch("src.controller.state.detect_page", return_value=PageState.NOTE_DETAIL), \
             patch("time.sleep"), \
             patch("random.random", return_value=0.10), \
             patch("random.uniform", return_value=1.0):
            result = orc._crawl_visible_card(0)

        assert result is True
        mock_actions.tap_back.assert_called_once()
        # 快速略过不应滚动评论
        mock_actions.scroll_comments.assert_not_called()


# ─── test_recover_on_exception ────────────────────────────────

class TestRecoverOnException:
    def test_recover_called_when_run_keyword_raises(self, orc, mock_midscene):
        """_run_keyword 抛异常后 _recover 被调用"""
        run_keyword_mock = MagicMock(side_effect=RuntimeError("boom"))

        with patch.object(orc, "_run_keyword", run_keyword_mock), \
             patch.object(orc, "_wait_for_work_hours"), \
             patch("src.orchestrator.preflight_check"), \
             patch("src.orchestrator.launch_app"), \
             patch("src.orchestrator.navigate_to_home"), \
             patch("time.sleep"), \
             patch("random.uniform", return_value=0):
            orc.run(daily_limit=100)

        # midscene.handle 在 _recover 中被调用，每个关键词一次
        assert mock_midscene.handle.call_count == 2

    def test_recover_falls_back_to_launch_app(self, orc, mock_midscene):
        """_recover 中 navigate_to_home 也失败时，fallback 到 launch_app"""
        mock_midscene.handle.side_effect = RuntimeError("midscene fail")

        with patch("src.orchestrator.navigate_to_home", side_effect=RuntimeError("nav fail")), \
             patch("src.orchestrator.launch_app") as mock_launch, \
             patch("time.sleep"):
            orc._recover()

        mock_launch.assert_called_once_with(orc._device, fresh_start=True)


# ─── test_wait_for_work_hours ─────────────────────────────────

class TestWaitForWorkHours:
    def test_sleeps_when_before_work_hours(self, orc):
        """凌晨 3 点应等待到 8 点"""
        fake_now = datetime.datetime(2026, 3, 17, 3, 0, 0)

        with patch("datetime.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            # 让 replace 和 timedelta 正常工作
            mock_dt.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            with patch("datetime.timedelta", side_effect=datetime.timedelta):
                with patch("time.sleep") as mock_sleep:
                    orc._wait_for_work_hours()

        mock_sleep.assert_called_once()
        wait_secs = mock_sleep.call_args[0][0]
        # 3:00 -> 8:00 = 5 hours = 18000s
        assert 17900 < wait_secs < 18100

    def test_no_sleep_during_work_hours(self, orc):
        """工作时段内不应 sleep"""
        fake_now = datetime.datetime(2026, 3, 17, 12, 0, 0)

        with patch("datetime.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            with patch("time.sleep") as mock_sleep:
                orc._wait_for_work_hours()

        mock_sleep.assert_not_called()

    def test_sleeps_when_after_work_hours(self, orc):
        """23:30 应等待到明天 8 点"""
        fake_now = datetime.datetime(2026, 3, 17, 23, 30, 0)

        with patch("datetime.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            with patch("datetime.timedelta", side_effect=datetime.timedelta):
                with patch("time.sleep") as mock_sleep:
                    orc._wait_for_work_hours()

        mock_sleep.assert_called_once()
        wait_secs = mock_sleep.call_args[0][0]
        # 23:30 -> next day 8:00 = 8.5 hours = 30600s
        assert 30500 < wait_secs < 30700
