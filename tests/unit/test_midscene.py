import json
import pytest
from unittest.mock import MagicMock, patch
from src.midscene.bridge import MidsceneBridge
from src.midscene.handlers import MidsceneHandler

@pytest.fixture
def mock_device():
    device = MagicMock()
    device.serial = "emulator-5554"
    return device

@pytest.fixture
def bridge():
    return MidsceneBridge("emulator-5554")

@pytest.fixture
def handler(mock_device, bridge):
    return MidsceneHandler(mock_device, bridge)

def test_bridge_call_runner(bridge):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout='{"success": true, "page_type": "home"}', stderr="")
        
        res = bridge.detect_page_type("fake_shot.png")
        
        assert res == "home"
        mock_run.assert_called_once()
        # 检查是否调用了 node 和 runner.js
        args = mock_run.call_args[0][0]
        assert "node" in args[0]
        assert "runner.js" in args[1]
        
        # 验证传入参数
        task_args = json.loads(args[2])
        assert task_args["task"] == "detect_page_type"
        assert task_args["screenshot_path"] == "fake_shot.png"

def test_handler_solve_captcha(handler, bridge, mock_device):
    with patch.object(bridge, "handle_captcha", return_value=True) as mock_handle:
        with patch.object(handler, "_take_screenshot", return_value="fake_shot.png"):
            with patch("os.path.exists", return_value=True), patch("os.unlink"):
                success = handler._solve_captcha()
                assert success is True
                mock_handle.assert_called_once_with("fake_shot.png")

def test_handler_handle_visual_detect(handler, bridge, mock_device):
    # 模拟 PageState 为 UNKNOWN
    with patch("src.midscene.handlers.detect_page", return_value="UNKNOWN"):
        with patch.object(handler, "_take_screenshot", return_value="fake_shot.png"):
            with patch.object(bridge, "detect_page_type", return_value="captcha"):
                with patch.object(handler, "_solve_captcha", return_value=True) as mock_solve:
                    with patch("os.path.exists", return_value=True), patch("os.unlink"):
                        success = handler.handle()
                        assert success is True
                        mock_solve.assert_called_once()
