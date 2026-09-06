"""Cross-repository smoke test against a running FinancialReports build.

Every other test in this suite mocks the producer, which proves the consumer
handles the shape it *expects*. This proves the producer actually serves that
shape: it talks to a real FinancialReports process over HTTP, so a contract
change on the producer side fails here rather than in production.

An unreachable producer is an **error**, not a skip. This file said as much
from the start -- "a smoke test that silently skips is worse than no smoke
test" -- but enforced it only in CI, and locally is where the seam actually
gets worked on. For a whole day this file reported "5 skipped" beside a green
217 while it was the only test covering the consumer/producer boundary, and the
producer was running the entire time.

The trap is that it is easy to hit while doing everything right: `.env` sets
FINANCIAL_REPORTS_BASE_URL to the compose hostname `http://financial-reports:8010`,
which resolves inside a container and nowhere else, and pytest does not read
`.env` anyway. So the variable is simply unset on the host and the tests
vanish.

Set FA_ALLOW_SMOKE_SKIP=1 to opt into running without a producer. That makes a
partial run a deliberate act rather than the default.
"""

from __future__ import annotations

import os

import pytest

from app.data.providers import FinancialReportsProvider

# The documented local producer port (DOCKER.md, NEXT_SESSION_PLAN §4). The
# compose hostname in .env is deliberately not the fallback: it resolves only
# inside the compose network, so defaulting to it would reintroduce the same
# silent absence one layer down.
DEFAULT_BASE_URL = "http://127.0.0.1:8010"
BASE_URL = os.getenv("FINANCIAL_REPORTS_BASE_URL") or DEFAULT_BASE_URL

ALLOW_SKIP = bool(os.getenv("FA_ALLOW_SMOKE_SKIP"))

# CI seeds a filing before running this, so "no data" there means the seed
# failed. A skip would look identical to a pass, which is the failure mode this
# whole job exists to catch, so it becomes an error instead.
REQUIRE_DATA = bool(os.getenv("SMOKE_REQUIRE_DATA"))

UNREACHABLE = f"""\
No FinancialReports producer is reachable at {BASE_URL}.

These {5} tests are the only coverage of the consumer/producer boundary --
every other test in this suite mocks the producer -- so skipping them silently
would report a green suite over the one seam neither repo tests.

Start it:      docker start financialreports-db-1 financialreports-api-1
Point at it:   FINANCIAL_REPORTS_BASE_URL=http://127.0.0.1:8010 uv run pytest
Run without:   FA_ALLOW_SMOKE_SKIP=1 uv run pytest

Note the port: the producer publishes 8010, and its database is on 5433 rather
than 5432 because langfuse holds 5432 on this machine.
"""


def _producer_is_reachable() -> bool:
    import httpx

    try:
        httpx.get(f"{BASE_URL}/health", timeout=3.0)
    except httpx.HTTPError:
        return False
    return True


if not _producer_is_reachable():
    if ALLOW_SKIP:
        pytestmark = pytest.mark.skip(reason=f"no producer at {BASE_URL}; FA_ALLOW_SMOKE_SKIP set")
    else:
        pytest.fail(UNREACHABLE, pytrace=False)


def _no_data(reason: str) -> None:
    """Skip locally, fail where the environment promised data."""
    if REQUIRE_DATA:
        pytest.fail(f"{reason} (SMOKE_REQUIRE_DATA is set, so this is a failure)")
    pytest.skip(reason)


@pytest.fixture(scope="module")
def provider() -> FinancialReportsProvider:
    return FinancialReportsProvider(base_url=BASE_URL or "", timeout=15.0, max_retries=1)


def test_producer_reports_the_schema_version_the_consumer_expects(provider):
    """The version the consumer's models are written against."""
    capabilities = provider.get_capabilities()

    assert capabilities["schema_version"] == "1.0.0", (
        "producer schema version moved; the consumer's transport models are "
        "written against 1.0.0"
    )


def test_capabilities_declares_the_endpoints_the_consumer_calls(provider):
    capabilities = provider.get_capabilities()
    declared = " ".join(capabilities.get("endpoints", []))

    for path in ("/snapshot", "/context", "/refresh", "/v1/stocks"):
        assert path in declared, f"producer no longer declares {path}"


def test_absent_filing_is_a_clean_miss_not_an_error(provider):
    """404 must map to None so the consumer can distinguish absent from broken."""
    assert provider.load_record("0000", "1999Q1") is None


def test_context_accepts_the_retrieval_parameters(provider):
    """The Phase D contract: question and sections must be accepted.

    A filing that has not finished its pipeline answers 409, which is correct
    producer behaviour rather than a contract break, so this walks filings
    until it finds a ready one.
    """
    import httpx

    attempted = 0
    for stock in provider.list_all_stocks()[:10]:
        for period in provider.list_available_periods(stock)[-3:]:
            attempted += 1
            try:
                context = provider.get_context(
                    stock, period, "公司面臨哪些風險", sections=["risk"], evidence_limit=3
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 409:
                    continue  # filing exists but is not ready; try another
                if exc.response.status_code == 422:
                    pytest.fail(
                        "producer rejected the retrieval parameters: " f"{exc.response.text[:300]}"
                    )
                raise
            if context is None:
                continue
            assert "evidence_chunks" in context
            assert len(context["evidence_chunks"]) <= 3
            return

    if not attempted:
        _no_data("producer has no filings loaded")
    _no_data(f"no ready filing among {attempted} tried")


def test_snapshot_round_trips_into_the_consumer_record_model(provider):
    """The producer's payload must parse into SnapshotRecord unchanged."""
    stocks = provider.list_all_stocks()
    if not stocks:
        _no_data("producer has no filings loaded")

    for stock in stocks[:5]:
        for period in provider.list_available_periods(stock)[-2:]:
            record = provider.load_record(stock, period)
            if record is None or record.snapshot is None:
                continue
            assert record.schema_version
            assert record.identity is not None
            assert record.identity.stock_code == stock
            return

    _no_data("no ready filing found to round-trip")
