"""API router for agent queries."""

import logging
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from app.models.agent_models import AgentQuery, AgentResponse
from app.agents import FinancialAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


@lru_cache()
def get_agent() -> FinancialAgent:
    """Initialize the agent lazily on the first request."""
    return FinancialAgent()


@router.post("/query", response_model=AgentResponse)
async def query_agent(query: AgentQuery) -> AgentResponse:
    """
    Submit a natural language query to the financial agent.

    Args:
        query: AgentQuery with natural language question and context

    Returns:
        AgentResponse with analysis and answer
    """
    try:
        response = await run_in_threadpool(get_agent().query, query)
        return response
    except Exception as exc:
        # The exception text is for the operator, not the caller: it has
        # carried provider URLs and upstream API messages into the client
        # response before.
        logger.exception("Agent query failed for %s/%s", query.stock_code, query.period)
        raise HTTPException(status_code=500, detail="Agent query failed") from exc


@router.post("/research", response_model=AgentResponse)
async def research_agent(query: AgentQuery) -> AgentResponse:
    """Run the full evidence-backed research workflow."""
    research_query = query.model_copy(update={"mode": "research"})
    try:
        return await run_in_threadpool(get_agent().query, research_query)
    except Exception as exc:
        # Without this the cause is discarded entirely: a failing research run
        # left a bare 500 in the response and nothing at all in the logs.
        logger.exception(
            "Research workflow failed for %s/%s", query.stock_code, query.period
        )
        raise HTTPException(status_code=500, detail="Research workflow failed") from exc
