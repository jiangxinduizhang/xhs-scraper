#!/bin/bash
# 启动 mitmproxy 拦截小红书数据
# 注意：必须使用系统 Python 调用，不能用 binary 版 mitmdump（缺少 sqlite3）
set -e

cd "$(dirname "$0")/.."

PROXY_PORT=8080
PROXY_HOST=$(ifconfig en0 2>/dev/null | grep "inet " | awk '{print $2}')

if [ -z "$PROXY_HOST" ]; then
    PROXY_HOST=$(ipconfig getifaddr en0 2>/dev/null || echo "127.0.0.1")
fi

echo "=== mitmproxy 启动 ==="
echo "代理地址: $PROXY_HOST:$PROXY_PORT"
echo "请在手机 WiFi 设置中配置上述代理"
echo ""

# 通过 ADB 设置手机代理（可选，需设备已连接）
if adb devices | grep -q "device$"; then
    adb shell settings put global http_proxy "$PROXY_HOST:$PROXY_PORT" 2>/dev/null && \
        echo "已通过 ADB 自动设置手机代理" || true
fi

# 启动代理（使用系统 Python 确保 sqlite3 等模块可用）
trap 'echo "正在清除代理..."; adb shell settings put global http_proxy :0 2>/dev/null; exit 0' INT TERM

mitmdump -p $PROXY_PORT -s src/proxy/addon.py
