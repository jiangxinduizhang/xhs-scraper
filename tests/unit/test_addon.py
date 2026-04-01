"""
mitmproxy Addon 单元测试
通过 mock 注入 db/parser，无需真实网络或 mitmproxy 进程
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from src.proxy.addon import XHSAddon
from src import config


def make_addon() -> XHSAddon:
    """创建已注入 mock db/parser 的 addon（跳过懒加载）"""
    addon = XHSAddon()
    addon._db = MagicMock()
    addon._parser = MagicMock()
    return addon


def make_flow(host: str, path: str, body=None) -> MagicMock:
    flow = MagicMock()
    flow.request.host = host
    flow.request.path = path
    flow.request.url = f"https://{host}{path}"
    flow.response.get_text.return_value = json.dumps(body or {})
    return flow


# ─── _is_target ─────────────────────────────────────────────

class TestIsTarget:
    def test_all_configured_paths_are_targeted(self):
        """TARGET_PATHS 中每条路径配合任意 TARGET_HOST 都应命中"""
        addon = XHSAddon()
        any_host = next(iter(config.TARGET_HOSTS))
        for path in config.TARGET_PATHS:
            flow = make_flow(any_host, path + "?cursor=abc")
            assert addon._is_target(flow) is True, f"应命中: {path}"

    def test_all_target_hosts_accepted(self):
        """所有 TARGET_HOSTS 都应被接受"""
        addon = XHSAddon()
        for host in config.TARGET_HOSTS:
            flow = make_flow(host, config.TARGET_PATHS[0])
            assert addon._is_target(flow) is True, f"host 应被接受: {host}"

    def test_wrong_host_rejected(self):
        addon = XHSAddon()
        flow = make_flow("www.google.com", config.TARGET_PATHS[0])
        assert addon._is_target(flow) is False

    def test_correct_host_unknown_path_rejected(self):
        addon = XHSAddon()
        any_host = next(iter(config.TARGET_HOSTS))
        flow = make_flow(any_host, "/api/sns/v1/unknown/endpoint")
        assert addon._is_target(flow) is False

    def test_path_prefix_match_with_query_string(self):
        """带 query string 的路径也应命中"""
        addon = XHSAddon()
        flow = make_flow("so.xiaohongshu.com", "/api/sns/v10/search/notes?keyword=穿搭&page=2")
        assert addon._is_target(flow) is True


# ─── response ───────────────────────────────────────────────

class TestAddonResponse:
    def test_calls_parser_and_saves_items(self):
        addon = make_addon()
        mock_item = MagicMock()
        addon._parser.parse.return_value = [mock_item]

        flow = make_flow(config.TARGET_HOST, config.TARGET_PATHS[0], {"data": {"items": []}})
        with patch("os.getenv", return_value="false"):
            addon.response(flow)

        addon._parser.parse.assert_called_once()
        addon._db.save.assert_called_once_with([mock_item], source="search")

    def test_skips_non_target_flow(self):
        addon = make_addon()
        flow = make_flow("www.other.com", "/api/v1/something")
        addon.response(flow)
        addon._parser.parse.assert_not_called()
        addon._db.save.assert_not_called()

    def test_no_save_when_parse_returns_empty(self):
        addon = make_addon()
        addon._parser.parse.return_value = []
        flow = make_flow(config.TARGET_HOST, config.TARGET_PATHS[0], {"data": {}})
        with patch("os.getenv", return_value="false"):
            addon.response(flow)
        addon._parser.parse.assert_called_once()
        addon._db.save.assert_not_called()

    def test_handles_invalid_json_gracefully(self):
        addon = make_addon()
        flow = make_flow(config.TARGET_HOST, config.TARGET_PATHS[0])
        flow.response.get_text.return_value = "{{invalid json{{{"
        # 不应抛出异常
        addon.response(flow)
        addon._parser.parse.assert_not_called()

    def test_handles_parser_exception_gracefully(self):
        addon = make_addon()
        addon._parser.parse.side_effect = RuntimeError("解析炸了")
        flow = make_flow(config.TARGET_HOST, config.TARGET_PATHS[0], {"data": {}})
        with patch("os.getenv", return_value="false"):
            # 不应抛出异常，日志记录错误即可
            addon.response(flow)
        addon._db.save.assert_not_called()

    def test_saves_fixture_when_env_set(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SAVE_FIXTURE", "true")
        monkeypatch.chdir(tmp_path)

        addon = make_addon()
        addon._parser.parse.return_value = []
        flow = make_flow(config.TARGET_HOST, config.TARGET_PATHS[0], {"key": "value"})
        addon.response(flow)

        import os
        raw_files = list((tmp_path / "data" / "raw").glob("*.jsonl"))
        assert len(raw_files) == 1

        content = raw_files[0].read_text()
        assert '"key": "value"' in content


# ─── source 字段设置 ──────────────────────────────────────────

class TestSourceDetection:
    def test_search_source(self):
        addon = make_addon()
        mock_item = MagicMock()
        mock_item.source = ""
        addon._parser.parse.return_value = [mock_item]

        flow = make_flow("so.xiaohongshu.com", "/api/sns/v10/search/notes?keyword=穿搭", {"data": {}})
        with patch("os.getenv", return_value="false"):
            addon.response(flow)

        assert mock_item.source == "search"
        addon._db.save.assert_called_once()
        _, kwargs = addon._db.save.call_args
        assert kwargs["source"] == "search"

    def test_homefeed_source(self):
        addon = make_addon()
        mock_item = MagicMock()
        mock_item.source = ""
        addon._parser.parse.return_value = [mock_item]

        flow = make_flow("rec.xiaohongshu.com", "/api/sns/v6/homefeed", {"data": []})
        with patch("os.getenv", return_value="false"):
            addon.response(flow)

        assert mock_item.source == "homefeed"

    def test_detailfeed_source(self):
        addon = make_addon()
        mock_item = MagicMock()
        mock_item.source = ""
        addon._parser.parse.return_value = [mock_item]

        flow = make_flow("edith.xiaohongshu.com", "/api/sns/v1/note/detailfeed", {"data": {}})
        with patch("os.getenv", return_value="false"):
            addon.response(flow)

        assert mock_item.source == "detailfeed"

    def test_comments_source(self):
        addon = make_addon()
        mock_item = MagicMock()
        mock_item.source = ""
        addon._parser.parse.return_value = [mock_item]

        flow = make_flow("edith.xiaohongshu.com", "/api/sns/v5/note/comment/list", {"data": {}})
        with patch("os.getenv", return_value="false"):
            addon.response(flow)

        assert mock_item.source == "comments"


# ─── _detect_source 静态方法 ─────────────────────────────────

class TestDetectSource:
    def test_search(self):
        assert XHSAddon._detect_source("/api/sns/v10/search/notes") == "search"

    def test_homefeed(self):
        assert XHSAddon._detect_source("/api/sns/v6/homefeed") == "homefeed"

    def test_detailfeed(self):
        assert XHSAddon._detect_source("/api/sns/v1/note/detailfeed") == "detailfeed"

    def test_comments(self):
        assert XHSAddon._detect_source("/api/sns/v5/note/comment/list") == "comments"

    def test_unknown(self):
        assert XHSAddon._detect_source("/api/something/else") == ""

    def test_index(self):
        assert XHSAddon._detect_source("/w1/api/index.php") == "index"

    def test_market_sentiment(self):
        assert XHSAddon._detect_source("/w1/api/index.php", {"BaceFaceList": []}) == "market_sentiment"


# ─── 懒加载属性 ──────────────────────────────────────────────

class TestLazyInit:
    def test_db_not_created_on_import(self):
        """addon 实例化时不应立即创建 DB"""
        addon = XHSAddon()
        assert addon._db is None

    def test_parser_not_created_on_import(self):
        addon = XHSAddon()
        assert addon._parser is None

    def test_db_created_on_first_access(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XHS_DB_PATH", str(tmp_path / "test.db"))
        addon = XHSAddon()
        _ = addon.db  # 触发懒加载
        assert addon._db is not None

    def test_parser_created_on_first_access(self):
        from src.proxy.parser import XHSParser
        addon = XHSAddon()
        _ = addon.parser
        assert isinstance(addon._parser, XHSParser)
