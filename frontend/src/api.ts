import type { AgentResponse, Json, Mode, Snapshot } from './types';

export class ApiError extends Error { constructor(public status: number, message: string, public body?: Json) { super(message); } }
export async function request<T>(path: string, init: RequestInit = {}, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { ...init, signal, headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) } });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) { const message = typeof body.detail === 'string' ? body.detail : body.message ?? body.error ?? `請求失敗（${response.status}）`; throw new ApiError(response.status, message, body); }
  return body as T;
}
export const getSnapshot = (stock: string, period: string, signal?: AbortSignal) => request<Snapshot>(`/api/financials/${encodeURIComponent(stock)}/${encodeURIComponent(period)}`, {}, signal);
export const getStocks = (signal?: AbortSignal) => request<{ stocks: string[] }>('/api/data/stocks', {}, signal);
export const getPeriods = (stock: string, signal?: AbortSignal) => request<{ periods: string[] }>(`/api/data/${encodeURIComponent(stock)}/periods`, {}, signal);
export const getAnalysis = <T>(path: string, signal?: AbortSignal) => request<T>(path, {}, signal);
export const postAnalysis = <T>(path: string, payload: Json, signal?: AbortSignal) => request<T>(path, { method: 'POST', body: JSON.stringify(payload) }, signal);
export const runAgent = (query: string, stockCode: string, period: string, mode: Mode, signal?: AbortSignal | AbortController) => postAnalysis<AgentResponse>('/api/agent/query', { query, stock_code: stockCode || null, period: period || null, mode }, signal instanceof AbortController ? signal.signal : signal);
