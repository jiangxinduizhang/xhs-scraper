# 06 - Midscene 异常处理

## Midscene 接入方式

### 方案：Python 调用 Node.js 子进程（推荐）

Midscene 是 Node.js 生态，主控流程是 Python (uiautomator2)。
通过子进程调用 Midscene CLI，传递截图和任务描述，获取执行结果。

```
Python Orchestrator
        │
        │ (异常检测)
        ▼
MidsceneBridge.handle(task_desc, screenshot)
        │
        │ subprocess.run(node midscene_runner.js ...)
        ▼
Node.js Midscene Runner
        │
        │ (视觉理解 + ADB 操作)
        ▼
返回结果给 Python
```

### 目录结构

```
src/midscene/
├── bridge.py           # Python 侧桥接器
├── runner.js           # Node.js 侧 Midscene 执行器
├── package.json
└── handlers.py         # 具体异常场景处理器
```

### src/midscene/runner.js

```javascript
/**
 * Midscene 异常处理运行器
 * 接收任务描述，通过视觉理解操作设备
 */
const { Midscene } = require('@midscene/web');
const fs = require('fs');

async function main() {
    const args = JSON.parse(process.argv[2]);
    const { task, screenshot_path, device_serial } = args;

    // 连接 ADB 设备（通过 @u2/driver 或直接调用 adb）
    const { execSync } = require('child_process');

    // 加载截图作为视觉上下文
    const screenshotBase64 = fs.readFileSync(screenshot_path, 'base64');

    try {
        let result = { success: false, action: null };

        if (task === 'handle_captcha') {
            result = await handleCaptcha(screenshotBase64, device_serial);
        } else if (task === 'dismiss_dialog') {
            result = await dismissDialog(screenshotBase64, device_serial);
        } else if (task === 'detect_page_type') {
            result = await detectPageType(screenshotBase64);
        } else if (task === 'recover_to_feed') {
            result = await recoverToFeed(screenshotBase64, device_serial);
        }

        console.log(JSON.stringify(result));
    } catch (err) {
        console.log(JSON.stringify({ success: false, error: err.message }));
        process.exit(1);
    }
}

async function handleCaptcha(screenshotBase64, deviceSerial) {
    // 通过 Claude Vision 分析验证码类型和操作方式
    const { Anthropic } = require('@anthropic-ai/sdk');
    const client = new Anthropic();

    const response = await client.messages.create({
        model: 'claude-opus-4-5',
        max_tokens: 1024,
        messages: [{
            role: 'user',
            content: [
                {
                    type: 'image',
                    source: { type: 'base64', media_type: 'image/png', data: screenshotBase64 }
                },
                {
                    type: 'text',
                    text: '这是小红书APP的截图。请分析：1. 是否存在验证码？2. 是什么类型（滑块/图形/短信）？3. 如果是滑块，滑块起点和终点的大致坐标是什么（以屏幕宽高百分比表示）？返回 JSON 格式。'
                }
            ]
        }]
    });

    const analysis = JSON.parse(response.content[0].text);
    if (!analysis.has_captcha) {
        return { success: true, action: 'no_captcha' };
    }

    // 根据分析结果执行操作
    const { execSync } = require('child_process');
    if (analysis.type === 'slider') {
        const { start_x, start_y, end_x } = analysis.coordinates;
        // 执行 ADB 滑动
        const cmd = `adb -s ${deviceSerial} shell input swipe ${start_x} ${start_y} ${end_x} ${start_y} 500`;
        execSync(cmd);
        return { success: true, action: 'slider_swiped' };
    }

    return { success: false, action: 'manual_required', type: analysis.type };
}

async function dismissDialog(screenshotBase64, deviceSerial) {
    const { Anthropic } = require('@anthropic-ai/sdk');
    const client = new Anthropic();

    const response = await client.messages.create({
        model: 'claude-opus-4-5',
        max_tokens: 512,
        messages: [{
            role: 'user',
            content: [
                {
                    type: 'image',
                    source: { type: 'base64', media_type: 'image/png', data: screenshotBase64 }
                },
                {
                    type: 'text',
                    text: '这是小红书APP截图。是否存在弹窗/对话框？如果有，"关闭"或"取消"按钮的大致坐标是什么（屏幕宽高百分比）？返回 JSON: {has_dialog, button_x, button_y}'
                }
            ]
        }]
    });

    const result = JSON.parse(response.content[0].text);
    if (!result.has_dialog) {
        return { success: true, action: 'no_dialog' };
    }

    // 点击关闭按钮
    const { execSync } = require('child_process');
    const screenInfo = execSync(`adb -s ${deviceSerial} shell wm size`).toString();
    const [w, h] = screenInfo.match(/(\d+)x(\d+)/)[0].split('x').map(Number);
    const tap_x = Math.round(result.button_x * w);
    const tap_y = Math.round(result.button_y * h);
    execSync(`adb -s ${deviceSerial} shell input tap ${tap_x} ${tap_y}`);

    return { success: true, action: 'dialog_dismissed', coord: [tap_x, tap_y] };
}

async function detectPageType(screenshotBase64) {
    const { Anthropic } = require('@anthropic-ai/sdk');
    const client = new Anthropic();

    const response = await client.messages.create({
        model: 'claude-haiku-4-5-20251001',   // 用更快的模型做页面检测
        max_tokens: 256,
        messages: [{
            role: 'user',
            content: [
                {
                    type: 'image',
                    source: { type: 'base64', media_type: 'image/png', data: screenshotBase64 }
                },
                {
                    type: 'text',
                    text: '这是小红书截图。当前页面类型是什么？选项：home/search_result/note_detail/comment/login/captcha/unknown。只返回一个词。'
                }
            ]
        }]
    });

    return { success: true, page_type: response.content[0].text.trim() };
}

async function recoverToFeed(screenshotBase64, deviceSerial) {
    // 多次按返回键直到回到首页
    const { execSync } = require('child_process');
    for (let i = 0; i < 5; i++) {
        const result = await detectPageType(screenshotBase64);
        if (result.page_type === 'home') {
            return { success: true, action: 'recovered' };
        }
        execSync(`adb -s ${deviceSerial} shell input keyevent 4`);  // BACK key
        await new Promise(r => setTimeout(r, 1000));
        // 重新截图
        execSync(`adb -s ${deviceSerial} shell screencap -p /sdcard/tmp.png`);
        execSync(`adb -s ${deviceSerial} pull /sdcard/tmp.png /tmp/midscene_screenshot.png`);
        screenshotBase64 = fs.readFileSync('/tmp/midscene_screenshot.png', 'base64');
    }
    return { success: false, action: 'recovery_failed' };
}

main().catch(console.error);
```

---

## 触发条件定义

### src/midscene/handlers.py

```python
"""
Midscene 触发条件定义和调用封装
"""
import subprocess
import json
import logging
import time
import uiautomator2 as u2
from controller.state import PageState, detect_page

logger = logging.getLogger(__name__)

# 触发 Midscene 的条件
TRIGGER_CONDITIONS = {
    "operation_timeout": 10.0,     # uiautomator2 操作超时（秒）
    "page_stuck_timeout": 15.0,    # 页面长时间无变化
    "unexpected_dialog": True,     # 检测到未知弹窗
    "captcha_detected": True,      # 检测到验证码
}


class MidsceneBridge:
    def __init__(self, device: u2.Device = None, device_serial: str = None):
        self.device = device
        self.device_serial = device_serial or self._get_serial(device)

    def _get_serial(self, device: u2.Device) -> str:
        if device is None:
            return ""
        return device.serial

    def _take_screenshot(self) -> str:
        """截图并保存到临时文件"""
        path = "/tmp/midscene_screenshot.png"
        if self.device:
            self.device.screenshot(path)
        return path

    def _call_runner(self, task: str, extra: dict = None) -> dict:
        """调用 Node.js Midscene Runner"""
        screenshot_path = self._take_screenshot()
        args = {
            "task": task,
            "screenshot_path": screenshot_path,
            "device_serial": self.device_serial,
            **(extra or {}),
        }

        try:
            result = subprocess.run(
                ["node", "src/midscene/runner.js", json.dumps(args)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.error(f"Midscene runner 失败: {result.stderr}")
                return {"success": False, "error": result.stderr}

            return json.loads(result.stdout.strip())
        except subprocess.TimeoutExpired:
            logger.error("Midscene runner 超时")
            return {"success": False, "error": "timeout"}
        except json.JSONDecodeError as e:
            logger.error(f"Midscene 返回解析失败: {e}")
            return {"success": False, "error": "parse_error"}

    def handle_captcha(self) -> bool:
        """处理验证码"""
        logger.info("Midscene: 处理验证码")
        result = self._call_runner("handle_captcha")
        return result.get("success", False)

    def dismiss_dialog(self) -> bool:
        """关闭未知弹窗"""
        logger.info("Midscene: 关闭弹窗")
        result = self._call_runner("dismiss_dialog")
        return result.get("success", False)

    def detect_page_type(self) -> str:
        """视觉检测当前页面类型"""
        result = self._call_runner("detect_page_type")
        return result.get("page_type", "unknown")

    def recover_to_feed(self) -> bool:
        """恢复到首页/列表页"""
        logger.info("Midscene: 尝试恢复到首页")
        result = self._call_runner("recover_to_feed")
        return result.get("success", False)
```

---

## 与 uiautomator2 主流程的集成方式

### 包装器模式（推荐）

在 uiautomator2 的关键操作上套一层异常捕获 + Midscene 兜底：

```python
# src/controller/safe_actions.py
"""
带 Midscene 兜底的安全操作封装
"""
import logging
import time
from controller.actions import XHSActions
from controller.state import PageState, detect_page
from midscene.handlers import MidsceneBridge

logger = logging.getLogger(__name__)


class SafeActions:
    def __init__(self, device, actions: XHSActions, bridge: MidsceneBridge):
        self.device = device
        self.actions = actions
        self.bridge = bridge

    def safe_tap(self, element, timeout: float = 10.0) -> bool:
        """带异常处理的点击操作"""
        try:
            if element.exists(timeout=timeout):
                element.click()
                return True
            else:
                # 元素未找到，触发 Midscene 检测
                logger.warning("元素未找到，触发 Midscene 检测")
                return self._handle_unexpected_state()
        except Exception as e:
            logger.error(f"点击异常: {e}")
            return self._handle_unexpected_state()

    def _handle_unexpected_state(self) -> bool:
        """处理非预期状态"""
        # 1. 检测页面类型
        page_state = detect_page(self.device)

        if page_state == PageState.CAPTCHA:
            logger.info("检测到验证码，调用 Midscene 处理")
            success = self.bridge.handle_captcha()
            if success:
                time.sleep(2)
                return True

        elif page_state == PageState.UNKNOWN_DIALOG:
            logger.info("检测到未知弹窗，调用 Midscene 处理")
            success = self.bridge.dismiss_dialog()
            if success:
                time.sleep(1)
                return True

        else:
            # 页面状态未知，用 Midscene 视觉判断
            page_type = self.bridge.detect_page_type()
            logger.info(f"Midscene 判断页面类型: {page_type}")

            if page_type in ("captcha",):
                return self.bridge.handle_captcha()
            elif page_type in ("unknown",):
                return self.bridge.dismiss_dialog()

        return False
```

---

## 降级逻辑

### 异常处理流程图

```
uiautomator2 操作失败 / 超时
        │
        ▼
detect_page() 判断页面状态
        │
        ├── CAPTCHA → Midscene 处理验证码
        │       │
        │       ├── 成功 → 等待 2s → 恢复主流程
        │       └── 失败 → 切换账号 / 暂停任务
        │
        ├── UNKNOWN_DIALOG → Midscene 关闭弹窗
        │       │
        │       ├── 成功 → 恢复主流程
        │       └── 失败 → 多次返回 → 回到首页
        │
        ├── LOGIN → 暂停任务，发送告警，等待人工处理
        │
        └── UNKNOWN → Midscene 视觉判断
                │
                ├── 可识别 → 对应处理
                └── 不可识别 → recover_to_feed() → 重试任务
```

### 恢复主流程代码

```python
# src/orchestrator.py 中的异常恢复逻辑

def _execute_with_recovery(self, func, *args, max_retries=2, **kwargs):
    """带恢复的任务执行包装器"""
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"第 {attempt+1} 次尝试失败: {e}")

            if attempt == max_retries:
                logger.error("达到最大重试次数，跳过")
                return None

            # 调用 Midscene 尝试恢复
            page_state = detect_page(self.device)
            logger.info(f"当前页面状态: {page_state}")

            if page_state == PageState.CAPTCHA:
                self.bridge.handle_captcha()
                time.sleep(3)
            elif page_state in (PageState.UNKNOWN, PageState.UNKNOWN_DIALOG):
                recovered = self.bridge.recover_to_feed()
                if not recovered:
                    # 彻底恢复：重启 APP
                    launch_app(self.device, fresh_start=True)
                    time.sleep(3)
            else:
                time.sleep(2)
```

---

## Midscene 相关配置

### src/midscene/package.json

```json
{
  "name": "xhs-midscene",
  "version": "1.0.0",
  "dependencies": {
    "@anthropic-ai/sdk": "^0.30.0"
  }
}
```

### 环境变量

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...

# Midscene 调用配置
MIDSCENE_TIMEOUT=60          # 单次调用超时（秒）
MIDSCENE_MODEL=claude-opus-4-5  # 验证码等复杂任务使用 Opus
MIDSCENE_FAST_MODEL=claude-haiku-4-5-20251001  # 页面检测等简单任务使用 Haiku
```

---

## 注意事项

1. **成本控制**：Midscene 每次调用 Claude Vision API 会产生费用。
   触发条件要设置合理阈值，避免频繁调用。
   建议：仅在 uiautomator2 连续 2 次失败后才触发 Midscene。

2. **超时设置**：Node.js runner 超时设为 60s，
   单次 Midscene 处理失败不应阻塞主流程超过 2 分钟。

3. **降级保证**：Midscene 处理失败时，主流程应能优雅降级（跳过当前笔记），
   而不是整个系统崩溃。

4. **日志记录**：每次触发 Midscene 时记录详细日志（截图路径、触发原因、处理结果），
   便于后续分析和优化触发策略。
