"""API router for agent queries."""

from fastapi import APIRouter, HTTPException
from app.models.agent_models import AgentQuery, AgentResponse
from app.agents import FinancialAgent

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Initialize agent
agent = FinancialAgent()


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
        response = agent.query(query)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
