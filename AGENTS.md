# 接续说明

当前上下文：

- 仓库：`xhs-scraper`
- 远程 `origin`：`git@github.com:jiangxinduizhang/xhs-scraper.git`
- 当前分支：`dev-kpl`
- 工作方式：Windows 负责改代码，Mac mini 负责真实运行和验证

当前目标：

- 判断现有 `xhs-scraper` 框架能否迁移到 `开盘啦`
- 保留小红书原实现，不要直接破坏主线
- 先做最小验证闭环，再逐步扩展

硬性约束：

- 不要把小红书的 host、path、文本、包名直接迁移到 `开盘啦`
- 不要一开始就全量重写
- 不要在 Windows 上做最终链路判断
- 最终运行验证放在 Mac mini
- 不要把 Wi-Fi 代理当主方案，本仓库当前默认走 `adb reverse` USB tunnel
- 没有抓包证据前，不要写死解析规则
- 测试后记得清理代理，不然手机可能表现为断网

优先阅读：

- [Docs/07-开盘啦迁移方案.md](Docs/07-%E5%BC%80%E7%9B%98%E5%95%A6%E8%BF%81%E7%A7%BB%E6%96%B9%E6%A1%88.md)
- [Docs/08-Mac-mini物料与验证清单.md](Docs/08-Mac-mini%E7%89%A9%E6%96%99%E4%B8%8E%E9%AA%8C%E8%AF%81%E6%B8%85%E5%8D%95.md)
- [KPL_HANDOFF.md](KPL_HANDOFF.md)

可复用的通用层：

- `orchestrator`
- `device`
- `addon`
- `db`
- `Midscene` 桥接层

大概率要重写的业务层：

- `config`
- `parser`
- `state`
- `actions`
- Midscene 提示词

快速恢复上下文规则：

- 如果忘了当前进度，先看 `AGENTS.md`
- 再看 `KPL_HANDOFF.md`
- 再看上面的两份 Docs
