"""API-backed ROIC versus WACC filing analysis."""

import json

import streamlit as st

from ui.api_client import api_request, describe_api_error
from ui.data_source import period_input, render_data_source


def _render_result(result: dict, stock_code: str, period: str) -> None:
    st.markdown("---")
    st.success(f"Loaded ROIC/WACC for {stock_code} · {period}")
    st.caption(
        "Rates and spreads are decimals in the API payload; displayed rates are percentages."
    )
    metrics = [
        ("ROIC", result.get("roic")),
        ("WACC", result.get("wacc")),
        ("Value Creation Gap", result.get("value_creation_gap")),
    ]
    st.dataframe(
        [
            {"Metric": name, "Value": "N/A" if value is None else f"{value * 100:.2f}%"}
            for name, value in metrics
        ],
        use_container_width=True,
        hide_index=True,
    )
    if result.get("is_value_creating") is not None:
        (st.success if result["is_value_creating"] else st.warning)(
            "Value creating (ROIC exceeds WACC)."
            if result["is_value_creating"]
            else "Not value creating (ROIC does not exceed WACC)."
        )
    for name in ("nopat", "invested_capital"):
        if result.get(name) is not None:
            st.metric(name.replace("_", " ").title(), f"{result[name]:,.2f} (API filing units)")
    if result.get("commentary"):
        st.subheader("Commentary")
        st.write(result["commentary"])
    if result.get("assumptions"):
        with st.expander("Assumptions used by the API"):
            st.json(result["assumptions"])
    st.download_button(
        "Download JSON",
        json.dumps(result, indent=2, ensure_ascii=False),
        f"{stock_code}_{period}_roic_wacc.json",
        "application/json",
    )


def show() -> None:
    """Display filing-backed ROIC/WACC analysis with caller-supplied assumptions."""
    st.title("💰 ROIC vs WACC Analysis")
    st.markdown("Evaluate value creation using filing data and clearly labeled assumptions.")
    stock_code = st.text_input("Stock Code", value="3661", key="roic_wacc_stock")
    period = period_input(stock_code, key="roic_wacc_period")
    with st.form("roic_wacc_form"):
        beta = st.number_input("Beta assumption", min_value=0.0, value=1.0, step=0.1)
        cost_of_debt = st.number_input(
            "Pre-tax cost of debt assumption", min_value=0.0, value=0.05, step=0.01, format="%.3f"
        )
        tax_rate = st.number_input(
            "Tax rate assumption",
            min_value=0.0,
            max_value=1.0,
            value=0.21,
            step=0.01,
            format="%.2f",
        )
        submitted = st.form_submit_button(
            "🔍 Analyze Filing", type="primary", disabled=period is None
        )
    with st.sidebar:
        render_data_source()
    if submitted and period:
        try:
            with st.spinner("Loading ROIC/WACC analysis..."):
                result = api_request(
                    "POST",
                    f"/api/roic_wacc/{stock_code}/{period}",
                    json={"beta": beta, "cost_of_debt": cost_of_debt, "tax_rate": tax_rate},
                )
            st.session_state.roic_wacc_result = result
            st.session_state.roic_wacc_identity = (stock_code, period)
        except Exception as exc:
            st.error(f"❌ {describe_api_error(exc)}")
    result = st.session_state.get("roic_wacc_result")
    if result and st.session_state.get("roic_wacc_identity") == (stock_code, period):
        _render_result(result, stock_code, period)
