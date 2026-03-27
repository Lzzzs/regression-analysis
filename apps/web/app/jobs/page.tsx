'use client';

import { useEffect, useMemo, useState } from 'react';
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

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [dead, setDead] = useState<JobItem[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);

  const offset = page * PAGE_SIZE;
  const hasPrev = page > 0;
  const hasNext = offset + jobs.length < total;

  async function refresh() {
    setLoading(true);
    setError('');
    try {
      const all = await listJobs({ status: status || undefined, q: search || undefined, limit: PAGE_SIZE, offset });
      const dl = await listDeadLetterJobs({ q: search || undefined, limit: 100 });
      setJobs(all.items || []);
      setTotal(all.total || 0);
      setDead(dl.items || []);
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

  const deadHint = useMemo(() => {
    if (!dead.length) return '';
    return '死信任务已达到当前重试上限，可点“重入队”人工恢复并重新计数。';
  }, [dead]);

  return (
    <main style={{ maxWidth: 1100, margin: '40px auto', background: '#fff', padding: 24, borderRadius: 12 }}>
      <h1 style={{ marginTop: 0 }}>任务列表</h1>
      <p><a href="/">返回实验提交</a></p>

      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12 }}>
        <input
          placeholder="搜索任务ID / 状态 / 快照ID"
          value={search}
          onChange={(e) => {
            setPage(0);
            setSearch(e.target.value);
          }}
          style={{ width: 340 }}
        />
        <select
          value={status}
          onChange={(e) => {
            setPage(0);
            setStatus(e.target.value);
          }}
        >
          <option value="">全部状态</option>
          <option value="queued">{toChineseValue('queued')}</option>
          <option value="running">{toChineseValue('running')}</option>
          <option value="completed">{toChineseValue('completed')}</option>
          <option value="failed">{toChineseValue('failed')}</option>
          <option value="dead-letter">{toChineseValue('dead-letter')}</option>
        </select>
        <button onClick={refresh} disabled={loading}>{loading ? '刷新中...' : '手动刷新'}</button>
      </div>

      <h2>全部任务（{total}）</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th align="left">{toChineseFieldName('job_id')}</th>
            <th align="left">{toChineseFieldName('status')}</th>
            <th align="left">{toChineseFieldName('retry_count')}</th>
            <th align="left">{toChineseFieldName('remaining_retries')}</th>
            <th align="left">{toChineseFieldName('created_at')}</th>
            <th align="left">操作</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((j) => (
            <tr key={j.job_id}>
              <td><a href={`/jobs/${j.job_id}`}>{j.job_id}</a></td>
              <td>{toChineseValue(j.status)}</td>
              <td>{j.retry_count ?? 0}/{j.max_retries ?? 0}</td>
              <td>{j.remaining_retries ?? 0}</td>
              <td>{j.created_at}</td>
              <td>
                {j.status === 'dead-letter' || j.status === 'failed' ? (
                  <button onClick={() => onRequeue(j.job_id)}>重入队</button>
                ) : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
        <button disabled={!hasPrev} onClick={() => setPage((p) => Math.max(0, p - 1))}>上一页</button>
        <button disabled={!hasNext} onClick={() => setPage((p) => p + 1)}>下一页</button>
        <span>第 {page + 1} 页</span>
      </div>

      <h2>死信任务（{dead.length}）</h2>
      {deadHint ? <p style={{ color: '#914f00' }}>{deadHint}</p> : null}
      <ul>
        {dead.map((j) => (
          <li key={j.job_id}>
            {j.job_id}
            {' '}
            （重试 {j.retry_count ?? 0}/{j.max_retries ?? 0}，剩余 {j.remaining_retries ?? 0}，错误 {j.error || '无'}）
            {' '}
            <button onClick={() => onRequeue(j.job_id)}>重入队</button>
          </li>
        ))}
      </ul>

      {error ? <p style={{ color: 'crimson' }}>{error}</p> : null}
    </main>
  );
}
