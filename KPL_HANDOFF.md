# 开盘啦迁移接续页

当前状态：

- 仓库远程：`origin = git@github.com:jiangxinduizhang/xhs-scraper.git`
- 当前分支：`dev-kpl`
- 开发方式：Windows 写代码，Mac mini 实机验证
- 当前目标：验证 `xhs-scraper` 的框架能否迁移到 `开盘啦`，先做最小闭环，不做全量重构

## 一句话结论

这不是直接复用小红书业务逻辑，而是复用“UI 控制 + 抓包 + 入库 + 异常兜底”的框架骨架，再为 `开盘啦` 重写适配层。

## 当前已确认的关键点

1. `xhs-scraper` 对小红书是强绑定实现，不能直接拿来抓别的 App。
2. `Mac mini + 已 root 的 OnePlus` 足以作为执行机。
3. Windows 可以负责开发，但最终验证放在 Mac mini。
4. 迁移时最容易踩坑的是：
   - 误把小红书 host/path/package 迁移过去
   - 先大改框架而不是先做最小验证
   - 在没有抓包证据前硬写 parser
   - 忘记清理代理，导致手机断网
   - 把 Windows 的 bash 脚本当成可直接运行

## 必须记住的闭坑点

1. 不要用 resourceId 做小红书式迁移假设，目标 App 的页面结构要重新确认。
2. 不要先写大量代码，先验证能否看到真实请求。
3. 不要假设 `mitmproxy` 一定能解密，先确认证书链路和 pinning。
4. 不要假设目标 App 是内容流，金融类 App 常常是行情、图表、WebSocket、加密协议。
5. 不要在 Windows 上做最终链路判断，Windows 只适合写代码。
6. 不要忘记代理退出流程，否则手机可能会“看起来像断网”。

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

- [迁移方案](Docs/07-开盘啦迁移方案.md)
- [Mac mini 物料与验证清单](Docs/08-Mac-mini物料与验证清单.md)

## 下次接续时直接看这几个文件

- [KPL_HANDOFF.md](KPL_HANDOFF.md)
- [Docs/07-开盘啦迁移方案.md](Docs/07-%E5%BC%80%E7%9B%98%E5%95%A6%E8%BF%81%E7%A7%BB%E6%96%B9%E6%A1%88.md)
- [Docs/08-Mac-mini物料与验证清单.md](Docs/08-Mac-mini%E7%89%A9%E6%96%99%E4%B8%8E%E9%AA%8C%E8%AF%81%E6%B8%85%E5%8D%95.md)

