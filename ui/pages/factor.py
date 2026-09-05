"""API-backed factor exposure filing analysis."""

import json

import streamlit as st

from ui.api_client import api_request, describe_api_error
from ui.data_source import period_input, render_data_source


def _render_result(result: dict, stock_code: str, period: str) -> None:
    st.markdown("---")
    st.success(f"Loaded factor exposure for {stock_code} · {period}")
    st.caption("Factor values are API-produced z-scores relative to the selected peer universe.")
    factors = {
        name: result.get(name) for name in ("quality", "value", "momentum", "size", "volatility")
    }
    st.dataframe(
        [
            {"Factor": name.title(), "Z-score": "N/A" if value is None else f"{value:.2f}σ"}
            for name, value in factors.items()
        ],
        use_container_width=True,
        hide_index=True,
    )
    if result.get("commentary"):
        st.subheader("Commentary")
        st.write(result["commentary"])
    if result.get("details"):
        with st.expander("Raw API metrics and units"):
            st.json(result["details"])
    st.download_button(
        "Download JSON",
        json.dumps(result, indent=2, ensure_ascii=False),
        f"{stock_code}_{period}_factors.json",
        "application/json",
    )


def show() -> None:
    """Display filing-backed factor exposures."""
    st.title("📐 Factor Exposure Analysis")
    st.markdown("Analyze the selected stock against API-provided peer statistics.")
    stock_code = st.text_input("Stock Code", value="3661", key="factor_stock")
    period = period_input(stock_code, key="factor_period")
    peers_raw = st.text_input(
        "Peer stocks (optional, comma-separated)", help="Passed to the API as the peer universe"
    )
    with st.sidebar:
        render_data_source()
    if st.button("🔍 Analyze Filing", type="primary", disabled=period is None) and period:
        try:
            peers = [item.strip() for item in peers_raw.split(",") if item.strip()] or None
            with st.spinner("Loading factor exposure analysis..."):
                result = api_request(
                    "POST", f"/api/factors/{stock_code}/{period}", json={"peer_stocks": peers}
                )
            st.session_state.factor_result = result
            st.session_state.factor_identity = (stock_code, period)
        except Exception as exc:
            st.error(f"❌ {describe_api_error(exc)}")
    result = st.session_state.get("factor_result")
    if result and st.session_state.get("factor_identity") == (stock_code, period):
        _render_result(result, stock_code, period)
