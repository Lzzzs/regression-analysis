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
