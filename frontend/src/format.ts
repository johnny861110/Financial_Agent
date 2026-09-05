export function number(value: unknown, digits = 0): string { return typeof value === 'number' && Number.isFinite(value) ? new Intl.NumberFormat('zh-TW', { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value) : '—'; }
export function percent(value: unknown, digits = 1): string { return typeof value === 'number' && Number.isFinite(value) ? `${number(value, digits)}%` : '—'; }
export function confidence(value: unknown): string { return typeof value === 'number' && Number.isFinite(value) ? percent(value * 100, 0) : '—'; }
export function safeUrl(value: unknown): string | null { if (typeof value !== 'string') return null; try { const u = new URL(value); return u.protocol === 'http:' || u.protocol === 'https:' ? u.href : null; } catch { return null; } }
