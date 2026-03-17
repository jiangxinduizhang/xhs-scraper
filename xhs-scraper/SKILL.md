---
name: xhs-scraper
description: "小红书数据采集调度 — ADB + mitmproxy 拦截 API 响应，解析后存入 SQLite。支持关键词搜索、评论抓取、数据导出。当用户提到小红书、XHS、抓取笔记、采集数据、爬取评论、导出小红书数据、红书抓取时触发此技能。即使用户只是问'帮我抓点小红书数据'或'搜一下小红书上的XX'也应该触发。"
---

# 小红书数据采集调度

## 架构概览

```
手机 XHS App ──USB tunnel──▶ mitmproxy (addon.py) ──解析──▶ SQLite
                                     ▲
     uiautomator2 (orchestrator) ────┘ 控制 UI 滑动/点击/搜索
```

**三层架构**:
- **数据层**: mitmproxy 中间人代理拦截小红书 API 响应（被动采集，不主动请求）
- **控制层**: uiautomator2 通过 ADB 控制手机 UI，模拟真人浏览行为
- **存储层**: SQLite 数据库，upsert 去重，支持 CSV/JSON 导出

**技术栈**: Python 3.13 · uiautomator2 · mitmproxy · SQLite · ADB (USB tunnel)

---

## 快速开始

### 前置条件
- 已 root 的 Android 设备（OnePlus 8T, Magisk）通过 USB 连接
- 已安装 mitmproxy 证书到系统信任存储（Magisk 模块）
- Python 3.13 + 依赖已安装（`pip install -r requirements.txt`）

### 1. 启动代理
```bash
adb reverse tcp:8080 tcp:8080
adb shell su -c "settings put global http_proxy 127.0.0.1:8080"
XHS_DB_PATH="data/xiaohongshu.db" mitmdump -p 8080 -s src/proxy/addon.py
```

### 2. 运行采集
```bash
# 基本用法
python -m src.orchestrator 三顿半 --sort 最新

# 多关键词 + 限制数量
python -m src.orchestrator 咖啡 奶茶 三顿半 --limit 200 --sort 最热

# 指定数据库
python -m src.orchestrator 咖啡 --db data/custom.db
```

### 3. 停止代理（必须完整执行）
```bash
adb shell su -c "settings put global http_proxy :0"
adb shell su -c "settings delete global http_proxy"
adb shell su -c "settings delete global global_http_proxy_host"
adb shell su -c "settings delete global global_http_proxy_port"
adb shell su -c "settings delete global global_http_proxy_exclusion_list"
adb reverse --remove-all
# 飞行模式刷新网络（必须，否则手机无法上网）
adb shell su -c "settings put global airplane_mode_on 1"
adb shell su -c "am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true"
sleep 2
adb shell su -c "settings put global airplane_mode_on 0"
adb shell su -c "am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false"
```

### 4. 导出数据
```bash
python scripts/export_data.py --db data/xiaohongshu.db --format csv --output data/export/
python scripts/export_data.py --db data/xiaohongshu.db --format json --output data/export/
```

---

## CLI 参数

### orchestrator（采集主程序）

```
python -m src.orchestrator <keywords...> [options]
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keywords` | positional | 必填 | 搜索关键词（支持多个，空格分隔） |
| `--limit` | int | 500 | 每日笔记采集上限 |
| `--sort` | choice | 综合 | 排序方式：综合 / 最新 / 最热 |
| `--db` | path | data/xiaohongshu.db | SQLite 数据库路径 |

### export_data（数据导出）

```
python scripts/export_data.py --db <path> --format <csv|json> --output <dir>
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `--db` | path | SQLite 数据库路径 |
| `--format` | choice | csv 或 json |
| `--output` | path | 输出目录（自动创建） |

---

## 项目结构

```
src/
├── config.py                  # 全局配置（TARGET_HOSTS、反封号参数）
├── orchestrator.py            # 主调度器（搜索→滑动→进详情→采评论）
├── proxy/
│   ├── addon.py               # mitmproxy 中间件（拦截+分发）
│   └── parser.py              # API 响应解析（4 种格式）+ 数据类
├── controller/
│   ├── device.py              # ADB 连接、APP 启动、preflight 预检
│   ├── actions.py             # UI 操作封装（滑动/点击/搜索/评论滚动）
│   └── state.py               # 页面状态检测（10 种状态，基于 activity）
├── storage/
│   └── db.py                  # SQLite upsert + CSV/JSON 导出
└── midscene/
    ├── bridge.py              # Node.js Midscene 桥接
    └── handlers.py            # 视觉异常处理（验证码/弹窗）
```

---

## 采集流程

1. **预检** — `preflight_check()` 验证 adb reverse、代理设置、端口连通
2. **启动 APP** — 冷启动小红书，等待加载
3. **逐关键词处理**:
   - 导航到首页 → 搜索关键词 → 切换排序（最新/最热）
   - `fling_load(rounds=3)` 快速上下翻滚加载列表
   - mitmproxy 自动拦截所有搜索 API 分页响应，解析后写入 SQLite
   - 逐个点击可见卡片进入详情页
   - 详情页停留 3-8s（模拟阅读），向下滚动 2-5 次触发评论分页
   - 评论 API 在进入详情时自动触发，无需显式打开评论区
   - 返回搜索列表，继续下一张卡片
4. **反封号行为穿插**:
   - 5% 概率走神 30-120s
   - 15% 概率快速略过（秒退详情）
   - 10% 概率随机浏览（模拟仔细阅读）
   - 关键词间随机等待 30-90s
5. **停止条件**: 达到日限 / 会话超时 / 所有关键词处理完毕

---

## 数据模型

### NoteItem（笔记）

| 字段 | 类型 | 说明 |
|------|------|------|
| note_id | str | 笔记唯一 ID |
| title | str | 标题 |
| desc | str | 描述正文 |
| author_id | str | 作者 ID |
| author_name | str | 作者昵称 |
| liked_count | int | 点赞数 |
| collected_count | int | 收藏数 |
| comment_count | int | 评论数 |
| cover_url | str | 封面图 URL |
| note_type | str | normal / video |
| timestamp | int | 发布时间（Unix 秒） |
| topics | list | 话题标签列表 |
| keyword | str | 搜索关键词 |
| source | str | 来源：search / homefeed / detailfeed |
| crawled_at | str | 采集时间（ISO 格式） |

### CommentItem（评论）

| 字段 | 类型 | 说明 |
|------|------|------|
| comment_id | str | 评论唯一 ID |
| note_id | str | 所属笔记 ID |
| content | str | 评论内容 |
| author_id | str | 作者 ID |
| author_name | str | 作者昵称 |
| liked_count | int | 点赞数 |
| create_time | int | 创建时间 |
| parent_comment_id | str/None | 父评论 ID（回复时有值） |

---

## 配置调整

常用场景下需要修改 `src/config.py` 的参数，详见 `references/anti-ban-config.md`。

**采 100 条/关键词**: 临时改 `NOTES_PER_KEYWORD = (100, 100)`，完成后恢复。

**降低封号风险**: 增大 `INTER_KEYWORD_DELAY`、`IDLE_PROBABILITY`，降低 `DAILY_NOTE_LIMIT`。

---

## 异常处理

orchestrator 内置三级恢复机制：
1. **Midscene 视觉检测** — 自动识别验证码/弹窗并处理
2. **导航回首页** — 通过 activity 检测当前页面并返回
3. **强制重启 APP** — 最后手段

遇到问题时查看 `references/troubleshooting.md`。

---

## 测试

```bash
# 全量单元测试（165 个，约 2.5s，无需设备）
python3 -m pytest tests/unit/ -q

# 指定模块
python3 -m pytest tests/unit/test_parser.py -v

# 端到端（需要真机 + 代理）
python scripts/e2e_test.py
```

---

## 重要约束

- 所有 XHS resource-id 已混淆（`0_resource_name_obfuscated`），禁止用 resourceId 定位元素
- API 格式必须基于实测抓包，详见 `references/api-formats.md`
- 代理必须走 `adb reverse` USB tunnel（手机与 Mac 不同子网，WiFi 代理不可用）
- 停止代理必须执行完整清理流程，否则手机无法上网
