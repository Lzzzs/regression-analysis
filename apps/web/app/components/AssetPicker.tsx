'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { AssetItem, searchAssets } from '../../lib/api';

export type SelectedAsset = {
  code: string;
  name: string;
  market: string;
  asset_type: string;
  weight: number; // 0-100 integer percent
};

type Props = {
  value: SelectedAsset[];
  onChange: (v: SelectedAsset[]) => void;
};

const MARKETS = [
  { key: 'cn', label: 'A股' },
  { key: 'us', label: '美股' },
  { key: 'hk', label: '港股' },
  { key: 'crypto', label: '加密' },
] as const;

const WEIGHT_STEP = 5;

export default function AssetPicker({ value, onChange }: Props) {
  const [market, setMarket] = useState<string>('cn');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<AssetItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doSearch = useCallback(async (q: string, m: string) => {
    setSearching(true);
    try {
      const data = await searchAssets({ q, market: m, limit: 50 });
      setResults(data.items);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }, []);

  // Fetch on market change or initial load
  useEffect(() => {
    setQuery('');
    doSearch('', market);
  }, [market, doSearch]);

  // Debounced search on query change
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      doSearch(query, market);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, market, doSearch]);

  const selectedCodes = new Set(value.map((a) => a.code));

  function toggleAsset(item: AssetItem) {
    if (selectedCodes.has(item.code)) {
      const next = value.filter((a) => a.code !== item.code);
      onChange(autoDistribute(next));
    } else {
      const next = [...value, { ...item, weight: 0 }];
      onChange(autoDistribute(next));
    }
  }

  function autoDistribute(assets: SelectedAsset[]): SelectedAsset[] {
    if (assets.length === 0) return assets;
    const base = Math.floor(100 / assets.length);
    const remainder = 100 - base * assets.length;
    return assets.map((a, i) => ({ ...a, weight: i === 0 ? base + remainder : base }));
  }

  function updateWeight(code: string, delta: number) {
    onChange(
      value.map((a) =>
        a.code === code ? { ...a, weight: Math.max(0, Math.min(100, a.weight + delta)) } : a
      )
    );
  }

  function setWeightDirect(code: string, raw: string) {
    const num = parseInt(raw, 10);
    if (isNaN(num)) return;
    onChange(
      value.map((a) =>
        a.code === code ? { ...a, weight: Math.max(0, Math.min(100, num)) } : a
      )
    );
  }

  function removeAsset(code: string) {
    onChange(autoDistribute(value.filter((a) => a.code !== code)));
  }

  function distributeEvenly() {
    if (value.length === 0) return;
    const base = Math.floor(100 / value.length);
    const remainder = 100 - base * value.length;
    onChange(
      value.map((a, i) => ({ ...a, weight: i === 0 ? base + remainder : base }))
    );
  }

  function clearAll() {
    onChange([]);
  }

  const totalWeight = value.reduce((sum, a) => sum + a.weight, 0);
  const weightOk = totalWeight === 100;
  const weightOver = totalWeight > 100;

  return (
    <div className="flex flex-col md:flex-row gap-0 border border-gray-200 rounded-xl overflow-hidden bg-white min-h-[360px]">
      {/* Left panel: search + list */}
      <div className="md:w-72 border-b md:border-b-0 md:border-r border-gray-100 flex flex-col">
        {/* Mobile collapse toggle */}
        <button
          type="button"
          className="md:hidden flex items-center justify-between px-4 py-3 text-sm text-gray-600 border-b border-gray-100"
          onClick={() => setPanelOpen((v) => !v)}
        >
          <span className="font-medium">选择产品</span>
          <span className="text-gray-400 text-xs">{panelOpen ? '收起 ▴' : '展开 ▾'}</span>
        </button>

        <div className={`${panelOpen ? 'flex' : 'hidden'} md:flex flex-col flex-1`}>
          {/* Market tabs */}
          <div className="flex border-b border-gray-100">
            {MARKETS.map((m) => (
              <button
                key={m.key}
                type="button"
                onClick={() => setMarket(m.key)}
                className={`flex-1 py-2 text-xs font-medium transition-colors ${
                  market === m.key
                    ? 'text-gray-900 border-b-2 border-gray-900'
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          {/* Search input */}
          <div className="px-3 py-2 border-b border-gray-100">
            <input
              type="text"
              placeholder="搜索代码或名称…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-1"
            />
          </div>

          {/* Results list */}
          <div className="flex-1 overflow-y-auto max-h-64 md:max-h-[400px]">
            {searching && (
              <p className="px-4 py-3 text-xs text-gray-400">搜索中…</p>
            )}
            {!searching && results.length === 0 && (
              <p className="px-4 py-3 text-xs text-gray-400">无结果</p>
            )}
            {!searching &&
              results.map((item) => {
                const selected = selectedCodes.has(item.code);
                return (
                  <button
                    key={item.code}
                    type="button"
                    onClick={() => toggleAsset(item)}
                    className={`w-full flex items-center gap-2 px-4 py-2 text-left hover:bg-gray-50 transition-colors ${
                      selected ? 'bg-blue-50' : ''
                    }`}
                  >
                    <span
                      className={`w-4 h-4 flex-shrink-0 rounded border text-xs flex items-center justify-center ${
                        selected
                          ? 'bg-gray-900 border-gray-900 text-white'
                          : 'border-gray-300'
                      }`}
                    >
                      {selected && '✓'}
                    </span>
                    <span className="flex-1 min-w-0">
                      <span className="text-xs font-mono text-gray-900">{item.code}</span>
                      <span className="ml-2 text-xs text-gray-500 truncate">{item.name}</span>
                    </span>
                  </button>
                );
              })}
          </div>
        </div>
      </div>

      {/* Right panel: selected assets + weight allocation */}
      <div className="flex-1 flex flex-col">
        {/* Weight summary */}
        <div className="px-4 py-3 border-b border-gray-100">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-gray-500">权重合计</span>
            <span
              className={`text-xs font-bold tabular-nums ${
                weightOk ? 'text-green-600' : weightOver ? 'text-red-600' : 'text-amber-600'
              }`}
            >
              {totalWeight}%
              {weightOk && ' ✓'}
              {!weightOk && !weightOver && ` (还差 ${100 - totalWeight}%)`}
              {weightOver && ' (超出!)'}
            </span>
          </div>
          <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                weightOk ? 'bg-green-500' : weightOver ? 'bg-red-500' : 'bg-amber-400'
              }`}
              style={{ width: `${Math.min(totalWeight, 100)}%` }}
            />
          </div>
        </div>

        {/* Selected asset list */}
        <div className="flex-1 overflow-y-auto">
          {value.length === 0 && (
            <div className="flex items-center justify-center h-24 text-xs text-gray-400">
              从左侧选择产品
            </div>
          )}
          {value.map((a) => (
            <div
              key={a.code}
              className="flex items-center gap-2 px-4 py-2.5 border-b border-gray-50 last:border-b-0"
            >
              <div className="flex-1 min-w-0">
                <span className="text-xs font-mono font-semibold text-gray-900">{a.code}</span>
                <span className="ml-2 text-xs text-gray-500 truncate">{a.name}</span>
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                <button
                  type="button"
                  onClick={() => updateWeight(a.code, -WEIGHT_STEP)}
                  className="w-6 h-6 flex items-center justify-center rounded border border-gray-200 text-gray-500 hover:bg-gray-100 text-sm"
                >
                  −
                </button>
                <input
                  type="number"
                  value={a.weight}
                  min={0}
                  max={100}
                  onChange={(e) => setWeightDirect(a.code, e.target.value)}
                  className="w-12 text-center text-xs border border-gray-200 rounded px-1 py-1 focus:outline-none focus:ring-1 focus:ring-gray-900"
                />
                <span className="text-xs text-gray-400">%</span>
                <button
                  type="button"
                  onClick={() => updateWeight(a.code, WEIGHT_STEP)}
                  className="w-6 h-6 flex items-center justify-center rounded border border-gray-200 text-gray-500 hover:bg-gray-100 text-sm"
                >
                  +
                </button>
                <button
                  type="button"
                  onClick={() => removeAsset(a.code)}
                  className="w-6 h-6 flex items-center justify-center rounded text-gray-300 hover:text-red-500 hover:bg-red-50 text-sm ml-1"
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Footer actions */}
        {value.length > 0 && (
          <div className="flex gap-2 px-4 py-3 border-t border-gray-100">
            <button
              type="button"
              onClick={distributeEvenly}
              className="flex-1 text-xs border border-gray-200 rounded-lg py-1.5 text-gray-600 hover:bg-gray-50 transition-colors"
            >
              均分权重
            </button>
            <button
              type="button"
              onClick={clearAll}
              className="text-xs border border-gray-200 rounded-lg px-3 py-1.5 text-gray-400 hover:text-red-500 hover:border-red-200 transition-colors"
            >
              清空
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
