# 开盘啦 Round3 实施方案（registered promote 与稳定交付）

> Round3 目标：把稳定 exploration 路径沉淀为 registered 能力，让自然语言任务逐步从“探索型”升级为“稳定交付型”。

---

## 0. 目标

Round3 只解决一件事：

**把已验证稳定的探索经验 promote 成 registered，使用户能稳定通过自然语言完成高频任务。**

---

## 1. 范围

### 要做
1. promote 判定标准
2. reusable recipe → registered 流程
3. registered verify 门槛
4. registered 失败时回退 exploration
5. 至少一个页面完成 promote 验证

### 不做
- 大规模页面扩展
- bridge 自行业务判断
- 脱离证据的自动成功判定

---

## 2. P0 实施项

### P0-1. promote 标准
只有同时满足以下条件才可 promote：
- 路径可复现
- 证据稳定
- 不再主要依赖人工解释
- 多次 run 一致

### P0-2. recipe 沉淀
需要沉淀：
- 动作顺序
- 等待时长
- 噪声基线
- 关键证据模式
- registered verify 门槛

### P0-3. registered 回退 exploration
当 registered 结果异常时，AI 必须能：
- 识别失败
- 回退 exploration
- 继续自然语言闭环

---

## 3. 验收

Round3 完成必须同时满足：
1. 至少一个页面完成 promote
2. 用户可通过自然语言稳定触发该任务
3. registered 失败时能自动回退 exploration
4. AI 对外仍自然语言解释结果
