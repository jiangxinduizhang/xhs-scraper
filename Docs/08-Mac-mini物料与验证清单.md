# 08 - Mac mini 物料与验证清单

## 角色定位

Mac mini 作为执行机，负责：

- 拉代码
- 装依赖
- 运行 `mitmproxy`
- 运行 `uiautomator2`
- 调起 Node.js 的 Midscene
- 连接已 root 的 Android 手机

Windows 作为开发机，负责：

- 写代码
- 改文档
- 提交分支
- 推送代码到 fork

## 需要的物料

### 硬件

- Mac mini
- 已 root 的 OnePlus / ColorOS 手机
- USB 数据线
- 稳定供电

### 软件

- Git
- Python 环境
- Node.js 18+
- `adb` / Android platform-tools
- `mitmproxy`
- `uiautomator2`

### 账号与权限

- GitHub fork 仓库权限
- 可用的 SSH key 或 Git 凭据
- 手机 USB 调试权限
- 手机 root 权限

### 手机侧能力

- root 可用
- `su` 可用
- `adb` 可连
- 代理可写
- 证书可安装或可系统化

### 可选增强物料

- MagiskTrustUserCerts
- LSPosed
- Frida / objection

## Mac mini 侧验证清单

### 1. 仓库状态

- `origin` 指向 fork
- 当前分支是 `dev-kpl`
- 工作区干净

### 2. 基础工具

- `git --version`
- `python3 --version`
- `node --version`
- `adb version`
- `mitmdump --version`

### 3. 手机连接

- `adb devices` 能看到设备
- `adb shell su -c id` 返回 root
- `adb shell wm size` 能拿到分辨率
- `uiautomator2` 能连接手机

### 4. 代理链路

- `adb reverse tcp:8080 tcp:8080` 成功
- 手机全局代理可写入
- `mitmdump` 监听 8080
- 手机能正常联网

### 5. 证书链路

- mitmproxy CA 已生成
- 手机已信任证书
- 目标 App 不因证书失败直接断流

### 6. UI 链路

- App 能拉起
- 能截图
- 能进行点击和滑动
- 能返回到首页或目标页

### 7. Midscene 链路

- Node.js 能执行
- Midscene bridge 能启动子进程
- 截图能传入 Node 侧
- 视觉兜底不会卡住主流程

## 验证顺序

1. 先验证 `adb` 和 root
2. 再验证 `mitmproxy`
3. 再验证证书信任
4. 再验证 `uiautomator2`
5. 再验证 Node / Midscene
6. 最后才开始改业务逻辑

## 失败时优先排查

### 代理失败

- `adb reverse` 是否存在
- 手机代理是否写入
- 8080 是否被占用
- mitmdump 是否真在监听

### 证书失败

- 证书是否安装到系统信任链
- App 是否做了 pinning
- 是否需要额外绕过

### UI 失败

- App 包名是否一致
- 页面是否被弹窗挡住
- 控件文本是否和预期一致
- 是否要回退到更稳的页面状态判断

### Node 失败

- Node 是否在 PATH
- 依赖是否装全
- 环境变量是否齐全

## 日常协作流程

### Windows

- 改代码
- 提交到 `dev-kpl`
- 推送到 fork

### Mac mini

- `git pull`
- 跑验证
- 记录结果
- 有问题回到 Windows 再改

## 验证记录建议

每次在 Mac mini 上做验证时，建议记录：

- 时间
- 分支
- App 版本
- 手机状态
- 代理状态
- 抓包结果
- UI 结果
- 结论

