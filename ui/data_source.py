"""Shared data-source widgets for Streamlit pages.

Pages used to offer a free-text period box and a data-source selectbox that was
never read. Both let a request that cannot succeed reach the API: a period the
provider rejects, and a source the user believed they had chosen. These helpers
ask the backend what it can actually serve and say what it is actually using.
"""

import streamlit as st

from app.core import normalize_period
from ui.api_client import api_request, describe_api_error


# Streamlit reruns the whole script on every widget interaction, so discovery
# calls are cached: without a TTL the sidebar would re-query the API on every
# keystroke in the ticker box.
@st.cache_data(ttl=60, show_spinner=False)
def fetch_capabilities() -> dict:
    """Return the configured provider's capability document."""
    return api_request("GET", "/api/data/capabilities", timeout=10.0)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_stocks() -> list[str]:
    """Return every stock the configured provider can serve."""
    return list(api_request("GET", "/api/data/stocks", timeout=10.0).get("stocks", []))


@st.cache_data(ttl=60, show_spinner=False)
def fetch_periods(stock_code: str) -> list[str]:
    """Return the periods available for a stock, newest first, or [] on failure."""
    try:
        body = api_request("GET", f"/api/data/{stock_code}/periods", timeout=10.0)
    except Exception:  # noqa: BLE001 - callers fall back to free text
        return []
    return list(body.get("periods", []))


def clear_cache() -> None:
    """Drop every cached discovery response."""
    fetch_capabilities.clear()
    fetch_stocks.clear()
    fetch_periods.clear()


def render_data_source() -> None:
    """
    Show which provider is actually serving data.

    This replaces a selectbox that never affected anything. The provider is
    chosen by DATA_PROVIDER in the API container's environment, so the honest
    thing for the UI to do is report what the backend is really using.
    """
    st.markdown("**Data Source**")
    try:
        capabilities = fetch_capabilities()
    except Exception as exc:  # noqa: BLE001 - every failure is reportable here
        st.error(f"🔴 Data source unreachable — {describe_api_error(exc)}")
    else:
        if capabilities.get("api_version") == "v1":
            st.success(
                f"🟢 FinancialReports API {capabilities['api_version']} · "
                f"schema {capabilities.get('schema_version', '?')}"
            )
        else:
            st.warning(f"🟡 Local JSON files · schema {capabilities.get('schema_version', '?')}")
        try:
            st.caption(f"{len(fetch_stocks())} stocks available")
        except Exception:  # noqa: BLE001 - the count is a nicety, not a requirement
            pass

    if st.button("🔄 Recheck", use_container_width=True):
        clear_cache()
        st.rerun()


def period_input(stock_code: str, *, key: str, default: str = "2025Q1") -> str | None:
    """
    Offer the periods the backend can serve, or a validated text box.

    Returns the canonical YYYYQn period, or None when the typed value is not a
    period at all -- callers should not send that to the API.
    """
    periods = fetch_periods(stock_code)
    if periods:
        return st.selectbox(
            "Period",
            periods,
            key=key,
            help="Periods the configured data source can serve for this stock",
        )

    raw = st.text_input(
        "Period",
        value=default,
        key=key,
        help="Period list unavailable; enter one as YYYYQn (e.g. 2026Q1)",
    )
    period = normalize_period(raw)
    if period is None and raw:
        st.warning(f"`{raw}` is not a reporting period. Use YYYYQn, for example 2026Q1.")
    return period
