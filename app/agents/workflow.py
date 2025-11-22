"""LangGraph agent workflow for financial analysis."""

from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from app.core import get_settings
from app.agents.tools import ALL_TOOLS
from app.models.agent_models import AgentQuery, AgentResponse, IntentClassification


class AgentState(TypedDict):
    """State for the agent workflow."""
    messages: Annotated[Sequence[BaseMessage], "Messages in the conversation"]
    query: str
    stock_code: str
    period: str
    intent: str
    analysis_data: dict
    final_answer: str


class FinancialAgent:
    """LangGraph-based financial analysis agent."""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatOpenAI(
            model=self.settings.llm_model,
            temperature=self.settings.llm_temperature,
            api_key=self.settings.openai_api_key,
        )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("intent_router", self._intent_router_node)
        workflow.add_node("snapshot", self._snapshot_node)
        workflow.add_node("trend", self._trend_node)
        workflow.add_node("peer", self._peer_node)
        workflow.add_node("management", self._management_node)
        workflow.add_node("earnings_quality", self._earnings_quality_node)
        workflow.add_node("roic_wacc", self._roic_wacc_node)
        workflow.add_node("factor", self._factor_node)
        workflow.add_node("capital_allocation", self._capital_allocation_node)
        workflow.add_node("ews", self._ews_node)
        workflow.add_node("answer_composer", self._answer_composer_node)
        
        # Set entry point
        workflow.set_entry_point("intent_router")
        
        # Add conditional edges from intent router
        workflow.add_conditional_edges(
            "intent_router",
            self._route_by_intent,
            {
                "snapshot": "snapshot",
                "trend": "trend",
                "peer": "peer",
                "management": "management",
                "earnings_quality": "earnings_quality",
                "roic_wacc": "roic_wacc",
                "factor": "factor",
                "capital_allocation": "capital_allocation",
                "ews": "ews",
                "default": "snapshot",
            }
        )
        
        # All analysis nodes lead to answer composer
        for node in ["snapshot", "trend", "peer", "management", "earnings_quality", 
                     "roic_wacc", "factor", "capital_allocation", "ews"]:
            workflow.add_edge(node, "answer_composer")
        
        # Answer composer ends the workflow
        workflow.add_edge("answer_composer", END)
        
        return workflow.compile()
    
    def _intent_router_node(self, state: AgentState) -> AgentState:
        """Classify user intent."""
        query = state["query"]
        
        # Simple keyword-based intent classification
        # In production, would use LLM-based classification
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["trend", "over time", "historical", "growth"]):
            intent = "trend"
        elif any(word in query_lower for word in ["compare", "peer", "vs", "versus", "against"]):
            intent = "peer"
        elif any(word in query_lower for word in ["management", "governance", "ceo", "board"]):
            intent = "management"
        elif any(word in query_lower for word in ["earnings quality", "accrual", "cash flow"]):
            intent = "earnings_quality"
        elif any(word in query_lower for word in ["roic", "wacc", "value creation", "return on capital"]):
            intent = "roic_wacc"
        elif any(word in query_lower for word in ["factor", "exposure", "quality", "value", "momentum"]):
            intent = "factor"
        elif any(word in query_lower for word in ["capital allocation", "dividend", "buyback", "capex"]):
            intent = "capital_allocation"
        elif any(word in query_lower for word in ["risk", "warning", "red flag", "concern"]):
            intent = "ews"
        else:
            intent = "snapshot"
        
        state["intent"] = intent
        return state
    
    def _route_by_intent(self, state: AgentState) -> str:
        """Route to appropriate node based on intent."""
        return state.get("intent", "default")
    
    def _snapshot_node(self, state: AgentState) -> AgentState:
        """Execute snapshot analysis."""
        from app.agents.tools import tool_snapshot
        
        result = tool_snapshot.invoke({
            "stock_code": state["stock_code"],
            "period": state["period"]
        })
        
        state["analysis_data"] = result
        return state
    
    def _trend_node(self, state: AgentState) -> AgentState:
        """Execute trend analysis."""
        from app.agents.tools import tool_trend
        
        result = tool_trend.invoke({"stock_code": state["stock_code"]})
        state["analysis_data"] = result
        return state
    
    def _peer_node(self, state: AgentState) -> AgentState:
        """Execute peer comparison."""
        from app.agents.tools import tool_peer_compare
        
        # Extract peer codes from query or use defaults
        stock_codes = state["stock_code"]  # Could parse multiple from query
        
        result = tool_peer_compare.invoke({
            "stock_codes": stock_codes,
            "period": state["period"]
        })
        
        state["analysis_data"] = result
        return state
    
    def _management_node(self, state: AgentState) -> AgentState:
        """Execute management quality analysis."""
        from app.agents.tools import tool_management_score
        
        # In production, would extract these from data or query
        result = tool_management_score.invoke({})
        state["analysis_data"] = result
        return state
    
    def _earnings_quality_node(self, state: AgentState) -> AgentState:
        """Execute earnings quality analysis."""
        from app.agents.tools import tool_earnings_quality_score
        
        result = tool_earnings_quality_score.invoke({
            "stock_code": state["stock_code"],
            "period": state["period"]
        })
        
        state["analysis_data"] = result
        return state
    
    def _roic_wacc_node(self, state: AgentState) -> AgentState:
        """Execute ROIC/WACC analysis."""
        from app.agents.tools import tool_roic_wacc
        
        result = tool_roic_wacc.invoke({
            "stock_code": state["stock_code"],
            "period": state["period"],
            "beta": 1.0
        })
        
        state["analysis_data"] = result
        return state
    
    def _factor_node(self, state: AgentState) -> AgentState:
        """Execute factor exposure analysis."""
        from app.agents.tools import tool_factor_exposure
        
        result = tool_factor_exposure.invoke({
            "stock_code": state["stock_code"],
            "period": state["period"],
            "peers": ""
        })
        
        state["analysis_data"] = result
        return state
    
    def _capital_allocation_node(self, state: AgentState) -> AgentState:
        """Execute capital allocation analysis."""
        from app.agents.tools import tool_capital_allocation
        
        result = tool_capital_allocation.invoke({
            "stock_code": state["stock_code"],
            "period": state["period"],
            "dividends": 0,
            "buybacks": 0,
            "capex": 0
        })
        
        state["analysis_data"] = result
        return state
    
    def _ews_node(self, state: AgentState) -> AgentState:
        """Execute early warning system analysis."""
        from app.agents.tools import tool_ews
        
        result = tool_ews.invoke({
            "stock_code": state["stock_code"],
            "period": state["period"]
        })
        
        state["analysis_data"] = result
        return state
    
    def _answer_composer_node(self, state: AgentState) -> AgentState:
        """Compose final answer from analysis data."""
        analysis_data = state.get("analysis_data", {})
        intent = state.get("intent", "unknown")
        query = state.get("query", "")
        
        if not analysis_data.get("success"):
            state["final_answer"] = f"Unable to complete {intent} analysis. {analysis_data.get('error', 'Unknown error')}"
            return state
        
        # Use LLM to compose natural language answer
        data = analysis_data.get("data", {})
        
        prompt = f"""
Based on the financial analysis results below, provide a clear and professional answer to the user's question.

User Question: {query}
Analysis Type: {intent}
Analysis Results: {data}

Provide a comprehensive but concise answer highlighting the key insights.
"""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        state["final_answer"] = response.content
        
        return state
    
    def query(self, query: AgentQuery) -> AgentResponse:
        """
        Process a user query through the agent workflow.
        
        Args:
            query: AgentQuery object with question and context
        
        Returns:
            AgentResponse with analysis results
        """
        # Initialize state
        initial_state = AgentState(
            messages=[HumanMessage(content=query.query)],
            query=query.query,
            stock_code=query.stock_code or "",
            period=query.period or "",
            intent="",
            analysis_data={},
            final_answer=""
        )
        
        # Run the workflow
        final_state = self.graph.invoke(initial_state)
        
        # Build response
        return AgentResponse(
            query=query.query,
            answer=final_state["final_answer"],
            sources=[f"{final_state['intent']} analysis"],
            analysis_steps=[final_state["intent"]],
            data=final_state.get("analysis_data", {}),
            confidence="medium"
        )
