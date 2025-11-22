# Example: Sample Financial Data

Below is an example of the expected JSON format for financial data files.

Save this as `2330_2023Q3_enhanced.json` in your `data/financial_reports/` directory.

```json
{
  "stock_code": "2330",
  "company_name": "Taiwan Semiconductor Manufacturing Company",
  "report_year": 2023,
  "report_season": 3,
  "report_period": "2023Q3",
  "currency": "TWD",
  "unit": "thousand",
  
  "cash_and_equivalents": 1500000000,
  "accounts_receivable": 300000000,
  "inventory": 200000000,
  "total_assets": 5000000000,
  "total_liabilities": 2000000000,
  "equity": 3000000000,
  
  "net_revenue": 800000000,
  "gross_profit": 400000000,
  "operating_income": 350000000,
  "net_income": 300000000,
  "eps": 9.65,
  
  "current_assets": 1800000000,
  "current_liabilities": 600000000,
  "short_term_debt": 100000000,
  "long_term_debt": 500000000,
  "retained_earnings": 2000000000,
  
  "operating_cash_flow": 320000000,
  "investing_cash_flow": -150000000,
  "financing_cash_flow": -100000000
}
```

## Notes

1. All monetary values should be in the specified `unit` (typically "thousand" or "million")
2. The `stock_code` should match your company identifier
3. The `report_period` should follow the format: `YYYYQ#` (e.g., "2023Q3" for Q3 2023)
4. Optional fields (like `operating_cash_flow`) can be omitted if not available
5. The system will automatically calculate derived metrics like margins, ratios, ROE, ROA, etc.

## Creating Multiple Periods

For trend analysis, create multiple files for different periods:

- `2330_2023Q1_enhanced.json`
- `2330_2023Q2_enhanced.json`
- `2330_2023Q3_enhanced.json`
- `2330_2023Q4_enhanced.json`

## Creating Peer Companies

For peer comparison, create files for multiple companies in the same period:

- `2330_2023Q3_enhanced.json` (TSMC)
- `2454_2023Q3_enhanced.json` (MediaTek)
- `3711_2023Q3_enhanced.json` (ASE Technology)
