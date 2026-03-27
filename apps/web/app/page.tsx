'use client';

import { FormEvent, useState } from 'react';
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

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError('');
    try {
      const parsedWeights = JSON.parse(weights);
      const parsedProviderFiles = providerFiles.trim() ? JSON.parse(providerFiles) : {};
      const payload: Record<string, unknown> = {
        start_date: startDate,
        end_date: endDate,
        rebalance_frequency: frequency,
        base_currency: 'CNY',
        weights: parsedWeights,
        provider_files: parsedProviderFiles
      };
      if (selectedAssets.trim()) payload.selected_assets = JSON.parse(selectedAssets);
      if (requiredFxPairs.trim()) payload.required_fx_pairs = JSON.parse(requiredFxPairs);
      const data = await createJobAuto(payload);
      setJobId(data.job_id);
      setSnapshotId(data.snapshot_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <main style={{ maxWidth: 900, margin: '40px auto', background: '#fff', padding: 24, borderRadius: 12 }}>
      <h1 style={{ marginTop: 0 }}>组合回测控制台</h1>
      <p>一次提交：自动生成快照并创建回测任务。</p>
      <p><a href="/jobs">查看任务列表 / 死信管理</a></p>
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <h2 style={{ marginBottom: 0 }}>提交组合并自动分析</h2>
        <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
        <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
        <select value={frequency} onChange={(e) => setFrequency(e.target.value)}>
          <option value="none">{toChineseValue('none')}</option>
          <option value="monthly">{toChineseValue('monthly')}</option>
          <option value="quarterly">{toChineseValue('quarterly')}</option>
        </select>
        <small>end_date 需要是周五（当前快照规则）。</small>
        <label>
          组合权重 JSON
          <textarea rows={4} value={weights} onChange={(e) => setWeights(e.target.value)} />
        </label>
        <label>
          资产列表 JSON（可选，留空则按权重推断）
          <textarea rows={2} value={selectedAssets} onChange={(e) => setSelectedAssets(e.target.value)} />
        </label>
        <label>
          汇率货币对 JSON（可选，留空自动推断）
          <textarea rows={2} value={requiredFxPairs} onChange={(e) => setRequiredFxPairs(e.target.value)} />
        </label>
        <label>
          数据源文件配置 JSON（可选，默认读取内置配置）
          <textarea rows={4} value={providerFiles} onChange={(e) => setProviderFiles(e.target.value)} />
        </label>
        <button type="submit">一键分析（自动生成快照+提交任务）</button>
      </form>
      {snapshotId ? <p>本次自动快照: {snapshotId}</p> : null}
      {jobId ? <p>已创建任务: <a href={`/jobs/${jobId}`}>{jobId}</a></p> : null}
      {error ? <p style={{ color: 'crimson' }}>{error}</p> : null}
    </main>
  );
}
