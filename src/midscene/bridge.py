"""
Midscene 桥接器
Python 调用 Node.js Midscene Runner
"""
import os
import json
import subprocess
import logging
import tempfile
from typing import Optional, Dict, Any

log = logging.getLogger(__name__)

class MidsceneBridge:
    def __init__(self, device_serial: str, node_path: str = "node"):
        self.device_serial = device_serial
        self.node_path = node_path
        self.runner_js = os.path.join(os.path.dirname(__file__), "runner.js")

    def _call_runner(self, task: str, screenshot_path: str, extra: Optional[Dict] = None) -> Dict[str, Any]:
        """执行 Node.js 子进程"""
        args = {
            "task": task,
            "screenshot_path": screenshot_path,
            "device_serial": self.device_serial,
            **(extra or {})
        }

        try:
            # 确保 ANTHROPIC_API_KEY 存在
            if not os.getenv("ANTHROPIC_API_KEY"):
                log.warning("ANTHROPIC_API_KEY not found in environment")

            result = subprocess.run(
                [self.node_path, self.runner_js, json.dumps(args)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                log.error(f"Midscene runner failed (exit {result.returncode}): {result.stderr}")
                return {"success": False, "error": result.stderr}

            # 尝试解析 stdout 中的 JSON
            output = result.stdout.strip()
            try:
                # 过滤掉非 JSON 输出（如果有日志）
                json_start = output.find('{')
                if json_start != -1:
                    output = output[json_start:]
                return json.loads(output)
            except json.JSONDecodeError:
                log.error(f"Failed to parse Midscene output: {output}")
                return {"success": False, "error": "invalid_json", "raw": output}

        except subprocess.TimeoutExpired:
            log.error("Midscene runner timed out")
            return {"success": False, "error": "timeout"}
        except Exception as e:
            log.error(f"Midscene bridge error: {e}")
            return {"success": False, "error": str(e)}

    def handle_captcha(self, screenshot_path: str) -> bool:
        """视觉处理验证码"""
        res = self._call_runner("handle_captcha", screenshot_path)
        return res.get("success", False)

    def dismiss_dialog(self, screenshot_path: str) -> bool:
        """视觉关闭弹窗"""
        res = self._call_runner("dismiss_dialog", screenshot_path)
        return res.get("success", False)

    def detect_page_type(self, screenshot_path: str) -> str:
        """视觉识别页面类型"""
        res = self._call_runner("detect_page_type", screenshot_path)
        return res.get("page_type", "unknown")

    def recover_to_feed(self, screenshot_path: str) -> bool:
        """视觉辅助恢复"""
        res = self._call_runner("recover_to_feed", screenshot_path)
        return res.get("success", False)
