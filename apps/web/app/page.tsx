'use client';

import { FormEvent, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Shell from './components/Shell';
import AssetPicker, { SelectedAsset } from './components/AssetPicker';
import { createJobAuto } from '../lib/api';
import { toChineseValue } from '../lib/field_localizer';

function lastFriday(from?: Date): string {
  const d = from ? new Date(from) : new Date();
  d.setHours(0, 0, 0, 0);
  const day = d.getDay(); // 0=Sun..6=Sat
  const diff = day >= 5 ? day - 5 : day + 2; // days since last Friday
  d.setDate(d.getDate() - (diff === 0 ? 7 : diff)); // if today is Fri, use last Fri
  return d.toISOString().slice(0, 10);
}

function dateOffset(base: string, years: number): string {
  const d = new Date(base);
  d.setFullYear(d.getFullYear() - years);
  // Move to next Monday if it falls on weekend
  const day = d.getDay();
  if (day === 0) d.setDate(d.getDate() + 1);
  else if (day === 6) d.setDate(d.getDate() + 2);
  return d.toISOString().slice(0, 10);
}

const DEFAULT_END = lastFriday();
const DEFAULT_START = dateOffset(DEFAULT_END, 1);

export default function Page() {
  const router = useRouter();
  const [startDate, setStartDate] = useState(DEFAULT_START);
  const [endDate, setEndDate] = useState(DEFAULT_END);
  const [frequency, setFrequency] = useState('monthly');
  const [selectedAssets, setSelectedAssets] = useState<SelectedAsset[]>([]);
  const [requiredFxPairs, setRequiredFxPairs] = useState('');
  const [providerFiles, setProviderFiles] = useState('{}');
  const [jobId, setJobId] = useState('');
  const [snapshotId, setSnapshotId] = useState('');
  const [error, setError] = useState('');
  const [advanced, setAdvanced] = useState(false);
  const [loading, setLoading] = useState(false);
  const submittingRef = useRef(false);

  const totalWeight = selectedAssets.reduce((sum, a) => sum + a.weight, 0);
  const weightOver = totalWeight > 100;
  const weightOk = totalWeight === 100;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (submittingRef.current) return;
    if (!weightOk) {
      setError(weightOver ? '权重合计超过 100%，请调整后再提交' : '权重合计不足 100%，请调整后再提交');
      return;
    }
    // Date validations
    const start = new Date(startDate);
    const end = new Date(endDate);
    if (startDate >= endDate) {
      setError('开始日期必须早于结束日期');
      return;
    }
    if (end.getUTCDay() !== 5) {
      setError('结束日期必须为周五（快照发布要求）');
      return;
    }
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    if (end > today) {
      setError('结束日期不能是未来日期');
      return;
    }
    setError('');
    submittingRef.current = true;
    setLoading(true);
    try {
      let parsedProviderFiles = {};
      try {
        parsedProviderFiles = providerFiles.trim() ? JSON.parse(providerFiles) : {};
      } catch {
        setError('数据源文件配置 JSON 格式错误，请检查后重试');
        setLoading(false);
        return;
      }
      const weights = Object.fromEntries(
        selectedAssets.map((a) => [a.code, a.weight / 100])
      );
      const assets = selectedAssets.map((a) => ({
        code: a.code,
        market: a.market,
        asset_type: a.asset_type,
      }));
      const payload: Record<string, unknown> = {
        start_date: startDate,
        end_date: endDate,
        rebalance_frequency: frequency,
        base_currency: 'CNY',
        weights,
        assets,
        provider_files: parsedProviderFiles,
      };
      if (requiredFxPairs.trim()) {
        try {
          payload.required_fx_pairs = JSON.parse(requiredFxPairs);
        } catch {
          setError('汇率货币对 JSON 格式错误，请检查后重试');
          setLoading(false);
          return;
        }
      }
      const data = await createJobAuto(payload);
      setJobId(data.job_id);
      setSnapshotId(data.snapshot_id);
      router.push(`/jobs/${data.job_id}`);
    } catch (err) {
      const raw = err instanceof Error ? err.message : String(err);
      try {
        const parsed = JSON.parse(raw);
        setError(parsed.detail || raw);
      } catch {
        setError(raw);
      }
    } finally {
      submittingRef.current = false;
      setLoading(false);
    }
  }

  return (
    <Shell>
      <div className="px-4 py-6 md:px-8 md:py-8">
        {/* 页头 */}
        <div className="mb-6">
          <h1 className="text-xl font-bold text-gray-900">提交回测任务</h1>
          <p className="text-sm text-gray-400 mt-1">自动生成快照并创建分析任务</p>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          {/* 分析区间 + 频率 */}
          <div className="bg-white border border-gray-100 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">分析区间</p>
              <div className="flex gap-1.5">
                {[
                  { label: '近1年', years: 1 },
                  { label: '近3年', years: 3 },
                  { label: '近5年', years: 5 },
                ].map((preset) => (
                  <button
                    key={preset.years}
                    type="button"
                    onClick={() => {
                      setEndDate(DEFAULT_END);
                      setStartDate(dateOffset(DEFAULT_END, preset.years));
                    }}
                    className={`px-2.5 py-1 text-xs rounded-md border transition-colors ${
                      endDate === DEFAULT_END && startDate === dateOffset(DEFAULT_END, preset.years)
                        ? 'bg-gray-900 text-white border-gray-900'
                        : 'border-gray-200 text-gray-500 hover:border-gray-400'
                    }`}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
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
          </div>

          {/* 资产选择器 */}
          <div className="space-y-2">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">选择产品与权重</p>
            <AssetPicker value={selectedAssets} onChange={setSelectedAssets} />
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
                  <label className="block text-xs text-gray-500 mb-1 mt-3">汇率货币对 JSON（留空自动推断）</label>
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
            disabled={loading || selectedAssets.length === 0 || !weightOk}
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
