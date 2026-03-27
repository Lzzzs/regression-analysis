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
                    <span className="mt-1 w-2 h-2 rounded-full bg-green-400 flex-shrink:0" />
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
