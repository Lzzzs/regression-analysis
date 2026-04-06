// apps/web/app/jobs/[id]/page.tsx
'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import Shell from '../../components/Shell';
import { localizeData, toChineseFieldName, toChineseValue } from '../../../lib/field_localizer';
import { getJob, getJobResult } from '../../../lib/api';

type EquityItem = { day?: string; equity?: number };

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false });
  } catch { return iso; }
}

const CHART_WIDTH = 1100;
const CHART_HEIGHT = 400;
const CHART_PADDING = { top: 16, right: 16, bottom: 28, left: 56 };

function buildLinePath(values: number[], min: number, max: number) {
  if (values.length < 2) return '';
  const range = max - min;
  const innerW = CHART_WIDTH - CHART_PADDING.left - CHART_PADDING.right;
  const innerH = CHART_HEIGHT - CHART_PADDING.top - CHART_PADDING.bottom;
  const points = values.map((v, i) => {
    const x = CHART_PADDING.left + (i / (values.length - 1)) * innerW;
    const ratio = range === 0 ? 0.5 : (max - v) / range;
    const y = CHART_PADDING.top + ratio * innerH;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });
  return `M ${points.join(' L ')}`;
}

function formatYLabel(value: number, isPercent: boolean): string {
  if (isPercent) return `${(value * 100).toFixed(1)}%`;
  return value >= 1000 ? value.toFixed(0) : value.toFixed(2);
}

function formatMetricValue(key: string, value: number) {
  const k = key.toLowerCase();
  if (k.includes('days') || k.includes('duration')) {
    return `${Math.round(value)} 天`;
  }
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

function LineChart({ title, values, days, startLabel, endLabel, stroke, isPercent = false }: {
  title: string; values: number[]; days?: string[]; startLabel: string; endLabel: string; stroke: string; isPercent?: boolean;
}) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  if (!values.length) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min;
  const path = buildLinePath(values, min, max);
  const innerW = CHART_WIDTH - CHART_PADDING.left - CHART_PADDING.right;
  const innerH = CHART_HEIGHT - CHART_PADDING.top - CHART_PADDING.bottom;
  const gridLines = [0, 0.25, 0.5, 0.75, 1];

  function onMouseMove(e: React.MouseEvent<SVGSVGElement>) {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const svgX = ((e.clientX - rect.left) / rect.width) * CHART_WIDTH;
    const ratio = (svgX - CHART_PADDING.left) / innerW;
    const idx = Math.round(ratio * (values.length - 1));
    if (idx >= 0 && idx < values.length) setHoverIdx(idx);
    else setHoverIdx(null);
  }

  const hoverX = hoverIdx !== null ? CHART_PADDING.left + (hoverIdx / (values.length - 1)) * innerW : 0;
  const hoverY = hoverIdx !== null ? CHART_PADDING.top + (range === 0 ? 0.5 : (max - values[hoverIdx]) / range) * innerH : 0;
  const hoverVal = hoverIdx !== null ? values[hoverIdx] : 0;
  const hoverDay = hoverIdx !== null && days ? days[hoverIdx] : '';

  return (
    <div className="bg-white border border-gray-100 rounded-xl p-4">
      <p className="text-xs font-semibold text-gray-900 mb-3">{title}</p>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        className="w-full cursor-crosshair"
        preserveAspectRatio="xMidYMid meet"
        onMouseMove={onMouseMove}
        onMouseLeave={() => setHoverIdx(null)}
      >
        <rect width={CHART_WIDTH} height={CHART_HEIGHT} fill="#fff" />
        {gridLines.map((r) => {
          const y = CHART_PADDING.top + innerH * r;
          const val = max - (max - min) * r;
          return (
            <g key={r}>
              <line
                x1={CHART_PADDING.left} y1={y}
                x2={CHART_WIDTH - CHART_PADDING.right} y2={y}
                stroke="#f3f4f6" strokeWidth="1"
              />
              <text x={CHART_PADDING.left - 6} y={y + 4} textAnchor="end" fill="#9ca3af" fontSize="11">
                {formatYLabel(val, isPercent)}
              </text>
            </g>
          );
        })}
        {path && <path d={path} fill="none" stroke={stroke} strokeWidth="2.5" strokeLinejoin="round" />}
        {hoverIdx !== null && (
          <>
            <line x1={hoverX} y1={CHART_PADDING.top} x2={hoverX} y2={CHART_HEIGHT - CHART_PADDING.bottom} stroke="#9ca3af" strokeWidth="1" strokeDasharray="4 2" />
            <line x1={CHART_PADDING.left} y1={hoverY} x2={CHART_WIDTH - CHART_PADDING.right} y2={hoverY} stroke="#9ca3af" strokeWidth="1" strokeDasharray="4 2" />
            <circle cx={hoverX} cy={hoverY} r="5" fill={stroke} stroke="#fff" strokeWidth="2" />
            <rect x={hoverX - 70} y={hoverY - 44} width="140" height="36" rx="6" fill="#1f2937" opacity="0.9" />
            <text x={hoverX} y={hoverY - 28} textAnchor="middle" fill="#fff" fontSize="11" fontWeight="bold">
              {hoverDay ? `${hoverDay}` : ''}
            </text>
            <text x={hoverX} y={hoverY - 14} textAnchor="middle" fill="#d1d5db" fontSize="11">
              {formatYLabel(hoverVal, isPercent)}
            </text>
          </>
        )}
      </svg>
      <div className="flex justify-between text-xs text-gray-400 mt-1">
        <span>{startLabel}</span>
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

  const resultFetched = useRef(false);

  useEffect(() => {
    resultFetched.current = false;
    const terminal = new Set(['completed', 'failed', 'dead-letter']);
    let timer: ReturnType<typeof setInterval> | null = null;
    const refresh = async () => {
      try {
        const s = await getJob(params.id);
        setStatus(s);
        if (s.status === 'completed' && !resultFetched.current) {
          resultFetched.current = true;
          setResult(await getJobResult(params.id));
        }
        if (terminal.has(s.status) && timer) clearInterval(timer);
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        if (msg.includes('not found') || msg.includes('404')) {
          // Permanent error — stop polling
          if (timer) clearInterval(timer);
          setError('任务不存在，请检查任务 ID 是否正确');
        }
        // Transient errors: keep polling, don't overwrite existing status
      }
    };
    void refresh();
    timer = setInterval(refresh, 2000);
    return () => { if (timer) clearInterval(timer); };
  }, [params.id]);

  const metrics: Record<string, number> = result?.metrics ?? {};
  const metricKeys = Array.from(new Set([...METRIC_ORDER, ...Object.keys(metrics)]));

  const equityCurve = useMemo(() => {
    const raw = (result?.equity_curve ?? []) as EquityItem[];
    return raw.map((p) => ({ day: String(p.day || ''), equity: Number(p.equity ?? NaN) }))
               .filter((p) => Number.isFinite(p.equity));
  }, [result]);

  const equityValues = equityCurve.map((p) => p.equity);
  const equityDays = equityCurve.map((p) => p.day);
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
      <div className="px-4 py-6 md:px-8 md:py-8 max-w-6xl">
        {/* 面包屑 */}
        <Link href="/jobs" className="text-xs text-gray-400 hover:text-gray-600 transition-colors">← 任务列表</Link>

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

        {/* 组合配置 */}
        {status && status.payload_summary && (
          <div className="bg-white border border-gray-100 rounded-xl p-4 mb-6">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">组合配置</p>
            {status.payload_summary.weights && (() => {
              const assetNameMap: Record<string, string> = {};
              const assets = status.payload_summary?.assets || status.assets || status.selected_assets;
              if (Array.isArray(assets)) {
                assets.forEach((a: any) => { if (a.code && a.name) assetNameMap[a.code] = a.name; });
              }
              return (
                <div className="flex flex-wrap gap-2 mb-2">
                  {Object.entries(status.payload_summary.weights).map(([code, weight]: [string, any]) => (
                    <span key={code} className="bg-gray-100 text-gray-700 rounded-full px-2.5 py-0.5 text-xs font-mono">
                      {code}{assetNameMap[code] ? ` ${assetNameMap[code]}` : ''} {Math.round(weight * 100)}%
                    </span>
                  ))}
                </div>
              );
            })()}
            <p className="text-xs text-gray-500">
              {status.payload_summary.start_date} ~ {status.payload_summary.end_date}
              {status.payload_summary.rebalance_frequency && (
                <span> · {toChineseValue(status.payload_summary.rebalance_frequency)}再平衡</span>
              )}
            </p>
          </div>
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
            <div className="space-y-4 mb-6">
              <LineChart title="净值曲线" values={equityValues} days={equityDays} startLabel={startDay} endLabel={endDay} stroke="#111111" />
              <LineChart title="回撤曲线" values={drawdownValues} days={equityDays} startLabel={startDay} endLabel={endDay} stroke="#ef4444" isPercent />
            </div>

            {/* 年度收益分解 */}
            {Array.isArray(result.yearly_returns) && result.yearly_returns.length > 0 && (
              <div className="mb-6">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">年度收益分解</p>
                <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100">
                        <th className="text-left px-4 py-2 text-xs font-semibold text-gray-400">年份</th>
                        <th className="text-right px-4 py-2 text-xs font-semibold text-gray-400">年初净值</th>
                        <th className="text-right px-4 py-2 text-xs font-semibold text-gray-400">年末净值</th>
                        <th className="text-right px-4 py-2 text-xs font-semibold text-gray-400">收益率</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {result.yearly_returns.map((yr: any) => (
                        <tr key={yr.year}>
                          <td className="px-4 py-2 font-mono text-gray-900">{yr.year}</td>
                          <td className="px-4 py-2 text-right text-gray-500">{yr.start_equity?.toFixed(4)}</td>
                          <td className="px-4 py-2 text-right text-gray-500">{yr.end_equity?.toFixed(4)}</td>
                          <td className={`px-4 py-2 text-right font-semibold ${yr.return >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                            {(yr.return * 100).toFixed(2)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
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
                      <span className="text-xs text-gray-400 ml-2">@ {event.at ? formatTime(event.at) : '-'}</span>
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
