"""Tests that the stack starts without its optional companions.

Langfuse and FinancialReports run in their own compose projects. Neither is
required to bring this stack up, and these tests pin that: joining an external
compose network makes the other project a hard prerequisite, because
`docker compose up` refuses to start when an external network is absent.
"""

from pathlib import Path

import pytest
import yaml

from app.agents.workflow import FinancialAgent
from app.core.config import Settings


COMPOSE = Path(__file__).resolve().parents[1] / "docker-compose.yaml"


@pytest.fixture(scope="module")
def compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text())


def test_compose_declares_no_external_networks(compose):
    """An absent external network stops the stack before any container starts."""
    external = [
        name
        for name, spec in (compose.get("networks") or {}).items()
        if isinstance(spec, dict) and spec.get("external")
    ]

    assert external == [], (
        f"{external} would have to exist before this stack can start; "
        "reach other compose projects over their published host ports instead"
    )


def test_services_reach_companion_projects_through_the_host_gateway(compose):
    """The hostnames used in default URLs have to resolve without a shared network."""
    for name, service in compose["services"].items():
        hosts = {entry.split(":")[0] for entry in service.get("extra_hosts", [])}
        assert "financial-reports" in hosts, f"{name} cannot resolve financial-reports"
        assert "langfuse-web" in hosts, f"{name} cannot resolve langfuse-web"


def test_langfuse_is_not_required_by_default():
    """Tracing is observability, not a dependency."""
    assert Settings().langfuse_required is False
    assert Settings().langfuse_enabled is False


def test_agent_starts_when_langfuse_is_misconfigured(monkeypatch, caplog):
    """A tracing failure must degrade to a warning, never block construction."""
    agent = FinancialAgent.__new__(FinancialAgent)
    agent.settings = Settings(
        langfuse_enabled=True,
        langfuse_public_key="",
        langfuse_secret_key="",
        langfuse_required=False,
    )

    assert agent._build_langfuse_handler() is None
    assert "Langfuse tracing is disabled" in caplog.text


def test_agent_refuses_to_start_when_langfuse_is_explicitly_required():
    """The strict mode still exists for deployments that depend on traces."""
    agent = FinancialAgent.__new__(FinancialAgent)
    agent.settings = Settings(
        langfuse_enabled=True,
        langfuse_public_key="",
        langfuse_secret_key="",
        langfuse_required=True,
    )

    with pytest.raises(RuntimeError, match="LANGFUSE"):
        agent._build_langfuse_handler()
