# Phase 1 完成报告：数据管道 + 端到端验证

## 1. 目标与交付

Phase 1 的核心目标是**打通 mitmproxy 抓包 → 解析 → SQLite 存储的全链路**，并建立可无设备运行的单元测试体系。

### 交付清单

| 交付物 | 状态 | 说明 |
|--------|------|------|
| mitmproxy addon | ✅ | 拦截小红书 API，懒加载 db/parser |
| API 响应解析器 | ✅ | 支持 search_notes / homefeed / detailfeed / comments |
| SQLite 存储层 | ✅ | notes + comments 表，upsert 去重 |
| 页面状态检测 | ✅ | 基于 activity 名称 + 元素特征 |
| UI 操作封装 | ✅ | 滑动/点击/搜索/评论，含随机化 |
| 设备连接管理 | ✅ | 懒加载 u2，支持无设备导入 |
| 任务调度器 | ⚠️ | 骨架完成，主循环待真机联调 |
| 单元测试 | ✅ | 95 个测试，0.13s 全通过 |
| 端到端验证 | ✅ | 真机首页滑动 → 16 条笔记写入 DB |
| 项目文档 | ✅ | 7 篇设计文档 |

---

## 2. 架构概览

```
┌──────────────┐       USB Tunnel        ┌───────────────┐
│  OnePlus 8T  │  ←─ adb reverse ──────→ │   Mac Host     │
│  XHS v9.19.5 │  ←─ proxy 127.0.0.1 ──→ │  mitmdump:8080 │
└──────────────┘                          └───────┬───────┘
                                                  │
                          ┌───────────────────────┼───────────────────────┐
                          │                       │                       │
                   ┌──────▼──────┐         ┌──────▼──────┐        ┌──────▼──────┐
                   │ addon.py    │         │ parser.py   │        │   db.py     │
                   │ response()  │────────→│ XHSParser   │───────→│  Database   │
                   │ _is_target()│         │ 4 种解析    │        │  SQLite     │
                   └─────────────┘         └─────────────┘        └─────────────┘

                   ┌─────────────┐         ┌─────────────┐        ┌─────────────┐
                   │ device.py   │         │ state.py    │        │ actions.py  │
                   │ connect_usb │────────→│ detect_page │───────→│ XHSActions  │
                   │ launch_app  │         │ 10 种状态   │        │ 滑/点/搜    │
                   └─────────────┘         └─────────────┘        └─────────────┘
                          │                       │                       │
                          └───────────────────────┼───────────────────────┘
                                                  │
                                         ┌────────▼────────┐
                                         │ orchestrator.py │
                                         │ 主循环（待联调）│
                                         └─────────────────┘
```

---

## 3. 关键技术决策与发现

### 3.1 代理方案：USB Tunnel 替代 WiFi

**问题**：手机 WiFi（172.16.90.x）与 Mac（192.168.100.x）不同子网，无法直接通信。

**方案**：
```bash
adb reverse tcp:8080 tcp:8080          # USB 端口转发
adb shell su -c "settings put global http_proxy 127.0.0.1:8080"
```

### 3.2 SSL 证书注入：Magisk Module

Android 13 的 `/system` 使用 erofs（只读），无法 `mount -o rw,remount`。

**方案**：创建 Magisk 模块 overlay 系统证书目录：
```
/data/adb/modules/mitmcert/
├── module.prop
└── system/etc/security/cacerts/c8750f0d.0
```

### 3.3 Resource ID 全混淆

XHS v9.19.5 所有 resource-id 均为 `com.xingin.xhs:id/0_resource_name_obfuscated`，不可用。

**方案**：页面检测改为 activity 名称优先 + text/description 兜底：
- `NoteDetailActivity` → NOTE_DETAIL / COMMENT
- `*Search*` → SEARCH_INPUT / SEARCH_RESULT
- `description="首页"` + `description="发现"` → HOME

### 3.4 真实 API 格式（与文档/假设不同）

| API | 假设格式 | 实测格式 |
|-----|----------|----------|
| homefeed | `data.data.items[]` + `note_card` 嵌套 | `data.data` 直接是 list，字段平铺 |
| search/notes | `data.data.items[].note_card` | `data.data.items[].note` |
| 用户字段 | `user.user_id` | `user.userid` |
| 点赞字段 | `interact_info.liked_count` | homefeed: `likes` / search: `liked_count` |
| 主机 | 全部 `edith.xiaohongshu.com` | 搜索: `so.` / 推荐: `rec.` / 详情: `edith.` |

---

## 4. 模块说明

### 4.1 `src/proxy/addon.py` — mitmproxy 中间件

- `response()` 钩子拦截目标 API 响应
- `_is_target()` 基于 `TARGET_HOSTS` (set) + `TARGET_PATHS` (prefix match) 过滤
- 懒加载 `Database` 和 `XHSParser`，避免 import 副作用
- `SAVE_FIXTURE=true` 环境变量启用原始 JSONL 存档

### 4.2 `src/proxy/parser.py` — API 响应解析

4 个解析方法，按 path 分发：

| 方法 | 匹配路径 | 数据结构 |
|------|----------|----------|
| `_parse_search_notes()` | `search/notes` | `items[].note` + `model_type` 过滤 |
| `_parse_homefeed()` | `homefeed`（排除 `categories`） | `data` 直接是 list，跳过 `is_ads` |
| `_parse_note_detail()` | `detailfeed`（排除 `preload`） | `note_detail_map` dict |
| `_parse_comments()` | `comments` | `comments[]` + `target_comment` 判断回复 |

### 4.3 `src/storage/db.py` — SQLite 存储

- 3 张表：`notes`、`comments`、`crawl_tasks`
- `save()` 使用 duck typing（`hasattr(item, 'cover_url')`）区分 NoteItem / CommentItem
- `INSERT OR REPLACE` 实现 upsert 去重
- `get_pending_tasks()` 自动重置中断的 `running` → `pending`

### 4.4 `src/controller/state.py` — 页面状态机

10 种状态枚举，检测优先级：
1. 包名检查 → UNKNOWN（非 XHS）
2. Activity 名称匹配 → LOGIN / NOTE_DETAIL / COMMENT / SEARCH / USER_PROFILE
3. 元素检测兜底 → CAPTCHA / SEARCH_RESULT / HOME / UNKNOWN_DIALOG / UNKNOWN

### 4.5 `src/controller/actions.py` — UI 操作

- 所有操作包含坐标抖动（jitter）和随机延时
- `search_keyword()` 逐字输入模拟打字
- `open_comments()` 使用 `descriptionMatches="评论 \\d+"` 匹配带数量的按钮

### 4.6 `src/orchestrator.py` — 主调度器

- 懒加载设备连接
- 关键词循环 → 搜索 → 滚动 → 进入笔记 → 评论采集
- 异常恢复：`navigate_to_home()` → `launch_app(fresh_start=True)`
- CLI 入口：`python -m src.orchestrator keyword1 keyword2 --limit 200`

---

## 5. 测试体系

### 95 个单元测试，全部无设备依赖

```
tests/unit/test_parser.py    29 tests  — 搜索/homefeed/详情/评论解析
tests/unit/test_db.py        21 tests  — CRUD + upsert + 任务管理
tests/unit/test_addon.py     15 tests  — 目标过滤 + 多 host 支持
tests/unit/test_actions.py   17 tests  — 滑动/点击/搜索/评论操作
tests/unit/test_state.py     13 tests  — 页面状态检测
```

**运行**：`python3 -m pytest tests/unit/ -q`（0.13s）

### 端到端验证结果

```
设备: OnePlus 8T KB2000
APP: 小红书 v9.19.5
操作: 强杀重启 → 首页滑动 5 次
结果: 16 条笔记写入 data/xiaohongshu.db
示例:
  [normal] 一滴雨     | 一周穿搭合集🔗              | 赞:1182
  [video]  燕麦谷妮   | 15套｜回顾1月最爱穿搭look    | 赞:438
  [normal] 包洁仪     | 大家好，我是包包             | 赞:28592
```

---

## 6. 运行方式

### 启动代理抓包
```bash
adb reverse tcp:8080 tcp:8080
adb shell su -c "settings put global http_proxy 127.0.0.1:8080"
XHS_DB_PATH="data/xiaohongshu.db" mitmdump -p 8080 -s src/proxy/addon.py
```

### 结束后清理
```bash
# 必须全部执行，否则手机无法上网
adb shell su -c "settings put global http_proxy :0"
adb shell su -c "settings delete global http_proxy"
adb shell su -c "settings delete global global_http_proxy_host"
adb shell su -c "settings delete global global_http_proxy_port"
adb shell su -c "settings delete global global_http_proxy_exclusion_list"
adb reverse --remove-all
```

### 查询数据
```bash
sqlite3 data/xiaohongshu.db "SELECT count(*) FROM notes;"
sqlite3 data/xiaohongshu.db "SELECT note_id, title, liked_count FROM notes LIMIT 10;"
```

---

## 7. 已知问题与 Phase 2 待办

| 项目 | 状态 | 说明 |
|------|------|------|
| 评论 API 路径 | ❓ | `/api/sns/v2/note/comments` 待抓包确认 |
| `detailfeed/preload` | ⚠️ | 总是 `success=False, code=-100`，需确认正确路径 |
| orchestrator `_crawl_note()` | ⚠️ | 使用了混淆的 resourceId 定位笔记卡片，需改用其他方式 |
| 搜索关键词自动化 | 🔲 | orchestrator 主循环待真机联调 |
| 反封号策略落地 | 🔲 | 频率控制/UA轮换/行为模式随机化 |
| 数据导出 | 🔲 | CSV/JSON 导出工具 |

---

## 8. 文件清单

```
src/
├── config.py              # 全局配置
├── orchestrator.py         # 主调度器
├── proxy/
│   ├── addon.py           # mitmproxy 中间件
│   └── parser.py          # API 响应解析
├── storage/
│   └── db.py              # SQLite 存储
└── controller/
    ├── device.py          # 设备连接
    ├── state.py           # 页面状态检测
    └── actions.py         # UI 操作封装

tests/unit/                # 95 个单元测试
tests/fixtures/            # 测试数据

Docs/                      # 7 篇设计文档 + 本报告
```
