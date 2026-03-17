# 常见问题排查

## 1. 代理连接不通

**症状**: 手机无法上网，或 mitmproxy 无流量

**排查步骤**:

```bash
# 1. 检查 adb reverse 是否生效
adb reverse --list
# 应有: (reverse) tcp:8080 tcp:8080

# 2. 检查手机代理设置
adb shell su -c "settings get global http_proxy"
# 应返回: 127.0.0.1:8080

# 3. 检查 mitmdump 是否在运行
lsof -i :8080

# 4. 测试连通性（手机侧）
adb shell curl -x 127.0.0.1:8080 http://httpbin.org/ip
```

**修复**:
```bash
adb reverse tcp:8080 tcp:8080
adb shell su -c "settings put global http_proxy 127.0.0.1:8080"
```

---

## 2. HTTPS 证书问题

**症状**: mitmproxy 报 TLS handshake 错误

**检查**:
```bash
adb shell ls /data/adb/modules/mitmcert/system/etc/security/cacerts/
# 应有 c8750f0d.0
```

**修复**: 重新安装 mitmproxy 证书到 Magisk 模块，重启手机

---

## 3. 手机断连

**症状**: `adb devices` 无设备

```bash
adb devices
# 应有: f8061f1d  device
adb kill-server && adb start-server && adb devices
```

---

## 4. APP 闪退或卡住

```bash
adb shell am force-stop com.xingin.xhs
adb shell am start -n com.xingin.xhs/.activity.SplashActivity
```

orchestrator 内置 `_recover()` 自动处理：Midscene 视觉检测 → 导航回首页 → 强制重启 APP

---

## 5. 验证码 / 滑块

- orchestrator 通过 Midscene 自动尝试处理
- 自动失败则需手动完成
- 频繁出现说明频率过高，降低 `NOTES_PER_KEYWORD` / 增大 `INTER_KEYWORD_DELAY`

---

## 6. 停止代理后手机无法上网

**必须执行完整清理流程**:
```bash
adb shell su -c "settings put global http_proxy :0"
adb shell su -c "settings delete global http_proxy"
adb shell su -c "settings delete global global_http_proxy_host"
adb shell su -c "settings delete global global_http_proxy_port"
adb shell su -c "settings delete global global_http_proxy_exclusion_list"
adb reverse --remove-all
adb shell su -c "settings put global airplane_mode_on 1"
adb shell su -c "am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true"
sleep 2
adb shell su -c "settings put global airplane_mode_on 0"
adb shell su -c "am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false"
```

漏掉任何一步都可能导致手机无法正常上网。

---

## 7. 数据没有入库

```bash
python3 -c "
from src.storage.db import Database
db = Database('data/xiaohongshu.db')
print('笔记:', db.conn.execute('SELECT COUNT(*) FROM notes').fetchone()[0])
print('评论:', db.conn.execute('SELECT COUNT(*) FROM comments').fetchone()[0])
"
```

**常见原因**: XHS_DB_PATH 环境变量未设、API 格式变化、`_is_target()` 未匹配
