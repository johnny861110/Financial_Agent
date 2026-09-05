import type { components } from './api.generated';

export type Json = Record<string, unknown>;
export type Page = 'snapshot' | 'trend' | 'peers' | 'management' | 'earnings' | 'roic' | 'factors' | 'ews' | 'capital' | 'agent';
export type Mode = 'auto' | 'quick' | 'research';
// Derived from the backend's OpenAPI schema (see package.json's generate:api) so a
// backend contract change fails typecheck here instead of silently drifting, as it
// did before (Snapshot and EarlyWarningResponse shape mismatches).
export type Snapshot = components['schemas']['FinancialSnapshotResponse'];
export type AgentResponse = components['schemas']['AgentResponse'];
export interface AgentHistory { schemaVersion: 1; id: string; savedAt: string; stockCode: string; period: string; query: string; mode: Mode; response: AgentResponse }
