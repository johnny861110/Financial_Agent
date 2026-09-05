"""API-backed early warning filing analysis."""

import json

import streamlit as st

from ui.api_client import api_request, describe_api_error
from ui.data_source import period_input, render_data_source


def _render_result(result: dict, stock_code: str, period: str) -> None:
    st.markdown("---")
    st.success(f"Loaded early warnings for {stock_code} · {period}")
    st.caption(
        "Signals, severity, and thresholds below are returned by the API; no UI thresholds are simulated."
    )
    if result.get("warning_level"):
        st.metric("Warning Level", str(result["warning_level"]).upper())
    if result.get("signal_count") is not None:
        st.metric("Signal Count", result["signal_count"])
    for signal in result.get("triggered_signals") or []:
        st.warning(
            f"{signal.get('signal_name', 'Signal')} · {signal.get('severity', 'unknown')}: "
            f"{signal.get('description', '')} "
            f"(current {signal.get('current_value')}, threshold {signal.get('threshold_value')})"
        )
    if result.get("recommendation"):
        st.subheader("Recommendation")
        st.write(result["recommendation"])
    if result.get("commentary"):
        st.subheader("Commentary")
        st.write(result["commentary"])
    st.download_button(
        "Download JSON",
        json.dumps(result, indent=2, ensure_ascii=False),
        f"{stock_code}_{period}_ews.json",
        "application/json",
    )


def show() -> None:
    """Display filing-backed early warning signals."""
    st.title("🚨 Early Warning System")
    st.markdown("Monitor financial health using the backend's filing analysis.")
    stock_code = st.text_input("Stock Code", value="3661", key="ews_stock")
    period = period_input(stock_code, key="ews_period")
    with st.sidebar:
        render_data_source()
    if st.button("🔍 Run Warning Detection", type="primary", disabled=period is None) and period:
        try:
            with st.spinner("Loading early warning analysis..."):
                result = api_request("GET", f"/api/ews/{stock_code}/{period}")
            st.session_state.ews_result = result
            st.session_state.ews_identity = (stock_code, period)
        except Exception as exc:
            st.error(f"❌ {describe_api_error(exc)}")
    result = st.session_state.get("ews_result")
    if result and st.session_state.get("ews_identity") == (stock_code, period):
        _render_result(result, stock_code, period)
