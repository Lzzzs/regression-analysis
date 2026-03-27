# UI 重设计规范

**日期:** 2026-03-27
**项目:** regression-analysis / apps/web
**状态:** 已确认，待实现

---

## 目标

将现有三页回测控制台（提交页、任务列表页、任务详情页）从原始内联样式升级为生产级 UI，引入 Tailwind CSS，实现响应式布局。

---

## 技术选型

- **CSS 框架:** Tailwind CSS v3（集成到 Next.js 14）
- **不引入** 组件库（shadcn、MUI 等），保持轻量
- **图标:** 使用 emoji 或 Heroicons（按需引入 SVG）

---

## 视觉风格

极简现代，参考 Vercel / Linear 风格：

| 元素 | 规范 |
|------|------|
| 背景 | `bg-gray-50` (#fafafa) |
| 卡片 | `bg-white border border-gray-100 rounded-xl` |
| 主色 | `#111111`（文字、按钮、Logo） |
| 激活导航 | `bg-gray-100 text-gray-900 font-semibold` |
| 状态-完成 | `bg-green-50 text-green-700` pill badge |
| 状态-运行中/排队 | `bg-amber-50 text-amber-700` pill badge |
| 状态-失败/死信 | `bg-red-50 text-red-600` pill badge |
| 主按钮 | `bg-gray-900 text-white rounded-lg hover:bg-gray-800` |
| 输入框 | `border border-gray-200 rounded-lg bg-gray-50 focus:bg-white` |

---

## 整体布局

### 桌面 / 平板（md: ≥ 768px）

```
┌──────────┬────────────────────────────────┐
│          │                                │
│  Sidebar │       主内容区                 │
│  200px   │       (flex-1, overflow-auto)  │
│          │                                │
└──────────┴────────────────────────────────┘
```

侧边栏结构：
- 顶部：Logo（黑色方块 + "Portfolio Lab"文字）
- 导航：提交任务、任务列表（两个 nav item）
- 底部：API 状态指示灯（绿点 + "API 就绪"）

### 手机（< 768px）

侧边栏隐藏，底部固定 Tab 栏：
```
┌───────────────────────────┐
│       主内容区             │
│                           │
├───────────┬───────────────┤
│  📝 提交  │   📋 任务     │  ← 底部 tab bar
└───────────┴───────────────┘
```

### 共用 Shell 组件

新建 `apps/web/app/components/Shell.tsx`，包含侧边栏 + 底部 Tab 栏逻辑，所有页面用它包裹替换 `<main>`。

---

## 页面详情

### 1. 提交任务页（`/`）

**桌面（md+）:** 两栏表单
- 左栏：分析区间（开始/结束日期）+ 再平衡频率
- 右栏：组合权重 JSON textarea
- 下方：高级配置折叠区（资产列表、汇率对、数据源文件），默认收起，点击展开
- 底部：全宽"一键分析"主按钮
- 成功后：快照 ID + 任务链接内联显示在按钮下方

**手机（< md）:** 单列，各字段依次排列，同样有折叠高级配置

### 2. 任务列表页（`/jobs`）

**桌面:** 表格布局
- 搜索框 + 状态筛选下拉 + 手动刷新按钮 横排
- 表格列：任务 ID（monospace 蓝色链接）、状态 badge、重试次数、创建时间、操作
- 分页：上一页/下一页 + 当前页数
- 死信任务：合并进主表格（通过状态筛选区分），不单独列表

**手机:** 卡片列表替代表格
- 每张卡片：任务 ID + 状态 badge（同行）、创建时间 + 重试（次行）
- 死信/失败卡片底部显示"重入队"按钮

### 3. 任务详情页（`/jobs/[id]`）

**顶部:**
- 面包屑：← 任务列表
- 任务 ID（monospace 大字）+ 状态 badge + 重试计数

**指标区（`completed` 状态才显示）:**
- 6 个指标卡片，3 列网格（手机 2 列）
- 年化收益、最大回撤、夏普比率、年化波动率、索提诺比率、卡玛比率
- 负值（回撤）用红色字体，正值默认黑色

**图表区（`completed` 状态才显示）:**
- 净值曲线 + 回撤曲线，桌面并排两列，手机单列
- 保留现有 SVG 手写图表逻辑，改样式（stroke 颜色、背景）

**执行时间线:**
- 可折叠，默认展开
- 每个事件：彩色圆点 + 事件名 + 时间戳，纵向排列

**原始 JSON:**
- 默认折叠（"展开 ▾"），点击展开 `<pre>` 块

---

## 响应式断点

| 断点 | 布局变化 |
|------|---------|
| `< md (768px)` | 侧边栏隐藏 → 底部 tab 栏；表格 → 卡片；表单单列 |
| `md - lg` | 侧边栏显示（图标+文字），表单两栏 |
| `> lg` | 同 md，内容区更宽 |

---

## 文件改动范围

| 文件 | 改动 |
|------|------|
| `apps/web/package.json` | 新增 tailwindcss、postcss、autoprefixer |
| `apps/web/tailwind.config.js` | 新建，配置 content 路径 |
| `apps/web/postcss.config.js` | 新建 |
| `apps/web/app/globals.css` | 新建，引入 Tailwind 指令 |
| `apps/web/app/layout.tsx` | 引入 globals.css，移除内联 body 样式 |
| `apps/web/app/components/Shell.tsx` | 新建，侧边栏 + 底部 tab 栏 |
| `apps/web/app/page.tsx` | 用 Shell 包裹，重写表单 UI |
| `apps/web/app/jobs/page.tsx` | 用 Shell 包裹，重写列表 UI |
| `apps/web/app/jobs/[id]/page.tsx` | 用 Shell 包裹，重写详情 UI |

---

## 不在本次范围内

- 图表库替换（保留现有 SVG 手写实现）
- 数据层 / API 改动
- 深色模式
- 动画 / 过渡效果（基础 hover 除外）
