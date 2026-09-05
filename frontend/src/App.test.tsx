import { fireEvent, render, screen, waitFor, cleanup } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from './App';

afterEach(cleanup);
beforeEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    const body = url.includes('/stocks') ? { stocks: ['2330'] } : url.includes('/periods') ? { periods: ['2025Q1'] } : {
      identification: { stock_code: '2330', company_name: '測試公司', period: '2025Q1', currency: 'TWD', unit: 'thousand' },
      income_statement: { net_revenue: null, gross_profit: null, operating_income: null, net_income: 100, eps: null },
      margins: { gross_margin: null, operating_margin: null, net_margin: null },
      balance_sheet: { total_assets: null, total_liabilities: null, equity: null, cash_and_equivalents: null },
      financial_structure: { debt_ratio: null, equity_ratio: null, current_ratio: null },
      returns: { roa: null, roe: null },
      data_context: { schema_version: '1', status: 'ok', quality_score: null, is_stale: false, field_states: { net_revenue: 'missing' }, failed_validations: [] },
      units: {},
    };
    return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
  }) as typeof fetch;
});

describe('workbench', () => {
  it('renders nullable snapshot values as em dashes', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByLabelText('報告期間')).toHaveValue('2025Q1'));
    fireEvent.change(screen.getByLabelText('報告期間'), { target: { value: '2025Q1' } });
    fireEvent.click(screen.getByText('執行分析'));
    await waitFor(() => expect(screen.getAllByText('—').length).toBeGreaterThan(0));
  });
  it('shows request failure honestly', async () => {
    globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/stocks')) return Promise.resolve(new Response(JSON.stringify({ stocks: ['2330'] }), { status: 200 }));
      if (url.includes('/periods')) return Promise.resolve(new Response(JSON.stringify({ periods: ['2025Q1'] }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({ detail: 'provider unavailable' }), { status: 503 }));
    }) as typeof fetch;
    render(<App />);
    await waitFor(() => expect(screen.getByLabelText('報告期間')).toHaveValue('2025Q1'));
    fireEvent.change(screen.getByLabelText('報告期間'), { target: { value: '2025Q1' } });
    fireEvent.click(screen.getByText('執行分析'));
    await waitFor(() => expect(screen.getByText('provider unavailable')).toBeInTheDocument());
  });
  it('calls GET-only analysis endpoints with GET, not POST', async () => {
    render(<App />);
    fireEvent.click(screen.getByText('早期預警'));
    await waitFor(() => expect(screen.getByLabelText('報告期間')).toHaveValue('2025Q1'));
    fireEvent.click(screen.getByText('送出後端分析'));
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining('/api/ews/'), expect.not.objectContaining({ method: 'POST' })));
  });
  it('sends research mode to the unified query endpoint', async () => {
    render(<App />);
    fireEvent.click(screen.getByText('Agent Research'));
    fireEvent.change(screen.getByLabelText('期間'), { target: { value: '2025Q1' } });
    fireEvent.change(screen.getByDisplayValue('Auto'), { target: { value: 'research' } });
    fireEvent.change(screen.getByLabelText('研究問題'), { target: { value: '研究問題' } });
    fireEvent.click(screen.getByText('送出研究問題'));
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledWith('/api/agent/query', expect.objectContaining({ method: 'POST', body: expect.stringContaining('"mode":"research"') })));
  });
});
