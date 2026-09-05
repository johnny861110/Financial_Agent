"""Financial Snapshot page."""

import streamlit as st

from ui.presentation import group_field_states
import pandas as pd
import plotly.graph_objects as go
from ui.api_client import api_request, describe_api_error
from ui.data_source import period_input


def _format_number(value, suffix: str = "", decimals: int = 2) -> str:
    """Format nullable API metrics without turning missing data into a crash."""
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}{suffix}"


def render_data_context(context: dict) -> None:
    """Show where the numbers came from and which of them are absent.

    A blank cell in the tables above can mean the filer does not report the
    field, the producer failed to supply it, or it is genuinely null. Those are
    different situations and the snapshot should say which.
    """
    if not context:
        return

    st.markdown("---")
    st.subheader("🧾 Data Context")

    columns = st.columns(3)
    columns[0].metric("Schema", str(context.get("schema_version") or "unknown"))
    columns[1].metric("Status", str(context.get("status") or "unknown"))
    quality = context.get("quality_score")
    columns[2].metric("Quality", f"{quality:.2f}" if isinstance(quality, (int, float)) else "n/a")

    if context.get("is_stale"):
        st.warning("This filing is stale — a newer source may exist.")

    failures = context.get("failed_validations") or []
    if failures:
        # Validation failures are not warnings: the producer is reporting that
        # a number did not reconcile.
        st.error(f"{len(failures)} validation rule(s) failed")
        for failure in failures:
            rule = failure.get("rule_name", "rule") if isinstance(failure, dict) else str(failure)
            message = failure.get("message") if isinstance(failure, dict) else None
            st.markdown(f"- **{rule}**" + (f" — {message}" if message else ""))

    groups = group_field_states(context.get("field_states") or {})
    absent = [group for group in groups if group.state != "present"]
    if absent:
        st.markdown("**Fields not available**")
        for group in absent:
            st.markdown(f"{group.icon} **{group.description}** — {', '.join(group.fields)}")
    elif groups:
        st.success("All requested fields are present.")


def show():
    """Display financial snapshot analysis page."""

    st.title("📈 Financial Snapshot Analysis")
    st.markdown("Analyze single-period financial metrics and derived ratios.")

    # Input section
    col1, col2 = st.columns(2)

    with col1:
        stock_code = st.text_input("Stock Code", value="3661", help="Enter the stock ticker code")

    with col2:
        period = period_input(stock_code, key="snapshot_period")

    if st.button("🔍 Analyze", type="primary", disabled=period is None):
        with st.spinner("Loading financial data..."):
            # Reporting the real failure matters: an unreachable API, a rejected
            # period and a genuine miss are three different problems that this
            # page used to render as the same "data not found".
            try:
                result = api_request("GET", f"/api/financials/{stock_code}/{period}")
            except Exception as exc:  # noqa: BLE001 - surfaced to the user
                st.error(f"❌ {describe_api_error(exc)}")
            else:
                st.session_state.snapshot_result = result
                st.session_state.snapshot_identity = (stock_code, period)

    result = st.session_state.get("snapshot_result")
    if result and st.session_state.get("snapshot_identity") == (stock_code, period):
        display_snapshot_results(result)


def display_snapshot_results(result):
    """Display snapshot analysis results."""

    # Company info
    st.success(
        f"✅ Loaded: **{result['identification']['company_name']}** - {result['identification']['period']}"
    )

    # Key metrics overview
    st.markdown("---")
    st.subheader("📊 Key Metrics Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        revenue = result["income_statement"]["net_revenue"]
        st.metric(
            "Net Revenue", _format_number(revenue, decimals=0), help="Net revenue for the period"
        )

    with col2:
        net_income = result["income_statement"]["net_income"]
        st.metric(
            "Net Income", _format_number(net_income, decimals=0), help="Net income for the period"
        )

    with col3:
        eps = result["income_statement"]["eps"]
        st.metric("EPS", _format_number(eps), help="Earnings per share")

    with col4:
        assets = result["balance_sheet"]["total_assets"]
        st.metric("Total Assets", _format_number(assets, decimals=0), help="Total assets")

    # Margins
    st.markdown("---")
    st.subheader("📈 Profitability Margins")

    margins = result["margins"]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Gross Margin", _format_number(margins.get("gross_margin"), "%"), delta=None)

    with col2:
        st.metric(
            "Operating Margin", _format_number(margins.get("operating_margin"), "%"), delta=None
        )

    with col3:
        st.metric("Net Margin", _format_number(margins.get("net_margin"), "%"), delta=None)

    # Margin chart
    fig = go.Figure(
        data=[
            go.Bar(
                x=["Gross Margin", "Operating Margin", "Net Margin"],
                y=[
                    margins.get("gross_margin") or 0,
                    margins.get("operating_margin") or 0,
                    margins.get("net_margin") or 0,
                ],
                marker_color=["#1f77b4", "#ff7f0e", "#2ca02c"],
                text=[
                    _format_number(margins.get("gross_margin"), "%", 1),
                    _format_number(margins.get("operating_margin"), "%", 1),
                    _format_number(margins.get("net_margin"), "%", 1),
                ],
                textposition="auto",
            )
        ]
    )

    fig.update_layout(
        title="Profitability Margins (%)",
        xaxis_title="Metric",
        yaxis_title="Percentage (%)",
        height=400,
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Financial Structure
    st.markdown("---")
    st.subheader("🏦 Financial Structure")

    structure = result["financial_structure"]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Debt Ratio",
            _format_number(structure.get("debt_ratio"), "%"),
            help="Total liabilities / Total assets",
        )

    with col2:
        st.metric(
            "Equity Ratio",
            _format_number(structure.get("equity_ratio"), "%"),
            help="Equity / Total assets",
        )

    with col3:
        if structure.get("current_ratio") is not None:
            st.metric(
                "Current Ratio",
                _format_number(structure.get("current_ratio")),
                help="Current assets / Current liabilities",
            )
        else:
            st.metric("Current Ratio", "N/A")

    # Structure pie chart
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Liabilities", "Equity"],
                values=[structure.get("debt_ratio") or 0, structure.get("equity_ratio") or 0],
                hole=0.4,
                marker_colors=["#ff7f0e", "#2ca02c"],
            )
        ]
    )

    fig.update_layout(
        title="Capital Structure",
        height=400,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Returns
    st.markdown("---")
    st.subheader("💰 Return Metrics")

    returns = result["returns"]

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "ROA (Annualized)", _format_number(returns.get("roa"), "%"), help="Return on Assets"
        )

    with col2:
        st.metric(
            "ROE (Annualized)", _format_number(returns.get("roe"), "%"), help="Return on Equity"
        )

    # Balance Sheet Details
    st.markdown("---")
    st.subheader("📋 Balance Sheet Details")

    balance_sheet_df = pd.DataFrame(
        {
            "Item": ["Total Assets", "Total Liabilities", "Equity", "Cash & Equivalents"],
            "Amount": [
                result["balance_sheet"]["total_assets"],
                result["balance_sheet"]["total_liabilities"],
                result["balance_sheet"]["equity"],
                result["balance_sheet"]["cash_and_equivalents"],
            ],
        }
    )

    st.dataframe(balance_sheet_df, use_container_width=True, hide_index=True)

    # Income Statement Details
    st.markdown("---")
    st.subheader("💵 Income Statement Details")

    income_df = pd.DataFrame(
        {
            "Item": ["Net Revenue", "Gross Profit", "Operating Income", "Net Income", "EPS"],
            "Amount": [
                result["income_statement"]["net_revenue"],
                result["income_statement"]["gross_profit"],
                result["income_statement"]["operating_income"],
                result["income_statement"]["net_income"],
                result["income_statement"]["eps"],
            ],
        }
    )

    st.dataframe(income_df, use_container_width=True, hide_index=True)

    render_data_context(result.get("data_context") or {})

    # Bind download directly to the persisted result so reruns do not erase it.
    st.markdown("---")
    import json

    st.download_button(
        label="📥 Download Full Report",
        data=json.dumps(result, indent=2, ensure_ascii=False),
        file_name=f"{result['identification']['stock_code']}_{result['identification']['period']}_snapshot.json",
        mime="application/json",
    )
