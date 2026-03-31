// apps/web/app/jobs/page.tsx
'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
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
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);

  const [debouncedSearch, setDebouncedSearch] = useState('');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const offset = page * PAGE_SIZE;
  const hasPrev = page > 0;
  const hasNext = offset + jobs.length < total;

  const hasDeadLetter = useMemo(() => jobs.some((j) => j.status === 'dead-letter'), [jobs]);

  // Debounce search input
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(search);
    }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [search]);

  async function refresh() {
    setLoading(true);
    setError('');
    try {
      const all = await listJobs({ status: status || undefined, q: debouncedSearch || undefined, limit: PAGE_SIZE, offset });
      // 当没有筛选状态时，同时拉取死信任务合并展示
      if (!status) {
        const dl = await listDeadLetterJobs({ q: debouncedSearch || undefined, limit: 100 });
        const dlIds = new Set((dl.items || []).map((j: JobItem) => j.job_id));
        const merged = [
          ...(dl.items || []),
          ...(all.items || []).filter((j: JobItem) => !dlIds.has(j.job_id)),
        ];
        setJobs(merged);
        setTotal(all.total || 0);
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
  }, [status, debouncedSearch, page]);

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
                    <Link href={`/jobs/${j.job_id}`} className="font-mono text-blue-600 hover:underline text-xs">
                      {j.job_id}
                    </Link>
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
              {loading && jobs.length === 0 && Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="animate-pulse">
                  <td className="px-4 py-3"><div className="h-3 bg-gray-100 rounded w-28" /></td>
                  <td className="px-4 py-3"><div className="h-3 bg-gray-100 rounded w-16" /></td>
                  <td className="px-4 py-3"><div className="h-3 bg-gray-100 rounded w-10" /></td>
                  <td className="px-4 py-3"><div className="h-3 bg-gray-100 rounded w-24" /></td>
                  <td className="px-4 py-3"><div className="h-3 bg-gray-100 rounded w-16" /></td>
                </tr>
              ))}
              {!loading && jobs.length === 0 && (
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
                <Link href={`/jobs/${j.job_id}`} className="font-mono text-blue-600 hover:underline text-xs break-all">
                  {j.job_id}
                </Link>
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
          {loading && jobs.length === 0 && Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-white border border-gray-100 rounded-xl p-4 animate-pulse">
              <div className="flex items-start justify-between gap-2 mb-1">
                <div className="h-3 bg-gray-100 rounded w-28" />
                <div className="h-3 bg-gray-100 rounded w-16" />
              </div>
              <div className="h-3 bg-gray-100 rounded w-24 mt-2" />
            </div>
          ))}
          {!loading && jobs.length === 0 && (
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
