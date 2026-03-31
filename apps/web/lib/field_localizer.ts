const FIELD_MAP: Record<string, string> = {
  job_id: '任务ID',
  snapshot_id: '快照ID',
  run_id: '运行ID',
  status: '状态',
  created_at: '创建时间',
  started_at: '开始时间',
  finished_at: '完成时间',
  dead_lettered_at: '终止时间',
  retry_count: '重试次数',
  max_retries: '最大重试次数',
  remaining_retries: '剩余重试次数',
  error: '错误信息',
  payload_summary: '输入摘要',
  events: '事件列表',
  metrics: '指标',
  equity_curve: '净值曲线',
  base_currency: '基准币种',
  start_date: '开始日期',
  end_date: '结束日期',
  rebalance_frequency: '再平衡频率',
  weights: '组合权重',
  coverage: '覆盖区间',
  traceability: '可追溯信息',
  sources: '数据来源',
  integrity: '完整性校验',
  algorithm: '算法',
  checksum_sha256: 'SHA256校验和',
  total: '总数',
  count: '数量',
  limit: '每页条数',
  offset: '偏移量',
  items: '列表项',
  type: '类型',
  pair: '货币对',
  close: '收盘价',
  rate: '汇率',
  source: '来源',
};

const TOKEN_MAP: Record<string, string> = {
  job: '任务',
  id: 'ID',
  snapshot: '快照',
  run: '运行',
  status: '状态',
  created: '创建',
  started: '开始',
  finished: '完成',
  dead: '终止',
  letter: '信',
  retry: '重试',
  count: '次数',
  max: '最大',
  remaining: '剩余',
  error: '错误',
  payload: '输入',
  summary: '摘要',
  start: '开始',
  end: '结束',
  date: '日期',
  rebalance: '再平衡',
  frequency: '频率',
  base: '基准',
  currency: '币种',
  weight: '权重',
  weights: '权重',
  event: '事件',
  events: '事件',
  metric: '指标',
  metrics: '指标',
  equity: '净值',
  curve: '曲线',
  coverage: '覆盖',
  traceability: '可追溯',
  source: '来源',
  sources: '来源',
  integrity: '完整性',
  checksum: '校验和',
  algorithm: '算法',
  annualized: '年化',
  return: '收益',
  volatility: '波动率',
  drawdown: '回撤',
  sharpe: '夏普',
  sortino: '索提诺',
  calmar: '卡玛',
  ratio: '比率',
  total: '总',
  value: '值',
  queued: '排队中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  monthly: '月度',
  quarterly: '季度',
  none: '不再平衡',
};

const VALUE_MAP: Record<string, string> = {
  queued: '排队中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  'dead-letter': '已终止',
  none: '不再平衡',
  monthly: '月度',
  quarterly: '季度',
  created: '已创建',
  started: '已开始',
  retry_scheduled: '已安排重试',
  dead_lettered: '已终止',
  requeued: '已重入队',
};

function normalizeKey(key: string): string {
  return key
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .replace(/[-\s]+/g, '_')
    .toLowerCase();
}

function splitTokens(key: string): string[] {
  return normalizeKey(key).split('_').filter(Boolean);
}

function isLikelyCode(key: string): boolean {
  return /^[A-Z0-9./-]+$/.test(key);
}

export function toChineseFieldName(rawKey: string): string {
  if (FIELD_MAP[rawKey]) return FIELD_MAP[rawKey];
  const normalized = normalizeKey(rawKey);
  if (FIELD_MAP[normalized]) return FIELD_MAP[normalized];
  if (isLikelyCode(rawKey)) return rawKey;
  const tokens = splitTokens(rawKey);
  if (!tokens.length) return rawKey;
  return tokens.map((t) => TOKEN_MAP[t] ?? t).join('');
}

export function toChineseValue(rawValue: string): string {
  if (VALUE_MAP[rawValue]) return VALUE_MAP[rawValue];
  if (isLikelyCode(rawValue)) return rawValue;
  const normalized = normalizeKey(rawValue);
  if (TOKEN_MAP[normalized]) return TOKEN_MAP[normalized];
  const tokens = splitTokens(rawValue);
  if (!tokens.length) return rawValue;
  const mapped = tokens.map((t) => VALUE_MAP[t] ?? TOKEN_MAP[t] ?? t).join('');
  return mapped || rawValue;
}

function localizePrimitive(parentKey: string, value: unknown): unknown {
  if (value === null) return '空';
  if (typeof value === 'boolean') return value ? '是' : '否';
  if (typeof value !== 'string') return value;
  const key = normalizeKey(parentKey);
  if (key === 'status' || key === 'type' || key.endsWith('_status') || key.endsWith('_type')) {
    return toChineseValue(value);
  }
  if (key.endsWith('frequency')) {
    return toChineseValue(value);
  }
  return value;
}

export function localizeData(value: unknown, parentKey = ''): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => localizeData(item, parentKey));
  }
  if (value && typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(obj)) {
      const label = toChineseFieldName(key);
      out[label] = localizeData(val, key);
    }
    return out;
  }
  return localizePrimitive(parentKey, value);
}
