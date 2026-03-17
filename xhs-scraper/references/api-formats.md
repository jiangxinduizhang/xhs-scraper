# 小红书 API 实测格式速查（XHS v9.19.5）

所有格式均基于真机抓包验证，不可凭文档/猜测修改。

## 1. 搜索笔记 — so.xiaohongshu.com

**路径**: `/api/sns/v10/search/notes`

**结构**: `data.data.items[]`，每条 `{model_type: "note", note: {...}}`

| 字段 | 类型 | 说明 |
|------|------|------|
| `note.id` | string | 笔记 ID |
| `note.title` | string | 标题 |
| `note.desc` | string | 描述 |
| `note.liked_count` | string/int | 点赞数（可能是 "1.2万" 格式） |
| `note.collected_count` | string/int | 收藏数 |
| `note.comments_count` | string/int | 评论数 |
| `note.type` | string | "normal" / "video" |
| `note.timestamp` | int | Unix 秒 |
| `note.user.userid` | string | 作者 ID |
| `note.user.nickname` | string | 作者昵称 |
| `note.images_list[0].url` | string | 封面图 URL |
| `note.tag_list[].name` | string | 话题标签 |

**过滤**: `model_type != "note"` 的条目跳过（广告等）

---

## 2. 首页推荐 — rec.xiaohongshu.com

**路径**: `/api/sns/v6/homefeed`

**结构**: `data.data` 是**直接列表**（非 `{items: [...]}`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 笔记 ID |
| `title` / `name` | string | 标题（优先 title） |
| `desc` | string | 描述 |
| `likes` | int | 点赞数 |
| `type` | string | "normal" / "video" |
| `timestamp` | int | Unix 秒 |
| `is_ads` | bool | 广告标记（已跳过） |
| `user.userid` | string | 作者 ID |
| `user.nickname` | string | 作者昵称 |
| `images_list[0].url` | string | 封面图 URL |

**注意**: homefeed 不提供 `collected_count` 和 `comments_count`

---

## 3. 笔记详情 — edith.xiaohongshu.com

**路径**: `/api/sns/v1/note/detailfeed`

**结构**: `data.data.note_detail_map`，key 为 note_id

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 标题 |
| `desc` | string | 描述 |
| `interact_info.liked_count` | string/int | 点赞数 |
| `interact_info.collected_count` | string/int | 收藏数 |
| `interact_info.comment_count` | string/int | 评论数 |
| `type` | string | "normal" / "video" |
| `timestamp` / `time` | int | Unix 秒 |
| `user.userid` | string | 作者 ID |
| `user.nickname` | string | 作者昵称 |
| `tag_list[].name` | string | 话题标签 |

**注意**: `/api/sns/v1/note/detailfeed/preload` 的 `success=False, code=-100` 时 `data=null`，忽略

---

## 4. 评论列表 — edith.xiaohongshu.com

**路径**: `/api/sns/v5/note/comment/list`

**结构**: `data.data.comments[]`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 评论 ID |
| `content` | string | 评论内容 |
| `note_id` | string | 所属笔记 ID（在每条评论上，非顶层） |
| `like_count` | int | 点赞数 |
| `time` / `create_time` | int | 创建时间 |
| `user.userid` | string | 作者 ID |
| `user.nickname` | string | 作者昵称 |
| `target_comment` | object/null | 回复的父评论（null 表示一级评论） |

**注意**: `data.data.note_id` 不存在，note_id 在每条评论对象上

---

## 数量字段解析规则

parser.py 中的 `_parse_count()` 处理以下格式：
- `int` → 直接返回
- `float` → 截断为 int
- `"1,234"` → 去逗号后转 int
- `"2.3万"` → `float("2.3") * 10000 = 23000`
- 无法解析 → 返回 0
