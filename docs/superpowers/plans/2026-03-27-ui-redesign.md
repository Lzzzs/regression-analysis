# UI 重设计实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 regression-analysis 回测控制台从原始内联样式升级为 Tailwind CSS 驱动的响应式 UI，风格参考 Vercel/Linear。

**Architecture:** 新增 `Shell` 组件统一管理侧边栏（桌面）和底部 Tab 栏（手机），三个页面各自重写 JSX，保留所有数据逻辑不动。

**Tech Stack:** Next.js 14, Tailwind CSS v3, TypeScript

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `apps/web/package.json` | 修改 | 新增 tailwindcss、postcss、autoprefixer |
| `apps/web/tailwind.config.js` | 新建 | Tailwind content 路径配置 |
| `apps/web/postcss.config.js` | 新建 | PostCSS 插件配置 |
| `apps/web/app/globals.css` | 新建 | Tailwind 指令入口 |
| `apps/web/app/layout.tsx` | 修改 | 引入 globals.css，移除内联 body 样式 |
| `apps/web/app/components/Shell.tsx` | 新建 | 侧边栏 + 底部 Tab 栏布局组件 |
| `apps/web/app/page.tsx` | 修改 | 提交任务页，两栏表单 + 折叠高级配置 |
| `apps/web/app/jobs/page.tsx` | 修改 | 任务列表页，桌面表格 / 手机卡片 |
| `apps/web/app/jobs/[id]/page.tsx` | 修改 | 任务详情页，指标网格 + 图表 + 时间线 |

---

## Task 1: 安装并配置 Tailwind CSS

**Files:**
- Modify: `apps/web/package.json`
- Create: `apps/web/tailwind.config.js`
- Create: `apps/web/postcss.config.js`
- Create: `apps/web/app/globals.css`
- Modify: `apps/web/app/layout.tsx`

- [ ] **Step 1: 安装依赖**

```bash
cd /Users/didi/Desktop/code/regression-analysis/apps/web
npm install -D tailwindcss@3 postcss autoprefixer
```

Expected: package-lock.json 更新，node_modules 中有 tailwindcss。

- [ ] **Step 2: 创建 tailwind.config.js**

```js
// apps/web/tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
```

- [ ] **Step 3: 创建 postcss.config.js**

```js
// apps/web/postcss.config.js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 4: 创建 globals.css**

```css
/* apps/web/app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 5: 更新 layout.tsx 引入 globals.css 并移除内联样式**

```tsx
// apps/web/app/layout.tsx
import './globals.css';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="bg-gray-50 font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 6: 验证构建通过**

```bash
cd /Users/didi/Desktop/code/regression-analysis/apps/web
npm run build
```

Expected: 构建成功，无 PostCSS / Tailwind 相关报错。

- [ ] **Step 7: 提交**

```bash
cd /Users/didi/Desktop/code/regression-analysis/apps/web
git add package.json package-lock.json tailwind.config.js postcss.config.js app/globals.css app/layout.tsx
git commit -m "feat(web): add Tailwind CSS v3"
```

---

## Task 2: 创建 Shell 布局组件

**Files:**
- Create: `apps/web/app/components/Shell.tsx`

Shell 负责：侧边栏（md+）、底部 Tab 栏（< md）、当前路由高亮。

- [ ] **Step 1: 创建 components 目录并新建 Shell.tsx**

```tsx
// apps/web/app/components/Shell.tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV = [
  { href: '/', label: '提交任务', icon: '📝' },
  { href: '/jobs', label: '任务列表', icon: '📋' },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* ── 侧边栏（md+）── */}
      <aside className="hidden md:flex md:w-52 flex-col bg-white border-r border-gray-100 fixed inset-y-0 left-0 z-10">
        {/* Logo */}
        <div className="flex items-center gap-2 px-4 py-5 border-b border-gray-100">
          <div className="w-6 h-6 bg-gray-900 rounded-md flex-shrink-0" />
          <span className="text-sm font-bold text-gray-900">Portfolio Lab</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-2 space-y-0.5">
          {NAV.map(({ href, label, icon }) => (
            <Link
              key={href}
              href={href}
              className={[
                'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
                isActive(href)
                  ? 'bg-gray-100 text-gray-900 font-semibold'
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900',
              ].join(' ')}
            >
              <span className="text-base">{icon}</span>
              {label}
            </Link>
          ))}
        </nav>

        {/* API 状态 */}
        <div className="px-4 py-3 border-t border-gray-100">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-xs text-gray-400">API 就绪</span>
          </div>
        </div>
      </aside>

      {/* ── 主内容区 ── */}
      <main className="flex-1 md:ml-52 pb-16 md:pb-0">
        {children}
      </main>

      {/* ── 底部 Tab 栏（< md）── */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-gray-100 z-10 grid grid-cols-2">
        {NAV.map(({ href, label, icon }) => (
          <Link
            key={href}
            href={href}
            className={[
              'flex flex-col items-center justify-center py-2 text-xs gap-0.5 transition-colors',
              isActive(href)
                ? 'text-gray-900 font-semibold'
                : 'text-gray-400',
            ].join(' ')}
          >
            <span className="text-lg leading-none">{icon}</span>
            {label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
```

- [ ] **Step 2: 验证 TypeScript 无报错**

```bash
cd /Users/didi/Desktop/code/regression-analysis/apps/web
npx tsc --noEmit
```

Expected: 无错误输出。

- [ ] **Step 3: 提交**

```bash
git add app/components/Shell.tsx
git commit -m "feat(web): add Shell layout component with sidebar and bottom tab bar"
```

---

## Task 3: 重写提交任务页

**Files:**
- Modify: `apps/web/app/page.tsx`

两栏表单（桌面），单列（手机），高级配置默认折叠。

- [ ] **Step 1: 完整替换 page.tsx**

```tsx
// apps/web/app/page.tsx
'use client';

import { FormEvent, useState } from 'react';
import Shell from './components/Shell';
import { createJobAuto } from '../lib/api';
import { toChineseValue } from '../lib/field_localizer';

export default function Page() {
  const [startDate, setStartDate] = useState('2026-01-05');
  const [endDate, setEndDate] = useState('2026-01-09');
  const [frequency, setFrequency] = useState('monthly');
  const [weights, setWeights] = useState('{"CSI300":0.5,"SPY":0.5}');
  const [jobId, setJobId] = useState('');
  const [selectedAssets, setSelectedAssets] = useState('');
  const [requiredFxPairs, setRequiredFxPairs] = useState('');
  const [providerFiles, setProviderFiles] = useState('{}');
  const [snapshotId, setSnapshotId] = useState('');
  const [error, setError] = useState('');
  const [advanced, setAdvanced] = useState(false);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const parsedWeights = JSON.parse(weights);
      const parsedProviderFiles = providerFiles.trim() ? JSON.parse(providerFiles) : {};
      const payload: Record<string, unknown> = {
        start_date: startDate,
        end_date: endDate,
        rebalance_frequency: frequency,
        base_currency: 'CNY',
        weights: parsedWeights,
        provider_files: parsedProviderFiles,
      };
      if (selectedAssets.trim()) payload.selected_assets = JSON.parse(selectedAssets);
      if (requiredFxPairs.trim()) payload.required_fx_pairs = JSON.parse(requiredFxPairs);
      const data = await createJobAuto(payload);
      setJobId(data.job_id);
      setSnapshotId(data.snapshot_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Shell>
      <div className="px-4 py-6 md:px-8 md:py-8 max-w-4xl">
        {/* 页头 */}
        <div className="mb-6">
          <h1 className="text-xl font-bold text-gray-900">提交回测任务</h1>
          <p className="text-sm text-gray-400 mt-1">自动生成快照并创建分析任务</p>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          {/* 主配置：桌面两栏，手机单列 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* 左栏：区间 + 频率 */}
            <div className="bg-white border border-gray-100 rounded-xl p-4 space-y-3">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">分析区间</p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">开始日期</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    required
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-1"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">结束日期</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    required
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-1"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">再平衡频率</label>
                <select
                  value={frequency}
                  onChange={(e) => setFrequency(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-1"
                >
                  <option value="none">{toChineseValue('none')}</option>
                  <option value="monthly">{toChineseValue('monthly')}</option>
                  <option value="quarterly">{toChineseValue('quarterly')}</option>
                </select>
                <p className="text-xs text-gray-400 mt-1">结束日期需为周五</p>
              </div>
            </div>

            {/* 右栏：组合权重 */}
            <div className="bg-white border border-gray-100 rounded-xl p-4 space-y-3">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">组合权重</p>
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  权重 JSON <span className="text-red-400">*</span>
                </label>
                <textarea
                  rows={6}
                  value={weights}
                  onChange={(e) => setWeights(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-1 resize-none"
                />
              </div>
            </div>
          </div>

          {/* 高级配置折叠区 */}
          <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
            <button
              type="button"
              onClick={() => setAdvanced((v) => !v)}
              className="w-full flex items-center justify-between px-4 py-3 text-sm text-gray-500 hover:bg-gray-50 transition-colors"
            >
              <span className="font-medium">高级配置（可选）</span>
              <span className="text-gray-400 text-xs">{advanced ? '收起 ▴' : '展开 ▾'}</span>
            </button>
            {advanced && (
              <div className="px-4 pb-4 space-y-3 border-t border-gray-100">
                <div>
                  <label className="block text-xs text-gray-500 mb-1 mt-3">资产列表 JSON（留空自动推断）</label>
                  <textarea
                    rows={2}
                    value={selectedAssets}
                    onChange={(e) => setSelectedAssets(e.target.value)}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-1 resize-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">汇率货币对 JSON（留空自动推断）</label>
                  <textarea
                    rows={2}
                    value={requiredFxPairs}
                    onChange={(e) => setRequiredFxPairs(e.target.value)}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-1 resize-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">数据源文件配置 JSON（默认读取内置配置）</label>
                  <textarea
                    rows={3}
                    value={providerFiles}
                    onChange={(e) => setProviderFiles(e.target.value)}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-1 resize-none"
                  />
                </div>
              </div>
            )}
          </div>

          {/* 提交按钮 */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gray-900 text-white rounded-xl py-3 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? '分析中...' : '一键分析（自动生成快照 + 提交任务）'}
          </button>

          {/* 结果反馈 */}
          {snapshotId && (
            <p className="text-sm text-gray-500">
              快照 ID：<span className="font-mono text-gray-900">{snapshotId}</span>
            </p>
          )}
          {jobId && (
            <p className="text-sm text-gray-500">
              已创建任务：{' '}
              <a href={`/jobs/${jobId}`} className="font-mono text-blue-600 hover:underline">
                {jobId}
              </a>
            </p>
          )}
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
        </form>
      </div>
    </Shell>
  );
}
```

- [ ] **Step 2: 验证 TypeScript 无报错**

```bash
cd /Users/didi/Desktop/code/regression-analysis/apps/web
npx tsc --noEmit
```

Expected: 无错误。

- [ ] **Step 3: 启动开发服务器，浏览器验证页面渲染正常**

```bash
npm run dev
```

打开 http://localhost:3000，检查：
- 侧边栏在桌面可见，手机缩窗口时消失并出现底部 Tab 栏
- 表单两栏布局在桌面正常，手机单列
- 高级配置折叠/展开正常

- [ ] **Step 4: 提交**

```bash
git add app/page.tsx
git commit -m "feat(web): redesign home page with Tailwind"
```

---

## Task 4: 重写任务列表页

**Files:**
- Modify: `apps/web/app/jobs/page.tsx`

桌面用表格，手机用卡片列表，状态用彩色 badge。

- [ ] **Step 1: 完整替换 jobs/page.tsx**

```tsx
// apps/web/app/jobs/page.tsx
'use client';

import { useEffect, useMemo, useState } from 'react';
import Shell from '../components/Shell';
import { toChineseFieldName, toChineseValue } from '../../lib/field_localizer';
import { listDeadLetterJobs, listJobs, requeueJob } from '../../lib/api';

type JobItem = {
  job_id: string;
  status: string;
  created_at: string;
  retry_count?: number;
  max_retries?: number;
  remaining_retries?: number;
  error?: string | null;
};

const PAGE_SIZE = 20;

function statusBadge(status: string) {
  const map: Record<string, string> = {
    completed: 'bg-green-50 text-green-700',
    running: 'bg-amber-50 text-amber-700',
    queued: 'bg-amber-50 text-amber-700',
    failed: 'bg-red-50 text-red-600',
    'dead-letter': 'bg-red-50 text-red-600',
  };
  const cls = map[status] ?? 'bg-gray-100 text-gray-600';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${cls}`}>
      {toChineseValue(status)}
    </span>
  );
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);

  const offset = page * PAGE_SIZE;
  const hasPrev = page > 0;
  const hasNext = offset + jobs.length < total;

  const hasDeadLetter = useMemo(() => jobs.some((j) => j.status === 'dead-letter'), [jobs]);

  async function refresh() {
    setLoading(true);
    setError('');
    try {
      const all = await listJobs({ status: status || undefined, q: search || undefined, limit: PAGE_SIZE, offset });
      // 当没有筛选状态时，同时拉取死信任务合并展示
      if (!status) {
        const dl = await listDeadLetterJobs({ q: search || undefined, limit: 100 });
        const dlIds = new Set((dl.items || []).map((j: JobItem) => j.job_id));
        const merged = [
          ...(dl.items || []),
          ...(all.items || []).filter((j: JobItem) => !dlIds.has(j.job_id)),
        ];
        setJobs(merged);
        setTotal((all.total || 0) + (dl.items?.length || 0));
      } else {
        setJobs(all.items || []);
        setTotal(all.total || 0);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function onRequeue(jobId: string) {
    try {
      await requeueJob(jobId);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, [status, search, page]);

  return (
    <Shell>
      <div className="px-4 py-6 md:px-8 md:py-8">
        {/* 页头 */}
        <div className="mb-6">
          <h1 className="text-xl font-bold text-gray-900">任务列表</h1>
          <p className="text-sm text-gray-400 mt-1">共 {total} 个任务</p>
        </div>

        {/* 死信提示 */}
        {hasDeadLetter && (
          <div className="mb-4 px-3 py-2 bg-amber-50 border border-amber-100 rounded-lg text-xs text-amber-700">
            死信任务已达重试上限，可点"重入队"人工恢复。
          </div>
        )}

        {/* 工具栏 */}
        <div className="flex flex-wrap gap-2 mb-4">
          <input
            type="text"
            placeholder="搜索任务 ID / 快照 ID..."
            value={search}
            onChange={(e) => { setPage(0); setSearch(e.target.value); }}
            className="flex-1 min-w-0 border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-1"
          />
          <select
            value={status}
            onChange={(e) => { setPage(0); setStatus(e.target.value); }}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-1"
          >
            <option value="">全部状态</option>
            <option value="queued">{toChineseValue('queued')}</option>
            <option value="running">{toChineseValue('running')}</option>
            <option value="completed">{toChineseValue('completed')}</option>
            <option value="failed">{toChineseValue('failed')}</option>
            <option value="dead-letter">{toChineseValue('dead-letter')}</option>
          </select>
          <button
            onClick={refresh}
            disabled={loading}
            className="border border-gray-200 rounded-lg px-4 py-2 text-sm bg-white hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            {loading ? '刷新中...' : '刷新'}
          </button>
        </div>

        {/* 桌面：表格 */}
        <div className="hidden md:block bg-white border border-gray-100 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">{toChineseFieldName('job_id')}</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">{toChineseFieldName('status')}</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">{toChineseFieldName('retry_count')}</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">{toChineseFieldName('created_at')}</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {jobs.map((j) => (
                <tr key={j.job_id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <a href={`/jobs/${j.job_id}`} className="font-mono text-blue-600 hover:underline text-xs">
                      {j.job_id}
                    </a>
                  </td>
                  <td className="px-4 py-3">{statusBadge(j.status)}</td>
                  <td className="px-4 py-3 text-gray-500">{j.retry_count ?? 0}/{j.max_retries ?? 0}</td>
                  <td className="px-4 py-3 text-gray-500">{j.created_at}</td>
                  <td className="px-4 py-3">
                    {(j.status === 'dead-letter' || j.status === 'failed') ? (
                      <button
                        onClick={() => onRequeue(j.job_id)}
                        className="text-xs border border-gray-200 rounded-md px-2 py-1 hover:bg-gray-50 transition-colors"
                      >
                        重入队
                      </button>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                </tr>
              ))}
              {jobs.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-400">暂无任务</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* 手机：卡片列表 */}
        <div className="md:hidden space-y-2">
          {jobs.map((j) => (
            <div key={j.job_id} className="bg-white border border-gray-100 rounded-xl p-4">
              <div className="flex items-start justify-between gap-2 mb-1">
                <a href={`/jobs/${j.job_id}`} className="font-mono text-blue-600 hover:underline text-xs break-all">
                  {j.job_id}
                </a>
                {statusBadge(j.status)}
              </div>
              <div className="text-xs text-gray-400">{j.created_at} · 重试 {j.retry_count ?? 0}/{j.max_retries ?? 0}</div>
              {(j.status === 'dead-letter' || j.status === 'failed') && (
                <button
                  onClick={() => onRequeue(j.job_id)}
                  className="mt-2 text-xs border border-gray-200 rounded-md px-2 py-1 hover:bg-gray-50 transition-colors"
                >
                  重入队
                </button>
              )}
            </div>
          ))}
          {jobs.length === 0 && (
            <p className="text-center text-sm text-gray-400 py-8">暂无任务</p>
          )}
        </div>

        {/* 分页 */}
        <div className="flex items-center gap-2 mt-4">
          <button
            disabled={!hasPrev}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm disabled:opacity-40 hover:bg-gray-50 transition-colors"
          >
            上一页
          </button>
          <span className="text-sm text-gray-500">第 {page + 1} 页</span>
          <button
            disabled={!hasNext}
            onClick={() => setPage((p) => p + 1)}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm disabled:opacity-40 hover:bg-gray-50 transition-colors"
          >
            下一页
          </button>
        </div>

        {error && (
          <p className="mt-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
            {error}
          </p>
        )}
      </div>
    </Shell>
  );
}
```

- [ ] **Step 2: 验证 TypeScript 无报错**

```bash
cd /Users/didi/Desktop/code/regression-analysis/apps/web
npx tsc --noEmit
```

- [ ] **Step 3: 浏览器验证**

打开 http://localhost:3000/jobs，检查：
- 桌面宽度：表格正常显示
- 手机宽度（浏览器缩窄到 < 768px）：切换为卡片列表，底部 Tab 栏可见
- 状态 badge 颜色正确（完成绿、运行中黄、失败红）

- [ ] **Step 4: 提交**

```bash
git add app/jobs/page.tsx
git commit -m "feat(web): redesign jobs list page with Tailwind"
```

---

## Task 5: 重写任务详情页

**Files:**
- Modify: `apps/web/app/jobs/[id]/page.tsx`

指标卡片网格、图表并排（桌面）、可折叠时间线和原始 JSON。

- [ ] **Step 1: 完整替换 jobs/[id]/page.tsx**

```tsx
// apps/web/app/jobs/[id]/page.tsx
'use client';

import { useEffect, useMemo, useState } from 'react';
import Shell from '../../components/Shell';
import { localizeData, toChineseFieldName, toChineseValue } from '../../../lib/field_localizer';
import { getJob, getJobResult } from '../../../lib/api';

type EquityItem = { day?: string; equity?: number };

const CHART_W = 860;
const CHART_H = 260;
const PAD = 28;

function buildLinePath(values: number[], min: number, max: number) {
  if (values.length < 2) return '';
  const range = max - min;
  const iw = CHART_W - PAD * 2;
  const ih = CHART_H - PAD * 2;
  const pts = values.map((v, i) => {
    const x = PAD + (i / (values.length - 1)) * iw;
    const r = range === 0 ? 0.5 : (max - v) / range;
    const y = PAD + r * ih;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });
  return `M ${pts.join(' L ')}`;
}

function formatMetricValue(key: string, value: number) {
  const k = key.toLowerCase();
  if (k.includes('drawdown') || k.includes('volatility') || k.includes('return')) {
    return `${(value * 100).toFixed(2)}%`;
  }
  if (k.includes('ratio')) return value.toFixed(3);
  return value.toFixed(6);
}

function isNegative(key: string, value: number) {
  return key.toLowerCase().includes('drawdown') && value < 0;
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    completed: 'bg-green-50 text-green-700',
    running: 'bg-amber-50 text-amber-700',
    queued: 'bg-amber-50 text-amber-700',
    failed: 'bg-red-50 text-red-600',
    'dead-letter': 'bg-red-50 text-red-600',
  };
  const cls = map[status] ?? 'bg-gray-100 text-gray-600';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${cls}`}>
      ● {toChineseValue(status)}
    </span>
  );
}

function LineChart({ title, values, startLabel, endLabel, stroke }: {
  title: string; values: number[]; startLabel: string; endLabel: string; stroke: string;
}) {
  if (!values.length) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const path = buildLinePath(values, min, max);
  return (
    <div className="bg-white border border-gray-100 rounded-xl p-4">
      <p className="text-xs font-semibold text-gray-900 mb-3">{title}</p>
      <svg viewBox={`0 0 ${CHART_W} ${CHART_H}`} width="100%" height={CHART_H * 0.4}>
        <rect width={CHART_W} height={CHART_H} fill="#fff" />
        {[0.25, 0.5, 0.75].map((r) => (
          <line
            key={r}
            x1={PAD} y1={PAD + (CHART_H - PAD * 2) * r}
            x2={CHART_W - PAD} y2={PAD + (CHART_H - PAD * 2) * r}
            stroke="#f3f4f6" strokeWidth="1"
          />
        ))}
        {path && <path d={path} fill="none" stroke={stroke} strokeWidth="2" />}
      </svg>
      <div className="flex justify-between text-xs text-gray-400 mt-1">
        <span>{startLabel}</span>
        <span>min {min.toFixed(4)} / max {max.toFixed(4)}</span>
        <span>{endLabel}</span>
      </div>
    </div>
  );
}

const METRIC_ORDER = ['annualized_return', 'annualized_volatility', 'max_drawdown', 'sharpe_ratio', 'sortino_ratio', 'calmar_ratio'];

export default function JobPage({ params }: { params: { id: string } }) {
  const [status, setStatus] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [timelineOpen, setTimelineOpen] = useState(true);
  const [jsonOpen, setJsonOpen] = useState(false);

  useEffect(() => {
    const terminal = new Set(['completed', 'failed', 'dead-letter']);
    let timer: ReturnType<typeof setInterval> | null = null;
    const refresh = async () => {
      try {
        const s = await getJob(params.id);
        setStatus(s);
        if (s.status === 'completed' && !result) {
          setResult(await getJobResult(params.id));
        }
        if (terminal.has(s.status) && timer) clearInterval(timer);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    };
    void refresh();
    timer = setInterval(refresh, 2000);
    return () => { if (timer) clearInterval(timer); };
  }, [params.id, result]);

  const metrics: Record<string, number> = result?.metrics ?? {};
  const metricKeys = Array.from(new Set([...METRIC_ORDER, ...Object.keys(metrics)]));

  const equityCurve = useMemo(() => {
    const raw = (result?.equity_curve ?? []) as EquityItem[];
    return raw.map((p) => ({ day: String(p.day || ''), equity: Number(p.equity ?? NaN) }))
               .filter((p) => Number.isFinite(p.equity));
  }, [result]);

  const equityValues = equityCurve.map((p) => p.equity);
  const drawdownValues = useMemo(() => {
    let peak = -Infinity;
    return equityValues.map((v) => {
      peak = Math.max(peak, v);
      if (!isFinite(peak) || peak <= 0) return 0;
      return (v - peak) / peak;
    });
  }, [equityValues]);

  const startDay = equityCurve[0]?.day || '-';
  const endDay = equityCurve[equityCurve.length - 1]?.day || '-';
  const events = Array.isArray(status?.events) ? status.events : [];
  const localizedStatus = localizeData(status);

  return (
    <Shell>
      <div className="px-4 py-6 md:px-8 md:py-8 max-w-4xl">
        {/* 面包屑 */}
        <a href="/jobs" className="text-xs text-gray-400 hover:text-gray-600 transition-colors">← 任务列表</a>

        {/* 任务标题 */}
        <div className="flex flex-wrap items-center gap-3 mt-3 mb-6">
          <h1 className="text-lg font-bold font-mono text-gray-900">{params.id}</h1>
          {status && (
            <>
              {statusBadge(status.status)}
              <span className="text-xs text-gray-400">重试 {status.retry_count}/{status.max_retries}</span>
            </>
          )}
        </div>

        {!status && !error && (
          <p className="text-sm text-gray-400">加载中...</p>
        )}

        {/* 指标卡片 */}
        {result && (
          <>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">核心指标</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
              {metricKeys.map((key) => {
                if (typeof metrics[key] !== 'number') return null;
                const val = metrics[key];
                return (
                  <div key={key} className="bg-white border border-gray-100 rounded-xl p-4">
                    <p className="text-xs text-gray-400 mb-1">{toChineseFieldName(key)}</p>
                    <p className={`text-xl font-bold ${isNegative(key, val) ? 'text-red-500' : 'text-gray-900'}`}>
                      {formatMetricValue(key, val)}
                    </p>
                  </div>
                );
              })}
            </div>

            {/* 图表 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
              <LineChart title="净值曲线" values={equityValues} startLabel={startDay} endLabel={endDay} stroke="#111111" />
              <LineChart title="回撤曲线" values={drawdownValues} startLabel={startDay} endLabel={endDay} stroke="#ef4444" />
            </div>
          </>
        )}

        {/* 执行时间线 */}
        {status && (
          <div className="bg-white border border-gray-100 rounded-xl overflow-hidden mb-3">
            <button
              type="button"
              onClick={() => setTimelineOpen((v) => !v)}
              className="w-full flex items-center justify-between px-4 py-3 text-sm hover:bg-gray-50 transition-colors"
            >
              <span className="font-semibold text-gray-900">执行时间线</span>
              <span className="text-xs text-gray-400">{timelineOpen ? '收起 ▴' : '展开 ▾'}</span>
            </button>
            {timelineOpen && (
              <div className="px-4 pb-4 space-y-3 border-t border-gray-100">
                {events.length === 0 && <p className="text-sm text-gray-400 mt-3">暂无事件</p>}
                {events.map((event: any, idx: number) => (
                  <div key={`${event.at}-${idx}`} className="flex items-start gap-3 mt-3">
                    <span className="mt-1 w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
                    <div>
                      <span className="text-sm font-semibold text-gray-900">{toChineseValue(event.type || 'event')}</span>
                      <span className="text-xs text-gray-400 ml-2">@ {event.at || '-'}</span>
                      {event.error && <p className="text-xs text-red-500 mt-0.5">错误: {event.error}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 原始 JSON */}
        {status && (
          <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
            <button
              type="button"
              onClick={() => setJsonOpen((v) => !v)}
              className="w-full flex items-center justify-between px-4 py-3 text-sm hover:bg-gray-50 transition-colors"
            >
              <span className="font-semibold text-gray-500">原始 JSON 数据</span>
              <span className="text-xs text-gray-400">{jsonOpen ? '收起 ▴' : '展开 ▾'}</span>
            </button>
            {jsonOpen && (
              <pre className="px-4 pb-4 text-xs text-gray-600 overflow-auto border-t border-gray-100 mt-0 bg-gray-50">
                {JSON.stringify(localizedStatus, null, 2)}
              </pre>
            )}
          </div>
        )}

        {error && (
          <p className="mt-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
            {error}
          </p>
        )}
      </div>
    </Shell>
  );
}
```

- [ ] **Step 2: 验证 TypeScript 无报错**

```bash
cd /Users/didi/Desktop/code/regression-analysis/apps/web
npx tsc --noEmit
```

- [ ] **Step 3: 验证构建通过**

```bash
npm run build
```

Expected: Build 成功，无报错。

- [ ] **Step 4: 浏览器验证详情页**

打开 http://localhost:3000/jobs/（任意已存在任务 ID），检查：
- 指标卡片 3 列（桌面）/ 2 列（手机）
- 图表并排（桌面）/ 单列（手机）
- 时间线默认展开，可折叠
- 原始 JSON 默认折叠，点击展开

- [ ] **Step 5: 提交**

```bash
git add app/jobs/\[id\]/page.tsx
git commit -m "feat(web): redesign job detail page with Tailwind"
```

---

## Self-Review 结果

**Spec 覆盖检查：**
- Tailwind CSS 安装 ✓ Task 1
- Shell 组件（侧边栏 + 底部 Tab 栏）✓ Task 2
- 提交页两栏 + 高级折叠 ✓ Task 3
- 任务列表桌面表格 / 手机卡片 ✓ Task 4
- 详情页指标网格 + 并排图表 + 折叠时间线 + 折叠 JSON ✓ Task 5
- 死信提示文案 ✓ Task 4（hasDeadLetter 提示）
- 状态 badge 颜色系统 ✓ Task 4 & 5（statusBadge 函数）

**类型一致性：**
- `statusBadge` 函数在 Task 4 和 Task 5 各自独立定义（两个文件），避免共享依赖。✓
- `buildLinePath`、`formatMetricValue`、`isNegative` 仅在 Task 5 使用，命名与实现一致。✓

**无占位符确认：** 所有步骤均包含完整代码块。✓
