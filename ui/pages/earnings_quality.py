"""API-backed earnings quality filing analysis."""

import json

import streamlit as st

from ui.api_client import api_request, describe_api_error
from ui.data_source import period_input, render_data_source


def _render_result(result: dict, stock_code: str, period: str) -> None:
    st.markdown("---")
    st.success(f"Loaded earnings quality for {stock_code} · {period}")
    st.caption("Scores use a 0–100 scale. Amounts and ratios use the API's filing units.")
    if result.get("total_score") is not None:
        st.metric("Overall Score", f"{result['total_score']:.1f} / 100")
    components = result.get("components") or {}
    if components:
        st.subheader("Component Scores (0–100)")
        st.dataframe(
            [
                {"Component": name.replace("_", " ").title(), "Score": value}
                for name, value in components.items()
            ],
            use_container_width=True,
            hide_index=True,
        )
    for flag in result.get("red_flags") or []:
        st.warning(flag)
    if result.get("commentary"):
        st.subheader("Commentary")
        st.write(result["commentary"])
    if result.get("details"):
        with st.expander("API details and numeric units"):
            st.json(result["details"])
    st.download_button(
        "Download JSON",
        json.dumps(result, indent=2, ensure_ascii=False),
        f"{stock_code}_{period}_earnings_quality.json",
        "application/json",
    )


def show() -> None:
    """Display filing-backed earnings quality analysis."""
    st.title("💎 Earnings Quality Score")
    st.markdown("Assess earnings quality from the selected company's filing data.")
    stock_code = st.text_input("Stock Code", value="3661", key="earnings_quality_stock")
    period = period_input(stock_code, key="earnings_quality_period")
    with st.sidebar:
        render_data_source()
    if st.button("🔍 Analyze Filing", type="primary", disabled=period is None) and period:
        try:
            with st.spinner("Loading earnings quality analysis..."):
                result = api_request("GET", f"/api/scores/earnings_quality/{stock_code}/{period}")
            st.session_state.earnings_quality_result = result
            st.session_state.earnings_quality_identity = (stock_code, period)
        except Exception as exc:
            st.error(f"❌ {describe_api_error(exc)}")
    result = st.session_state.get("earnings_quality_result")
    if result and st.session_state.get("earnings_quality_identity") == (stock_code, period):
        _render_result(result, stock_code, period)
