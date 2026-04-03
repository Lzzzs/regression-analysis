# Portfolio Lab — Auto-Iterate Program

> 借鉴 [karpathy/autoresearch](https://github.com/karpathy/autoresearch) 的思想，针对 Portfolio Lab 量化回测系统定制的自迭代 agent 指令。
> 你不是在做 ML 训练，你是在做工程系统的持续改进。核心理念不变：改代码 → 验证 → 好就留、差就扔。

---

## 产品目标

Portfolio Lab 的最终目标是：**一个非专业用户也能用的资产组合回测工具**。

用户画像：对投资感兴趣但不会写代码的普通人。他们想回答一个问题——"如果我过去 N 年按这个比例持有这些资产，表现会怎么样？"

### 当前状态 → 目标状态

| 维度 | 当前状态 | 目标状态 |
|------|---------|---------|
| 上手体验 | 空表单，不知道选什么 | 有策略模板一键加载（60/40、全天候等），首页有引导 |
| 资产选择 | 搜索有时返回空，分类不直观 | 热门资产推荐，搜索快速可靠，支持模糊搜索 |
| 回测结果 | 6 个数字卡片 + 基础 SVG 曲线 | 交互式图表（tooltip、缩放、时间轴），基准对比线，年度分解表 |
| 历史管理 | 只有 job 列表（ID+状态） | 展示组合摘要和核心指标，支持多组合叠加对比 |
| 移动端 | 未验证 | 图表自适应，核心功能可在手机上完成 |

**一句话：从"能跑通的技术 demo"变成"朋友发给你链接你就能用起来的产品"。**

---

## 项目概览

- `apps/web` — Next.js 前端（提交组合、查看任务、查看结果）
- `apps/api` — FastAPI 接口（建任务、查状态、查结果）
- `apps/worker` — 回测后台 worker（消费队列并执行）
- `src/portfolio_lab` — 回测引擎与数据域模型
- `data/providers/*.csv` — 离线数据源
- `tests/` — Python 单元测试（含 `test_golden_cases.py` 回归基准）

---

## Setup

每次启动新一轮迭代时：

1. **确认 tag**：基于日期提议一个 tag（如 `apr3`），创建分支 `auto-iterate/<tag>`。
2. **通读上下文**：
   - `README.md` — 项目架构和启动方式
   - `TODO.md` — 当前已知问题和待办清单（**这是你的任务池**）
   - `CHANGELOG.md` — 已完成的工作
   - `tests/` — 现有测试，了解覆盖范围
3. **跑一次 baseline**：执行验证套件（见下方），记录当前状态。
4. **初始化 `iterations.tsv`**（如不存在）：只写 header。
5. **确认后开始迭代。**

---

## 两种迭代模式

不同类型的任务，验证方式不同。agent 根据任务性质自动选择模式。

### 模式 A：自动验证（引擎/API/工程）

适用于：回测引擎逻辑、API 接口、依赖升级、测试补充、代码清理。

判定规则：Gate 1 + Gate 2 全过 → keep，否则 revert。agent 完全自主。

### 模式 B：执行式（UI/交互/产品功能）

适用于：前端组件、图表升级、表单交互、策略模板、首页 Dashboard、移动端适配。

判定规则：`npm run build` 通过 + 不引入新的 lint/type 错误 → commit 并标记 `keep-pending-review`。agent 不自行判断 UI 效果好不好，留给人肉 review。

**模式 B 的关键约束：**
- 每个 UI 改动必须写清楚做了什么、改了哪个页面/组件、用户可见的变化是什么（写在 commit message 里）
- 不要同时改多个页面的 UI（一次一个页面/一个组件）
- 如果涉及新增 npm 依赖（如换图表库），在 commit message 里说明理由
- 优先使用项目已有的依赖和设计语言，不要随意引入新的 UI 框架

---

## 验证套件

### Gate 1：不能挂（必须全过）

```bash
# Python 单测（含 golden case 回归测试）
PYTHONPATH=.:src python -m pytest tests/ -x --tb=short 2>&1 | tail -20

# Web 构建
cd apps/web && npm run build 2>&1 | tail -20
```

任何一项失败 → 立即 revert，状态记为 `crash`。

### Gate 2：没有退步（模式 A 必须过，模式 B 仅看 build）

- 改了回测引擎（`src/portfolio_lab/`）→ golden case 测试全过，数值偏差 > 0.01% 视为 regression
- 改了 API（`apps/api/`）→ curl 核心接口确认 200
- 改了前端（`apps/web/`）→ `npm run build` 通过即可

### Gate 3：有改进（可选，但鼓励）

- 新增测试（覆盖率上升）
- 修复 TODO.md 中的某个条目
- 代码简化（行数减少，功能不变）
- 性能提升（回测耗时降低）

---

## 迭代循环

在 `auto-iterate/<tag>` 分支上运行。

```
LOOP FOREVER:

1. 读 TODO.md，选一个具体的改进目标
   - 优先级：P0 > P1 > P2 > P3 > 技术债
   - 已被标记 ✅ 的跳过
   - 一次只做一件事
   - 判断该任务属于模式 A 还是模式 B

2. 制定假设
   - 模式 A："改 X，预期 Y 指标不变 / 提升"
   - 模式 B："在 Z 页面添加 W 功能，用户可见变化：..."

3. 实施修改
   - 尽量原子化，一次改一个模块
   - 前后端联动的改动分两次 commit

4. git commit -m "iter(<模式>): <简述>"
   - 模式 A 示例: "iter(A): 回测引擎支持年度收益分解"
   - 模式 B 示例: "iter(B): 任务列表页增加组合摘要和核心指标列"

5. 运行验证套件
   - 模式 A：Gate 1 + Gate 2
   - 模式 B：Gate 1（build 通过即可）

6. 判定结果
   - 模式 A：Gate 1+2 通过 → keep | 失败 → crash/discard + revert
   - 模式 B：build 通过 → keep-pending-review | build 失败 → crash + revert

7. 记录到 iterations.tsv

8. 如果改进涉及 TODO.md 中的条目，更新 TODO.md（标记 ✅ + 日期）

9. 回到步骤 1
```

---

## 记录格式

`iterations.tsv`（tab 分隔）：

```
commit	mode	tests_pass	build_pass	status	description
a1b2c3d	-	yes	yes	keep	baseline
b2c3d4e	A	yes	yes	keep	引擎添加年度收益分解计算
c3d4e5f	B	yes	yes	keep-pending-review	任务列表页增加组合摘要列
d4e5f6g	B	yes	no	crash	换 Recharts 图表库（build 失败）
e5f6g7h	A	yes	yes	discard	重构 worker 为 async（golden case 回归）
```

---

## 任务分类参考

### 模式 A 任务（自动验证，agent 全自主）

| TODO 条目 | 验证信号 |
|-----------|---------|
| 补充单元测试 | 新测试通过，已有测试不挂 |
| 修复 lint/type 错误 | lint 通过 |
| 代码简化 / 删死代码 | 测试全过，行数减少 |
| 依赖升级 | pip install + pytest + build |
| 引擎性能优化 | golden case 通过 + 耗时下降 |
| 添加新的回测指标（年度分解、滚动收益等） | 新测试覆盖 + golden case 不回归 |
| API 新增接口 | pytest + curl 验证 |
| CI/CD 配置 | workflow 文件语法正确 |

### 模式 B 任务（执行式，留给人 review）

| TODO 条目 | 做完的标志 |
|-----------|-----------|
| 策略模板 / 预设组合 | 前端新增模板选择组件，build 通过 |
| 图表升级（SVG → Recharts/ECharts） | 图表组件替换完成，build 通过 |
| 表单体验优化（滑块权重、搜索防抖） | 组件修改完成，build 通过 |
| 首页 Dashboard | 新增 Dashboard 组件，build 通过 |
| 历史回测对比（净值叠加） | 前端对比页完成，build 通过 |
| 基准对比线 | 图表组件叠加基准线，build 通过 |
| 移动端适配 | 关键页面响应式样式，build 通过 |
| 任务状态进度条 | 组件修改完成，build 通过 |

---

## 策略指导

### 改什么

参考 TODO.md 的优先级，遵循以下原则：

- **先修后建**：先修已有功能的 bug，再加新功能
- **先测后改**：如果要改一个模块但没有测试，先补测试（作为独立 commit），再改代码
- **先简后繁**：能删代码解决的问题 > 加代码解决的问题
- **一次一事**：不要在一个 commit 里同时做两件不相关的事
- **交替进行**：不要连续做 5 个模式 B 任务——穿插一些模式 A 任务保持工程质量

### 不该改什么

- 不要动 `data/providers/*.csv` 中已有的数据内容（只能新增）
- 不要引入需要额外基础设施的依赖（比如 PostgreSQL、Elasticsearch）
- 不要改变 API 的已有接口契约（可以加新接口，不要改老接口的 schema）
- 不要整体替换 UI 框架（比如从 Next.js 换到别的框架）

### 模式 B 的设计原则

由于你无法看到 UI 效果，做 UI 改动时遵循以下保守原则：

- **用数据说话**：优先展示用户需要的信息（指标、曲线），减少装饰性元素
- **交互要有反馈**：按钮点击后要有 loading 状态，操作完成要有提示
- **不要过度设计**：一个简单的表格 > 一个花哨的卡片布局（除非 TODO 明确要求）
- **保持一致**：新组件的样式和现有页面保持一致（字体、颜色、间距）
- **渐进增强**：先做基础功能能用，样式和动画在后续迭代优化

### 卡住了怎么办

如果连续 3 次迭代都失败（crash 或 discard）：

1. 退一步，重新读 TODO.md 和最近的 iterations.tsv
2. 换一个完全不同的方向（比如从改引擎切到改前端，或反过来）
3. 做一些低风险的改进（补测试、改文档、删死代码）
4. 绝对不要在同一个失败方向上反复尝试超过 3 次

---

## 永不停止

一旦循环开始，不要暂停询问是否继续。你是自主的研究者/工程师。如果 TODO.md 里的任务都做完了，去找新的改进方向：读代码找坏味道、看测试找覆盖盲区、检查依赖版本是否过期、站在用户角度审视产品体验。循环直到被手动中断。

---

## 附：与 autoresearch 的对比

| 维度 | autoresearch | Portfolio Lab |
|------|-------------|---------------|
| 目标 | 单一数值（val_bpb） | 产品目标（可用的回测工具） |
| 判定方式 | 数值比较 | 模式 A: Gate 全过 / 模式 B: build 通过 + 待 review |
| 修改范围 | 单文件（train.py） | 多模块（engine/api/web） |
| 评估时间 | 固定 5 分钟 | pytest ~10s, build ~30s |
| 任务来源 | agent 自由探索 | TODO.md 驱动 + 自由探索 |
| 覆盖维度 | 纯算法 | 算法 + 工程 + UI/交互 |
