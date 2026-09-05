"""Agent request and response models."""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

from app.models.api_models import UnitsMetadata


class AgentQuery(BaseModel):
    """Agent natural language query request."""

    query: str = Field(..., description="Natural language question")
    stock_code: Optional[str] = Field(None, description="Stock code if relevant")
    period: Optional[str] = Field(None, description="Period if relevant (e.g., '2023Q3')")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    mode: Literal["auto", "quick", "research"] = Field(
        default="auto", description="Execution depth"
    )


class AgentResponse(BaseModel):
    """Agent response with analysis results."""

    query: str
    answer: str
    sources: List[str] = Field(default_factory=list, description="Data sources used")
    analysis_steps: List[str] = Field(default_factory=list, description="Steps taken")
    data: Dict[str, Any] = Field(default_factory=dict, description="Supporting data")
    confidence: str = Field(default="medium", description="Confidence level: low, medium, high")
    confidence_score: float = Field(default=0.0, ge=0, le=1)
    verdict: Optional[str] = None
    research_plan: List[str] = Field(default_factory=list)
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    data_gaps: List[str] = Field(default_factory=list)
    watch_items: List[str] = Field(default_factory=list)
    units: UnitsMetadata = Field(default_factory=UnitsMetadata)


class IntentClassification(BaseModel):
    """Intent classification result."""

    intent_type: str = Field(
        ...,
        description="snapshot, trend, peer, management, earnings_quality, roic_wacc, factor, capital_allocation, sentiment, guidance, ews",
    )
    confidence: float = Field(..., ge=0, le=1)
    entities: Dict[str, Any] = Field(default_factory=dict)
