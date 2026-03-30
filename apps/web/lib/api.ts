export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export async function createJob(payload: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function createJobAuto(payload: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/jobs/auto`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function createSnapshotFromProviders(payload: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/snapshots/from-providers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getJob(jobId: string) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getJobResult(jobId: string) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/result`, { cache: 'no-store' });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

type ListJobsOptions = {
  status?: string;
  q?: string;
  limit?: number;
  offset?: number;
};

function toQuery(options: ListJobsOptions = {}) {
  const params = new URLSearchParams();
  if (options.status) params.set('status', options.status);
  if (options.q) params.set('q', options.q);
  if (typeof options.limit === 'number') params.set('limit', String(options.limit));
  if (typeof options.offset === 'number') params.set('offset', String(options.offset));
  const text = params.toString();
  return text ? `?${text}` : '';
}

export async function listJobs(options: ListJobsOptions = {}) {
  const res = await fetch(`${API_BASE}/jobs${toQuery(options)}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listDeadLetterJobs(options: Omit<ListJobsOptions, 'status'> = {}) {
  const res = await fetch(`${API_BASE}/jobs/dead-letter${toQuery(options)}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function requeueJob(jobId: string) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/requeue`, { method: 'POST' });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export type AssetItem = {
  code: string;
  name: string;
  market: string;
  asset_type: string;
};

export async function searchAssets(params: {
  q: string;
  market: string;
  limit?: number;
}): Promise<{ items: AssetItem[] }> {
  const query = new URLSearchParams({ q: params.q, market: params.market });
  if (params.limit != null) query.set('limit', String(params.limit));
  const res = await fetch(`${API_BASE}/assets/search?${query}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
