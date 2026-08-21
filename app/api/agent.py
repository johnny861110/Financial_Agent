"""API router for agent queries."""

from functools import lru_cache

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from app.models.agent_models import AgentQuery, AgentResponse
from app.agents import FinancialAgent

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@router.post("/research", response_model=AgentResponse)
async def research_agent(query: AgentQuery) -> AgentResponse:
    """Run the full evidence-backed research workflow."""
    research_query = query.model_copy(update={"mode": "research"})
    try:
        return await run_in_threadpool(get_agent().query, research_query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Research workflow failed") from exc
