/**
 * Midscene 异常处理运行器
 * 接收任务描述，通过视觉理解操作设备
 */
const fs = require('fs');
const { execSync } = require('child_process');

async function main() {
    // 检查环境变量
    if (!process.env.ANTHROPIC_API_KEY) {
        console.log(JSON.stringify({ 
            success: false, 
            error: "ANTHROPIC_API_KEY environment variable is not set" 
        }));
        process.exit(0); // 即使失败也退出 0，让 Python 解析 JSON 错误
    }

    // 检查参数
    if (process.argv.length < 3) {
        console.log(JSON.stringify({ success: false, error: "Missing arguments" }));
        process.exit(0);
    }

    const args = JSON.parse(process.argv[2]);
    const { task, screenshot_path, device_serial } = args;

    // 加载截图作为视觉上下文
    if (!fs.existsSync(screenshot_path)) {
        console.error(JSON.stringify({ success: false, error: `Screenshot not found: ${screenshot_path}` }));
        process.exit(1);
    }
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
        } else {
            result = { success: false, error: `Unknown task: ${task}` };
        }

        console.log(JSON.stringify(result));
    } catch (err) {
        console.log(JSON.stringify({ success: false, error: err.message }));
        process.exit(1);
    }
}

async function handleCaptcha(screenshotBase64, deviceSerial) {
    // 这里应该是 Midscene 或直接调用 LLM Vision
    // 此处实现简化版：使用 Claude API 分析截图
    const { Anthropic } = require('@anthropic-ai/sdk');
    const client = new Anthropic({
        apiKey: process.env.ANTHROPIC_API_KEY
    });

    const response = await client.messages.create({
        model: 'claude-3-5-sonnet-20240620',
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
                    text: '这是小红书APP的截图。请分析：1. 是否存在验证码？2. 是什么类型（滑块/图形/短信）？3. 如果是滑块，滑块起点和终点的大致坐标是什么（以屏幕宽高百分比表示，范围 0.0-1.0）？返回 JSON 格式：{"has_captcha": boolean, "type": "slider"|"image"|"other", "coordinates": {"start_x": number, "start_y": number, "end_x": number}}'
                }
            ]
        }]
    });

    // 提取 JSON
    const text = response.content[0].text;
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) return { success: false, error: "No JSON found in response" };
    
    const analysis = JSON.parse(jsonMatch[0]);
    if (!analysis.has_captcha) {
        return { success: true, action: 'no_captcha' };
    }

    if (analysis.type === 'slider') {
        const { start_x, start_y, end_x } = analysis.coordinates;
        // 获取屏幕分辨率
        const screenInfo = execSync(`adb -s ${deviceSerial} shell wm size`).toString();
        const [w, h] = screenInfo.match(/(\d+)x(\d+)/)[0].split('x').map(Number);
        
        const x1 = Math.round(start_x * w);
        const y1 = Math.round(start_y * h);
        const x2 = Math.round(end_x * w);
        
        // 执行 ADB 滑动
        const cmd = `adb -s ${deviceSerial} shell input swipe ${x1} ${y1} ${x2} ${y1} 500`;
        execSync(cmd);
        return { success: true, action: 'slider_swiped' };
    }

    return { success: false, action: 'manual_required', type: analysis.type };
}

async function dismissDialog(screenshotBase64, deviceSerial) {
    const { Anthropic } = require('@anthropic-ai/sdk');
    const client = new Anthropic({
        apiKey: process.env.ANTHROPIC_API_KEY
    });

    const response = await client.messages.create({
        model: 'claude-3-5-sonnet-20240620',
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
                    text: '这是小红书APP截图。是否存在非预期的弹窗、广告、对话框或评价提醒？如果有，找到"关闭"、"取消"或"我知道了"按钮的大致坐标（以屏幕宽高百分比表示，0.0-1.0）。返回 JSON: {"has_dialog": boolean, "button_x": number, "button_y": number}'
                }
            ]
        }]
    });

    const text = response.content[0].text;
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) return { success: false, error: "No JSON found in response" };
    const result = JSON.parse(jsonMatch[0]);
    
    if (!result.has_dialog) {
        return { success: true, action: 'no_dialog' };
    }

    // 点击关闭按钮
    const screenInfo = execSync(`adb -s ${deviceSerial} shell wm size`).toString();
    const [w, h] = screenInfo.match(/(\d+)x(\d+)/)[0].split('x').map(Number);
    const tap_x = Math.round(result.button_x * w);
    const tap_y = Math.round(result.button_y * h);
    execSync(`adb -s ${deviceSerial} shell input tap ${tap_x} ${tap_y}`);

    return { success: true, action: 'dialog_dismissed', coord: [tap_x, tap_y] };
}

async function detectPageType(screenshotBase64) {
    const { Anthropic } = require('@anthropic-ai/sdk');
    const client = new Anthropic({
        apiKey: process.env.ANTHROPIC_API_KEY
    });

    const response = await client.messages.create({
        model: 'claude-3-5-sonnet-20240620',
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
                    text: '这是小红书APP截图。当前页面类型是什么？选项：home (首页/发现), search_result (搜索列表), note_detail (笔记正文), comment (评论区), login (登录页), captcha (验证码), unknown。只返回一个词。'
                }
            ]
        }]
    });

    return { success: true, page_type: response.content[0].text.trim().toLowerCase() };
}

async function recoverToFeed(screenshotBase64, deviceSerial) {
    // 递归尝试返回，由于这是 JS 脚本运行，逻辑相对独立
    // 这里仅做一次 BACK 并检测
    execSync(`adb -s ${deviceSerial} shell input keyevent 4`);
    return { success: true, action: 'back_pressed' };
}

main().catch(err => {
    console.error(JSON.stringify({ success: false, error: err.message }));
    process.exit(1);
});
