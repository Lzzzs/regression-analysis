'use client';

import { useEffect, useMemo, useState } from 'react';
import { localizeData, toChineseFieldName, toChineseValue } from '../../../lib/field_localizer';
import { getJob, getJobResult } from '../../../lib/api';

type EquityItem = {
  day?: string;
  equity?: number;
};

const CHART_WIDTH = 860;
const CHART_HEIGHT = 260;
const CHART_PADDING = 28;

function buildLinePath(values: number[], min: number, max: number) {
  if (values.length < 2) return '';
  const range = max - min;
  const innerW = CHART_WIDTH - CHART_PADDING * 2;
  const innerH = CHART_HEIGHT - CHART_PADDING * 2;
  const points = values.map((v, i) => {
    const x = CHART_PADDING + (i / (values.length - 1)) * innerW;
    const ratio = range === 0 ? 0.5 : (max - v) / range;
    const y = CHART_PADDING + ratio * innerH;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });
  return `M ${points.join(' L ')}`;
}

function formatMetricValue(key: string, value: number) {
  const normalized = key.toLowerCase();
  if (normalized.includes('drawdown') || normalized.includes('volatility') || normalized.includes('return')) {
    return `${(value * 100).toFixed(2)}%`;
  }
  if (normalized.includes('ratio')) {
    return value.toFixed(3);
  }
  return value.toFixed(6);
}

function MetricCards({ metrics }: { metrics: Record<string, number> }) {
  const ordered = ['annualized_return', 'annualized_volatility', 'max_drawdown', 'sharpe_ratio', 'sortino_ratio', 'calmar_ratio'];
  const keys = Array.from(new Set([...ordered, ...Object.keys(metrics)]));
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
      {keys.map((key) => {
        if (typeof metrics[key] !== 'number') return null;
        const value = metrics[key] as number;
        return (
          <div
            key={key}
            style={{
              border: '1px solid #e5e7eb',
              borderRadius: 10,
              padding: 12,
              background: '#fafafa',
            }}
          >
            <div style={{ fontSize: 12, color: '#666' }}>{toChineseFieldName(key)}</div>
            <div style={{ fontSize: 20, fontWeight: 700, marginTop: 6 }}>{formatMetricValue(key, value)}</div>
          </div>
        );
      })}
    </div>
  );
}

function LineChart({
  title,
  values,
  startLabel,
  endLabel,
  stroke,
}: {
  title: string;
  values: number[];
  startLabel: string;
  endLabel: string;
  stroke: string;
}) {
  if (!values.length) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const path = buildLinePath(values, min, max);
  return (
    <section style={{ marginTop: 10 }}>
      <h3 style={{ marginBottom: 8 }}>{title}</h3>
      <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 8 }}>
        <svg viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} width="100%" height={CHART_HEIGHT}>
          <rect x="0" y="0" width={CHART_WIDTH} height={CHART_HEIGHT} fill="#fff" />
          {[0.25, 0.5, 0.75].map((r) => (
            <line
              key={r}
              x1={CHART_PADDING}
              y1={CHART_PADDING + (CHART_HEIGHT - CHART_PADDING * 2) * r}
              x2={CHART_WIDTH - CHART_PADDING}
              y2={CHART_PADDING + (CHART_HEIGHT - CHART_PADDING * 2) * r}
              stroke="#f0f0f0"
            />
          ))}
          {path ? <path d={path} fill="none" stroke={stroke} strokeWidth="2.5" /> : null}
        </svg>
        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#666', fontSize: 12 }}>
          <span>{startLabel}</span>
          <span>
            最小: {min.toFixed(4)} | 最大: {max.toFixed(4)}
          </span>
          <span>{endLabel}</span>
        </div>
      </div>
    </section>
  );
}

export default function JobPage({ params }: { params: { id: string } }) {
  const [status, setStatus] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const terminalStates = new Set(['completed', 'failed', 'dead-letter']);
    let timer: ReturnType<typeof setInterval> | null = null;
    const refresh = async () => {
      try {
        const nextStatus = await getJob(params.id);
        setStatus(nextStatus);
        if (nextStatus.status === 'completed' && !result) {
          const nextResult = await getJobResult(params.id);
          setResult(nextResult);
        }
        if (terminalStates.has(nextStatus.status) && timer) {
          clearInterval(timer);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    };
    void refresh();
    timer = setInterval(refresh, 2000);
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [params.id, result]);

  const payloadSummary = status?.payload_summary ?? {};
  const events = Array.isArray(status?.events) ? status.events : [];
  const localizedPayloadSummary = localizeData(payloadSummary);
  const localizedStatus = localizeData(status);
  const localizedMetrics = localizeData(result?.metrics ?? {});
  const localizedEquityCurve = localizeData(result?.equity_curve?.slice(0, 20) ?? []);

  const equityCurve = useMemo(() => {
    const raw = (result?.equity_curve ?? []) as EquityItem[];
    return raw
      .map((p) => ({ day: String(p.day || ''), equity: Number(p.equity ?? NaN) }))
      .filter((p) => Number.isFinite(p.equity));
  }, [result]);

  const equityValues = equityCurve.map((p) => p.equity);
  const drawdownValues = useMemo(() => {
    let peak = Number.NEGATIVE_INFINITY;
    return equityValues.map((v) => {
      peak = Math.max(peak, v);
      if (!Number.isFinite(peak) || peak <= 0) return 0;
      return (v - peak) / peak;
    });
  }, [equityValues]);

  const startDay = equityCurve[0]?.day || '-';
  const endDay = equityCurve[equityCurve.length - 1]?.day || '-';

  return (
    <main style={{ maxWidth: 900, margin: '40px auto', background: '#fff', padding: 24, borderRadius: 12 }}>
      <h1>任务 {params.id}</h1>
      {status ? (
        <>
          <h2>状态摘要</h2>
          <p>
            当前状态: <strong>{toChineseValue(status.status)}</strong>
          </p>
          <p>
            重试: {status.retry_count}/{status.max_retries}，剩余 {status.remaining_retries}
          </p>
          <h2>输入摘要</h2>
          <pre>{JSON.stringify(localizedPayloadSummary, null, 2)}</pre>
          <h2>执行时间线</h2>
          {events.length ? (
            <ol style={{ paddingLeft: 20 }}>
              {events.map((event: any, idx: number) => (
                <li key={`${event.at || 'na'}-${event.type || 'event'}-${idx}`}>
                  <strong>{toChineseValue(event.type || 'event')}</strong> @ {event.at || '-'}
                  {event.error ? ` | 错误: ${event.error}` : ''}
                  {typeof event.retry_count === 'number' ? ` | 重试: ${event.retry_count}` : ''}
                </li>
              ))}
            </ol>
          ) : (
            <p>暂无事件</p>
          )}
          <h2>完整状态 JSON</h2>
          <pre>{JSON.stringify(localizedStatus, null, 2)}</pre>
        </>
      ) : (
        <p>加载中...</p>
      )}
      {result ? (
        <>
          <h2>核心指标</h2>
          <MetricCards metrics={result.metrics || {}} />
          <LineChart title="净值曲线" values={equityValues} startLabel={startDay} endLabel={endDay} stroke="#1463ff" />
          <LineChart title="回撤曲线" values={drawdownValues} startLabel={startDay} endLabel={endDay} stroke="#d14343" />
          <h2>指标明细（中文字段）</h2>
          <pre>{JSON.stringify(localizedMetrics, null, 2)}</pre>
          <h2>净值序列样本（前20点）</h2>
          <pre>{JSON.stringify(localizedEquityCurve, null, 2)}</pre>
        </>
      ) : null}
      {error ? <p style={{ color: 'crimson' }}>{error}</p> : null}
    </main>
  );
}
