"""
preflight_check 单元测试
mock subprocess 和 socket，无需设备连接
"""
import socket
import subprocess
import pytest
from unittest.mock import MagicMock, patch, call

from src.controller.device import preflight_check
from src import config

# 预检通过时各 subprocess 的返回值
_REVERSE_OK = subprocess.CompletedProcess(
    args=[], returncode=0,
    stdout=f"tcp:{config.PROXY_PORT} tcp:{config.PROXY_PORT}\n",
    stderr="",
)
_PROXY_OK = subprocess.CompletedProcess(
    args=[], returncode=0,
    stdout=f"127.0.0.1:{config.PROXY_PORT}\n",
    stderr="",
)


def _make_run_side_effect(reverse_result, proxy_result):
    """按调用顺序分别返回 adb reverse --list 和 settings get 的结果"""
    return [reverse_result, proxy_result]


# ─── 全部通过 ─────────────────────────────────────────────────

class TestPreflightAllPass:
    def test_no_exception_when_all_ok(self):
        mock_sock = MagicMock()
        with patch("subprocess.run", side_effect=[_REVERSE_OK, _PROXY_OK]) as mock_run, \
             patch("socket.socket", return_value=mock_sock):
            preflight_check()  # 不应抛异常

        assert mock_run.call_count == 2

    def test_logs_pass_message(self, caplog):
        import logging
        mock_sock = MagicMock()
        with patch("subprocess.run", side_effect=[_REVERSE_OK, _PROXY_OK]), \
             patch("socket.socket", return_value=mock_sock), \
             caplog.at_level(logging.INFO, logger="src.controller.device"):
            preflight_check()

        assert "代理预检通过" in caplog.text


# ─── adb reverse 缺少转发 ─────────────────────────────────────

class TestPreflightAdbReverseFail:
    def test_raises_runtime_error_when_no_forward(self):
        reverse_fail = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        with patch("subprocess.run", return_value=reverse_fail):
            with pytest.raises(RuntimeError) as exc_info:
                preflight_check()

        assert "adb reverse" in str(exc_info.value)
        assert str(config.PROXY_PORT) in str(exc_info.value)

    def test_error_message_contains_fix_command(self):
        reverse_fail = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="some other forward\n", stderr=""
        )
        with patch("subprocess.run", return_value=reverse_fail):
            with pytest.raises(RuntimeError) as exc_info:
                preflight_check()

        assert f"tcp:{config.PROXY_PORT}" in str(exc_info.value)


# ─── 设备代理设置错误 ─────────────────────────────────────────

class TestPreflightProxySettingFail:
    def test_raises_when_proxy_not_set(self):
        proxy_fail = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="null\n", stderr=""
        )
        with patch("subprocess.run", side_effect=[_REVERSE_OK, proxy_fail]):
            with pytest.raises(RuntimeError) as exc_info:
                preflight_check()

        assert "代理设置错误" in str(exc_info.value)

    def test_raises_when_proxy_wrong_value(self):
        proxy_wrong = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="192.168.1.1:8080\n", stderr=""
        )
        with patch("subprocess.run", side_effect=[_REVERSE_OK, proxy_wrong]):
            with pytest.raises(RuntimeError) as exc_info:
                preflight_check()

        assert "192.168.1.1:8080" in str(exc_info.value)

    def test_error_message_contains_fix_command(self):
        proxy_fail = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=":0\n", stderr=""
        )
        with patch("subprocess.run", side_effect=[_REVERSE_OK, proxy_fail]):
            with pytest.raises(RuntimeError) as exc_info:
                preflight_check()

        assert f"127.0.0.1:{config.PROXY_PORT}" in str(exc_info.value)


# ─── 本地端口无监听 ───────────────────────────────────────────

class TestPreflightPortFail:
    def test_raises_when_port_not_listening(self):
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = ConnectionRefusedError()
        with patch("subprocess.run", side_effect=[_REVERSE_OK, _PROXY_OK]), \
             patch("socket.socket", return_value=mock_sock):
            with pytest.raises(RuntimeError) as exc_info:
                preflight_check()

        assert "mitmdump" in str(exc_info.value)

    def test_raises_on_os_error(self):
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = OSError("timeout")
        with patch("subprocess.run", side_effect=[_REVERSE_OK, _PROXY_OK]), \
             patch("socket.socket", return_value=mock_sock):
            with pytest.raises(RuntimeError) as exc_info:
                preflight_check()

        assert str(config.PROXY_PORT) in str(exc_info.value)

    def test_error_message_contains_port(self):
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = ConnectionRefusedError()
        with patch("subprocess.run", side_effect=[_REVERSE_OK, _PROXY_OK]), \
             patch("socket.socket", return_value=mock_sock):
            with pytest.raises(RuntimeError) as exc_info:
                preflight_check()

        assert str(config.PROXY_PORT) in str(exc_info.value)
