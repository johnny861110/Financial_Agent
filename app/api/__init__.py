"""API module initialization."""

from app.api.financials import router as financials_router
from app.api.agent import router as agent_router
from app.api.data import router as data_router

__all__ = ["financials_router", "agent_router", "data_router"]
