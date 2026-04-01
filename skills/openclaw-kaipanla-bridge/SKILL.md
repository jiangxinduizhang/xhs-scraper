---
name: openclaw-kaipanla-bridge
description: "用于抓取、校验和回读开盘啦中的 A 股行情与题材数据；当用户要查看市场情绪、板块、个股、打板、涨停/炸板、龙虎榜、资金流向、题材热点，或确认抓取是否成功、导出最近一次运行产物时触发。"
---

# 开盘啦 A 股行情桥接

处理开盘啦中的 A 股行情与题材数据。

## 覆盖范围

优先处理这些结构化内容：

- A 股行情
- 板块
- 个股
- 打板 / 连板
- 涨停 / 炸板 / 跌停
- 龙虎榜
- 资金流向
- 市场情绪
- 题材 / 热点

可兼容但不作为主目标：

- 全球入口里的可结构化行情信息
- 首页消息 / 资讯中稳定可抽取的行情提示

不纳入边界：

- 交易执行
- 投资建议
- 通用新闻摘要
- 其他 App
- 需要人工解释的大段文本分析

## 核心动作

- `capture`：抓取并写出产物
- `verify`：校验运行是否真的成立
- `report`：回读运行结果
- `latest`：查看最近一次运行
- `status`：查看最近一次运行及校验结果

## 定位约定

- 安装时会把当前仓库根目录写入已安装 skill 的 `repo-root.txt`。
- launcher 会优先读取 `repo-root.txt`，再读 `OPENCLAW_KPL_REPO_ROOT` / `KPL_REPO_ROOT`，最后才向上搜索当前工作目录。
- launcher 在定位到仓库根目录后会自动切换到该目录再执行命令。
- 如果命令要显式指定仓库根目录，可用 `--repo-root`。

## 调用方式

先安装 skill，再调用桥接脚本：

```bash
bash scripts/install_openclaw_skill.sh
```

优先使用 bundled launcher：

```bash
bash scripts/kpl_bridge.sh capture --task <task.json>
bash scripts/kpl_bridge.sh verify --run <run.json>
bash scripts/kpl_bridge.sh report --run <run.json>
bash scripts/kpl_bridge.sh latest
bash scripts/kpl_bridge.sh status
```

也可以直接调用机器可读桥接：

```bash
python3 scripts/kpl_tool.py capture --task <task.json>
python3 scripts/kpl_tool.py verify --run <run.json>
python3 scripts/kpl_tool.py report --run <run.json>
python3 scripts/kpl_tool.py latest
python3 scripts/kpl_tool.py status
```

`scripts/run_kpl_task.py` 只用于人工或手动触发。

## 输入约定

### `task.json`
至少包含：

- `task_id`
- `app`
- `page`
- `goal`
- `success_criteria`
- `max_attempts`
- `timeout_sec`

### `run.json`
`verify` 和 `report` 读取运行结果文件。

## 证据

以下产物视为事实来源：

- `runs/<task_id>.task.json`
- `runs/<task_id>.json`
- `reports/<task_id>.md`
- `data/raw/<date>.jsonl`
- `data/kaipanla.db`
- `step_events` inside `run.json`

## 判定规则

- `capture` 只表示任务被执行过，不表示闭环成功。
- `verify` 是最终判定门。
- `verify=verified` 才表示闭环成立。
- `step_events` 必须完整，才能证明过程真的发生过。

## 不要做

- 不要把“执行任务”当成这个 skill 的主语义。
- 不要把读取源码当作接入方式。
- 不要依赖内部类名、函数名或目录结构。
- 不要跳过 `verify`。
- 不要把 `capture` 当成成功证明。
