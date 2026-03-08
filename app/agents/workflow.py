"""LangGraph agent workflow for financial analysis."""

from typing import TypedDict, Annotated, Sequence, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
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
    entities: dict
    analysis_data: dict
    final_answer: str


class FinancialAgent:
    """LangGraph-based financial analysis agent."""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatOpenAI(
            model=self.settings.llm_model,
            temperature=0.0,  # Force zero temperature for extraction
            api_key=self.settings.openai_api_key,
        )
        self.parser = PydanticOutputParser(pydantic_object=IntentClassification)
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
        """Classify user intent and extract entities using LLM."""
        query = state["query"]
        
        prompt = PromptTemplate(
            template="Analyze the following financial query and classify the intent and extract relevant entities (stock_code, period, etc.).\n{format_instructions}\nQuery: {query}\n",
            input_variables=["query"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )
        
        chain = prompt | self.llm | self.parser
        
        try:
            result = chain.invoke({"query": query})
            state["intent"] = result.intent_type
            state["entities"] = result.entities
            
            # Update stock_code and period if found in entities
            if "stock_code" in result.entities and result.entities["stock_code"]:
                state["stock_code"] = str(result.entities["stock_code"])
            if "period" in result.entities and result.entities["period"]:
                state["period"] = str(result.entities["period"])
                
        except Exception:
            # Fallback to keyword matching if LLM fails
            query_lower = query.lower()
            if any(word in query_lower for word in ["roic", "wacc"]): intent = "roic_wacc"
            elif "trend" in query_lower: intent = "trend"
            elif "management" in query_lower: intent = "management"
            else: intent = "snapshot"
            state["intent"] = intent
            state["entities"] = {}
            
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
        
        # Try to get peers from entities
        stock_codes = state["entities"].get("peers", state["stock_code"])
        
        result = tool_peer_compare.invoke({
            "stock_codes": stock_codes,
            "period": state["period"]
        })
        
        state["analysis_data"] = result
        return state
    
    def _management_node(self, state: AgentState) -> AgentState:
        """Execute management quality analysis."""
        from app.agents.tools import tool_management_score
        
        # Extract parameters from entities with defaults
        params = {
            "ceo_tenure": float(state["entities"].get("ceo_tenure", 5.0)),
            "cfo_tenure": float(state["entities"].get("cfo_tenure", 4.0)),
            "board_independence": float(state["entities"].get("board_independence", 0.4)),
            "insider_buys": int(state["entities"].get("insider_buys", 0)),
            "insider_sells": int(state["entities"].get("insider_sells", 0)),
            "governance_incidents": int(state["entities"].get("governance_incidents", 0)),
        }
        
        result = tool_management_score.invoke(params)
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
            "beta": float(state["entities"].get("beta", 1.0))
        })
        
        state["analysis_data"] = result
        return state
    
    def _factor_node(self, state: AgentState) -> AgentState:
        """Execute factor exposure analysis."""
        from app.agents.tools import tool_factor_exposure
        
        result = tool_factor_exposure.invoke({
            "stock_code": state["stock_code"],
            "period": state["period"],
            "peers": state["entities"].get("peers", "")
        })
        
        state["analysis_data"] = result
        return state
    
    def _capital_allocation_node(self, state: AgentState) -> AgentState:
        """Execute capital allocation analysis."""
        from app.agents.tools import tool_capital_allocation
        
        result = tool_capital_allocation.invoke({
            "stock_code": state["stock_code"],
            "period": state["period"],
            "dividends": float(state["entities"].get("dividends", 0)),
            "buybacks": float(state["entities"].get("buybacks", 0)),
            "capex": float(state["entities"].get("capex", 0))
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
            error_msg = analysis_data.get("error", "Unknown error")
            state["final_answer"] = f"I encountered an issue while performing the {intent} analysis: {error_msg}. Please ensure the data for {state.get('stock_code')} and period {state.get('period')} is available."
            return state
        
        # Use LLM to compose natural language answer
        data = analysis_data.get("data", {})
        
        prompt = f"""
As a professional financial analyst, provide a clear, insightful, and professional answer to the user's question based on the data provided.

User Question: {query}
Analysis Type: {intent}
Stock: {state.get('stock_code')}
Period: {state.get('period')}
Analysis Results: {data}

Guidelines:
- If the data is missing or incomplete, explain what is missing.
- Highlight key metrics and their implications.
- Use a professional tone suitable for fund managers.
- Keep the answer concise but comprehensive.
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
        # Initialize state with fallback period if not provided
        initial_state = AgentState(
            messages=[HumanMessage(content=query.query)],
            query=query.query,
            stock_code=query.stock_code or "AAPL",
            period=query.period or "2023Q3",  # Provide a default fallback period
            intent="",
            entities={},
            analysis_data={},
            final_answer=""
        )
        
        # Run the workflow
        final_state = self.graph.invoke(initial_state)
        
        # Build response
        return AgentResponse(
            query=query.query,
            answer=final_state["final_answer"],
            sources=[f"{final_state['intent']} analysis tool"],
            analysis_steps=[f"Detected intent: {final_state['intent']}", f"Extracted entities: {final_state.get('entities')}"],
            data=final_state.get("analysis_data", {}),
            confidence="high" if final_state.get("analysis_data", {}).get("success") else "low"
        )

