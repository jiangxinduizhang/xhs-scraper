# 代理操作指南

## 启动抓包

```bash
# 1. 建立 USB 端口转发（手机 127.0.0.1:8080 → Mac 8080）
adb reverse tcp:8080 tcp:8080

# 2. 设置手机全局代理（需 root）
adb shell su -c "settings put global http_proxy 127.0.0.1:8080"

# 3. 启动 mitmproxy
XHS_DB_PATH="data/xiaohongshu.db" mitmdump -p 8080 -s src/proxy/addon.py
```

## 停止抓包 & 恢复手机网络

```bash
# 1. 杀掉 mitmproxy 进程
pkill -f mitmdump

# 2. 删除手机全局代理设置（否则手机断网）
adb shell su -c "settings delete global http_proxy"

# 3. 清除 USB 端口转发
adb reverse --remove-all
```

一行版：
```bash
pkill -f mitmdump; adb shell su -c "settings delete global http_proxy"; adb reverse --remove-all
```

## 为什么需要这三步

| 步骤 | 不做的后果 |
|------|-----------|
| 杀 mitmdump | 8080 端口占用，下次启动失败 |
| 删手机代理 | 手机所有 HTTP 流量转发到不存在的代理，**完全断网** |
| 清 USB 转发 | 残留端口映射，拔线后无影响但保持清洁 |

## 验证手机网络已恢复

```bash
# 确认代理已清除（应返回 "null"）
adb shell settings get global http_proxy

# 确认手机能上网
adb shell ping -c 1 baidu.com
```
