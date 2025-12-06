"""AI Agent Chat Interface page."""

import streamlit as st
import json
from datetime import datetime
from app.agents.workflow import FinancialAgent
from app.core.config import get_settings


@st.cache_resource
def get_agent():
    """Get or create agent instance."""
    return FinancialAgent()


def show():
    """Display AI agent chat interface."""
    
    st.title("🤖 AI Financial Agent")
    st.markdown("Ask questions in natural language. The agent will analyze data and provide insights.")
    
    st.markdown("---")
    
    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "agent" not in st.session_state:
        try:
            settings = get_settings()
            st.session_state.agent = get_agent()
            st.session_state.agent_ready = True
        except Exception as e:
            st.session_state.agent_ready = False
            st.session_state.agent_error = str(e)
    
    # Sidebar for agent settings
    with st.sidebar:
        st.subheader("⚙️ Agent Settings")
        
        # Company context
        company_ticker = st.text_input("Company Ticker", value="AAPL", help="Stock ticker for context")
        company_name = st.text_input("Company Name", value="Apple Inc.", help="Company name for context")
        
        # Data source settings
        st.markdown("**Data Source**")
        data_source = st.selectbox("Source", ["CSV Upload", "API Endpoint", "Sample Data"])
        
        if data_source == "CSV Upload":
            uploaded_file = st.file_uploader("Upload Financial Data CSV", type=['csv'])
        
        st.markdown("---")
        
        # Agent capabilities
        st.markdown("**Agent Capabilities**")
        st.info("""
        The agent can help with:
        
        📊 Financial Snapshot
        📈 Trend Analysis
        🔄 Peer Comparison
        ⭐ Management Quality
        💎 Earnings Quality
        💰 ROIC vs WACC
        📐 Factor Exposure
        🚨 Early Warning System
        🔮 Capital Allocation
        """)
        
        # Example queries
        st.markdown("---")
        st.markdown("**Example Queries**")
        
        example_queries = [
            "What is the financial snapshot for this quarter?",
            "How has revenue trended over the past 5 years?",
            "Compare this company with its top 3 peers",
            "What is the management quality score?",
            "Assess the earnings quality",
            "Calculate ROIC vs WACC analysis",
            "What are the factor exposures?",
            "Are there any early warning signals?",
            "Evaluate capital allocation decisions"
        ]
        
        for query in example_queries:
            if st.button(query, key=f"example_{query[:20]}", use_container_width=True):
                st.session_state.example_query = query
    
    # Check agent readiness
    if not st.session_state.agent_ready:
        st.error(f"⚠️ Agent initialization failed: {st.session_state.get('agent_error', 'Unknown error')}")
        st.info("""
        **Troubleshooting:**
        - Ensure OpenAI API key is set in environment variables
        - Check that all dependencies are installed
        - Verify network connectivity
        """)
        return
    
    # Display chat history
    st.subheader("💬 Conversation")
    
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Display metadata if available
                if "metadata" in message and message["metadata"]:
                    with st.expander("🔍 Analysis Details"):
                        st.json(message["metadata"])
    
    # Query input
    query_input = st.chat_input("Ask a financial question...")
    
    # Handle example query from sidebar
    if "example_query" in st.session_state:
        query_input = st.session_state.example_query
        del st.session_state.example_query
    
    # Process query
    if query_input:
        # Add user message to chat
        st.session_state.messages.append({
            "role": "user",
            "content": query_input,
            "timestamp": datetime.now().isoformat()
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(query_input)
        
        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Analyzing..."):
                try:
                    # Prepare query object
                    from app.models.agent_models import AgentQuery
                    
                    agent_query = AgentQuery(
                        query=query_input,
                        stock_code=company_ticker,
                        period="",  # Will be extracted from query if needed
                        context={"company_name": company_name}
                    )
                    
                    # Call agent
                    response = st.session_state.agent.query(agent_query)
                    
                    # Display response
                    st.markdown(response.answer if hasattr(response, 'answer') else response.get("answer", "No response generated."))
                    
                    # Display analysis steps if available
                    analysis_steps = response.analysis_steps if hasattr(response, 'analysis_steps') else response.get("steps", [])
                    if analysis_steps:
                        with st.expander("🔬 Analysis Steps"):
                            for idx, step in enumerate(analysis_steps, 1):
                                st.markdown(f"**Step {idx}**: {step}")
                    
                    # Display data used
                    data_used = response.data if hasattr(response, 'data') else response.get("data", {})
                    if data_used:
                        with st.expander("📊 Data Used"):
                            st.json(data_used)
                    
                    # Display sources
                    sources = response.sources if hasattr(response, 'sources') else response.get("sources", [])
                    if sources:
                        with st.expander("🛠️ Data Sources"):
                            for source in sources:
                                st.markdown(f"- `{source}`")
                    
                    # Add assistant message to chat
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.answer if hasattr(response, 'answer') else response.get("answer", "No response"),
                        "metadata": {
                            "steps": analysis_steps,
                            "sources": sources,
                            "confidence": response.confidence if hasattr(response, 'confidence') else response.get("confidence", "N/A")
                        },
                        "timestamp": datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.error(error_msg)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                        "timestamp": datetime.now().isoformat()
                    })
    
    # Chat controls
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    with col2:
        if st.button("💾 Export Chat", use_container_width=True):
            chat_export = json.dumps(st.session_state.messages, indent=2)
            st.download_button(
                label="Download JSON",
                data=chat_export,
                file_name=f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col3:
        st.caption(f"💬 {len(st.session_state.messages)} messages in conversation")
    
    # Usage tips
    st.markdown("---")
    st.subheader("💡 Usage Tips")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Effective Queries:**
        - Be specific about the analysis type
        - Mention time periods when relevant
        - Ask follow-up questions for clarification
        - Request comparisons or benchmarks
        """)
    
    with col2:
        st.markdown("""
        **Best Practices:**
        - Review analysis steps for transparency
        - Verify data sources in metadata
        - Export important conversations
        - Provide context with ticker/company name
        """)
    
    # Debug info (collapsible)
    with st.expander("🐛 Debug Information"):
        st.markdown("**Session State:**")
        st.json({
            "agent_ready": st.session_state.agent_ready,
            "message_count": len(st.session_state.messages),
            "company_ticker": company_ticker,
            "company_name": company_name,
        })
        
        st.markdown("**Environment:**")
        try:
            settings = get_settings()
            st.json({
                "openai_available": bool(settings.openai_api_key),
                "api_base_url": settings.api_base_url,
            })
        except Exception as e:
            st.error(f"Settings error: {e}")


def format_agent_response(response):
    """Format agent response for display."""
    
    if isinstance(response, dict):
        return response.get("answer", str(response))
    elif isinstance(response, str):
        return response
    else:
        return str(response)
