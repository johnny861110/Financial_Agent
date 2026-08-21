# Sample Financial Data

The default JSON provider reads enhanced files from
`data/financial_reports/<stock_code>_<period>_enhanced.json`.

```json
{
  "stock_code": "3661",
  "company_name": "Example Company",
  "report_year": 2025,
  "report_season": 1,
  "report_period": "2025Q1",
  "currency": "TWD",
  "unit": "thousand",
  "cash_and_equivalents": 38262852.0,
  "accounts_receivable": 2794776.0,
  "inventory": 5754313.0,
  "total_assets": 52621348.0,
  "total_liabilities": 15818473.0,
  "equity": 41588114.0,
  "net_revenue": 318737.0,
  "gross_profit": 73833.0,
  "operating_income": 45431.0,
  "net_income": 44424.0,
  "eps": 0.55,
  "current_assets": null,
  "current_liabilities": null,
  "short_term_debt": null,
  "long_term_debt": null,
  "retained_earnings": null,
  "operating_cash_flow": null,
  "investing_cash_flow": null,
  "financing_cash_flow": null
}
```

## Conventions

- Periods use uppercase `YYYYQn`, for example `2025Q1`.
- Monetary values use the declared currency and unit consistently.
- Unknown optional values should be `null`, not zero. Zero is a real financial
  value and changes formulas.
- `stock_code`, `report_period`, currency, and unit must describe the same
  filing as the filename.
- The loader calculates derived ratios such as margins, debt ratio, ROA, and
  ROE from source fields.

For trends, provide multiple periods for one stock. For peers/factors, provide
the same period for multiple stocks.

## Evidence Behavior

The JSON provider creates field-level evidence references to the source
filename for every non-null snapshot field. This makes local development
auditable but does not provide filing page citations.

The remote FinancialReports provider should return document-grade evidence:

```json
{
  "field": "net_revenue",
  "source_type": "filing",
  "page_number": 12,
  "section_title": "Consolidated Statements of Comprehensive Income",
  "excerpt": "Revenue ...",
  "confidence": 0.99
}
```

The complete remote response fixture is
`tests/fixtures/financial_reports_snapshot_v1.json`.

## Missing Data

Different tools need different fields. A snapshot may load successfully while
ROIC/WACC, earnings quality, factor, or EWS analysis is gated. Missing fields
are returned explicitly in API and Agent responses; they must not be silently
replaced with zero.
