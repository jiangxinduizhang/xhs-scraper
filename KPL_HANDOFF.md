# 开盘啦迁移接续页

当前状态：

- 仓库远程：`origin = git@github.com:jiangxinduizhang/xhs-scraper.git`
- 当前分支：`dev-kpl`
- 开发方式：Mac mini 单机开发 + 真机验证
- 当前目标：验证当前框架能否适配 `开盘啦`，先做最小闭环，不做全量重构
- 开盘啦正式适配包：`src/apps/kaipanla/`

## 一句话结论

这不是直接复用小红书业务逻辑，而是复用“UI 控制 + 抓包 + 入库 + 异常兜底”的框架骨架，再为 `开盘啦` 重写适配层。

当前最优先的执行入口：

- `python3 -m src.apps.kaipanla --section env`
- 先看 Mac mini 环境是否就绪，再进入画像和抓包

## 当前已确认的关键点

1. `xhs-scraper` 对小红书是强绑定实现，不能直接拿来抓别的 App。
2. `Mac mini + 已 root 的 OnePlus` 足以作为唯一执行环境。
3. 迁移时最容易踩坑的是：
   - 误把小红书 host/path/package 迁移过去
   - 先大改框架而不是先做最小验证
   - 在没有抓包证据前硬写 parser
   - 忘记清理代理，导致手机断网

## 必须记住的闭坑点

1. 不要用 resourceId 做小红书式迁移假设，目标 App 的页面结构要重新确认。
2. 不要先写大量代码，先验证能否看到真实请求。
3. 不要假设 `mitmproxy` 一定能解密，先确认证书链路和 pinning。
4. 不要假设目标 App 是内容流，金融类 App 常常是行情、图表、WebSocket、加密协议。
5. 不要忘记代理退出流程，否则手机可能会“看起来像断网”。

## 迁移方案顺序

1. Mac mini 环境就绪检查
2. 目标 App 画像确认
3. 抓包可见性验证
4. UI 可控性验证
5. 最小闭环打通
6. 再扩字段和页面

## 最小闭环定义

必须至少完成以下链路：

1. 启动 App
2. 进入一个目标页面
3. 触发一个真实请求
4. `mitmproxy` 拦截到响应
5. parser 解析出结构化记录
6. 写入 SQLite
7. 导出成功

## Mac mini 侧需要验证的物料

- `git`
- `Python`
- `Node.js`
- `adb`
- `mitmproxy`
- `uiautomator2`
- 已 root 手机
- USB 数据线
- 可用的证书信任链

## 当前文档入口

- [总览索引](Docs/00-%E6%80%BB%E8%A7%88%E7%B4%A2%E5%BC%95.md)
- [单机方案](Docs/07-开盘啦迁移方案.md)
- [Mac mini 物料与验证清单](Docs/08-Mac-mini物料与验证清单.md)
- [AI 自动闭环方案 - 项目内部建设](Docs/09-AI自动闭环方案.md)
- [AI 对外暴露与工具接入方案](Docs/10-AI对外暴露与工具接入方案.md)
- [开盘啦适配说明](Docs/kaipanla/README.md)

后续所有项目内部建设，优先按 [Docs/09-AI自动闭环方案.md](Docs/09-AI%E8%87%AA%E5%8A%A8%E9%97%AD%E7%8E%AF%E6%96%B9%E6%A1%88.md) 中的“验收标准 / 反省标准”执行。

外部 AI Agent 的接入方式按 [Docs/10-AI对外暴露与工具接入方案.md](Docs/10-AI%E5%AF%B9%E5%A4%96%E6%9A%B4%E9%9C%B2%E4%B8%8E%E5%B7%A5%E5%85%B7%E6%8E%A5%E5%85%A5%E6%96%B9%E6%A1%88.md) 执行，只通过 skill / tool / script / 产物交互，不读取仓库源码作为接入前提。

外部 Agent 使用的 skill 源文件在仓库内：

- `skills/openclaw-kaipanla-bridge/`
- 安装脚本：`scripts/install_openclaw_skill.sh`

## 下次接续时直接看这几个文件

- [KPL_HANDOFF.md](KPL_HANDOFF.md)
- [Docs/07-开盘啦迁移方案.md](Docs/07-%E5%BC%80%E7%9B%98%E5%95%A6%E8%BF%81%E7%A7%BB%E6%96%B9%E6%A1%88.md)
- [Docs/08-Mac-mini物料与验证清单.md](Docs/08-Mac-mini%E7%89%A9%E6%96%99%E4%B8%8E%E9%AA%8C%E8%AF%81%E6%B8%85%E5%8D%95.md)
