"""Snapshot service for single-period financial analysis."""

from typing import Optional
from app.models import FinancialSnapshot
from app.core import DataLoader, enrich_snapshot
from app.data import CanonicalFinancialContext


class SnapshotService:
    """Service for loading and analyzing single financial snapshots."""

    def __init__(self, data_loader: DataLoader | None = None):
        self.data_loader = data_loader or DataLoader()

    def get_snapshot(self, stock_code: str, period: str) -> Optional[FinancialSnapshot]:
        """
        Get enriched financial snapshot for a specific period.

        Args:
            stock_code: Stock ticker code
            period: Period identifier (e.g., '2023Q3')

        Returns:
            Enriched FinancialSnapshot or None if not found
        """
        snapshot = self.data_loader.load_snapshot(stock_code, period)
        if snapshot:
            return enrich_snapshot(snapshot)
        return None

    def get_summary(self, stock_code: str, period: str) -> Optional[dict]:
        """
        Get structured summary of financial snapshot.

        Args:
            stock_code: Stock ticker code
            period: Period identifier

        Returns:
            Dictionary with key metrics and analysis
        """
        context = self.data_loader.load_context(stock_code, period)
        if not context or not context.has_analysis_data:
            return None

        snapshot = context.record.snapshot
        if snapshot is None:
            return None

        # Every canonical monetary field the producer publishes, not just the
        # headline ones. A number that exists upstream and is not surfaced here
        # is a number the agent has to go looking for in filing prose, where
        # the same term appears for prior periods and for segments -- so the
        # answer comes back real but attached to the wrong period.
        money_fields = [
            # income statement
            "net_revenue",
            "gross_profit",
            "operating_income",
            "profit_before_tax",
            "net_income",
            "net_income_attributable_to_parent",
            "operating_expenses",
            "rd_expenses",
            "tax_expense",
            "comprehensive_income",
            "net_interest_income",
            "net_non_interest_income",
            "loan_loss_provisions",
            # balance sheet
            "cash_and_equivalents",
            "accounts_receivable",
            "inventory",
            "current_assets",
            "total_assets",
            "accounts_payable",
            "current_liabilities",
            "total_liabilities",
            "equity",
            "equity_attributable_to_parent",
            "retained_earnings",
            "share_capital",
            # cash flow
            "operating_cash_flow",
            "investing_cash_flow",
            "financing_cash_flow",
            "capex",
            "free_cash_flow",
            "cash_beginning",
            "cash_ending",
        ]

        def money(field: str) -> float | None:
            return context.optional_value(field, "TWD_thousands")

        def rounded(value: float | None) -> float | None:
            return round(value, 2) if value is not None else None

        current_assets = money("current_assets")
        current_liabilities = money("current_liabilities")
        current_ratio = context.metric_value("current_ratio", "ratio")
        if (
            current_ratio is None
            and current_assets is not None
            and current_liabilities is not None
            and current_liabilities != 0
        ):
            current_ratio = current_assets / current_liabilities

        return {
            "identification": {
                "stock_code": snapshot.stock_code,
                "company_name": snapshot.company_name,
                "period": snapshot.report_period,
                "currency": snapshot.currency,
                "unit": snapshot.unit,
            },
            "income_statement": {
                "net_revenue": money("net_revenue"),
                "gross_profit": money("gross_profit"),
                "operating_income": money("operating_income"),
                "profit_before_tax": money("profit_before_tax"),
                "net_income": money("net_income"),
                "net_income_attributable_to_parent": money("net_income_attributable_to_parent"),
                "operating_expenses": money("operating_expenses"),
                "rd_expenses": money("rd_expenses"),
                "tax_expense": money("tax_expense"),
                "comprehensive_income": money("comprehensive_income"),
                "net_interest_income": money("net_interest_income"),
                "net_non_interest_income": money("net_non_interest_income"),
                "loan_loss_provisions": money("loan_loss_provisions"),
                "eps": context.optional_value("eps_basic", "TWD_per_share"),
                "eps_diluted": context.optional_value("eps_diluted", "TWD_per_share"),
            },
            "margins": {
                "gross_margin": rounded(
                    context.ratio_percent("gross_margin", "gross_profit", "net_revenue")
                ),
                "operating_margin": rounded(
                    context.ratio_percent("operating_margin", "operating_income", "net_revenue")
                ),
                "net_margin": rounded(
                    context.ratio_percent("net_margin", "net_income", "net_revenue")
                ),
            },
            "balance_sheet": {
                "cash_and_equivalents": money("cash_and_equivalents"),
                "accounts_receivable": money("accounts_receivable"),
                "inventory": money("inventory"),
                "current_assets": money("current_assets"),
                "total_assets": money("total_assets"),
                "accounts_payable": money("accounts_payable"),
                "current_liabilities": money("current_liabilities"),
                "total_liabilities": money("total_liabilities"),
                "equity": money("equity"),
                "equity_attributable_to_parent": money("equity_attributable_to_parent"),
                "retained_earnings": money("retained_earnings"),
                "share_capital": money("share_capital"),
            },
            "cash_flow": {
                "operating_cash_flow": money("operating_cash_flow"),
                "investing_cash_flow": money("investing_cash_flow"),
                "financing_cash_flow": money("financing_cash_flow"),
                "capex": money("capex"),
                "free_cash_flow": money("free_cash_flow"),
                "cash_beginning": money("cash_beginning"),
                "cash_ending": money("cash_ending"),
            },
            "financial_structure": {
                "debt_ratio": rounded(
                    context.ratio_percent("debt_ratio", "total_liabilities", "total_assets")
                ),
                "equity_ratio": rounded(
                    context.ratio_percent("equity_ratio", "equity", "total_assets")
                ),
                "current_ratio": rounded(current_ratio),
            },
            "returns": {
                "roa": rounded(
                    context.ratio_percent("roa", "net_income", "total_assets", annualize=4)
                ),
                "roe": rounded(context.ratio_percent("roe", "net_income", "equity", annualize=4)),
            },
            "data_context": {
                "schema_version": context.record.schema_version,
                "status": context.record.status,
                "quality_score": context.quality.score,
                "is_stale": context.freshness.is_stale,
                "field_states": context.field_states(money_fields + ["eps_basic"]),
                "failed_validations": [
                    item.model_dump(mode="json") for item in context.failed_validations()
                ],
            },
        }
