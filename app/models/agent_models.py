"""Agent request and response models."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AgentQuery(BaseModel):
    """Agent natural language query request."""
    
    query: str = Field(..., description="Natural language question")
    stock_code: Optional[str] = Field(None, description="Stock code if relevant")
    period: Optional[str] = Field(None, description="Period if relevant (e.g., '2023Q3')")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class AgentResponse(BaseModel):
    """Agent response with analysis results."""
    
    query: str
    answer: str
    sources: List[str] = Field(default_factory=list, description="Data sources used")
    analysis_steps: List[str] = Field(default_factory=list, description="Steps taken")
    data: Dict[str, Any] = Field(default_factory=dict, description="Supporting data")
    confidence: str = Field(default="medium", description="Confidence level: low, medium, high")


class IntentClassification(BaseModel):
    """Intent classification result."""
    
    intent_type: str = Field(
        ...,
        description="snapshot, trend, peer, management, earnings_quality, roic_wacc, factor, capital_allocation, sentiment, guidance, ews"
    )
    confidence: float = Field(..., ge=0, le=1)
    entities: Dict[str, Any] = Field(default_factory=dict)
