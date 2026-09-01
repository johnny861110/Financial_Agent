"""AI Agent Chat Interface page."""

import streamlit as st
import json
from datetime import datetime
import httpx

from app.core.config import get_settings
from app.models.agent_models import AgentQuery, AgentResponse
from ui.api_client import describe_api_error
from ui.data_source import period_input, render_data_source
from ui.presentation import (
    blocked_tools,
    group_field_states,
    pipeline_view,
    split_data_gaps,
    split_evidence,
)


def query_agent_api(query: AgentQuery) -> AgentResponse:
    """Submit research through the shared FastAPI application."""
    settings = get_settings()
    response = httpx.post(
        f"{settings.api_base_url.rstrip('/')}/api/agent/research",
        json=query.model_dump(mode="json"),
        timeout=120,
    )
    response.raise_for_status()
    return AgentResponse.model_validate(response.json())


def render_pipeline_state(response: AgentResponse) -> None:
    """Show processing state, calling out a failed pipeline stage."""
    readiness = (response.data or {}).get("data_readiness", {})
    if not readiness:
        return
    view = pipeline_view(readiness, (response.data or {}).get("record"))

    label = f"Data state: **{view.status}**"
    if view.has_failure:
        st.error(f"{label} — pipeline stage `{view.failed_stage}` failed")
    elif view.status in {"stale", "low_quality", "processing"}:
        st.warning(label)
    else:
        st.caption(label)

    if view.stage_states:
        with st.expander("Pipeline stages"):
            for stage, state in view.stage_states:
                icon = {"completed": "✅", "failed": "❌", "started": "⏳"}.get(state, "•")
                st.markdown(f"{icon} `{stage}` — {state}")

    states = group_field_states(readiness.get("field_states") or {})
    if states:
        with st.expander("Field availability"):
            for group in states:
                st.markdown(f"{group.icon} **{group.description}** — {', '.join(group.fields)}")


def render_blocked_tools(response: AgentResponse) -> None:
    """Explain any tool the planner refused to run, field by field."""
    blocked = blocked_tools((response.data or {}).get("tools", {}))
    if not blocked:
        return
    with st.expander(f"⛔ {len(blocked)} analysis step(s) could not run", expanded=True):
        for item in blocked:
            st.markdown(f"**{item.tool}**")
            for reason in item.reasons():
                st.markdown(f"- {reason}")


def render_citations(response: AgentResponse) -> None:
    """Render filing passages as followable sources, facts as structured data."""
    citations, structured = split_evidence(response.evidence)

    if citations:
        with st.expander(f"📄 Filing sources ({len(citations)})", expanded=True):
            for citation in citations:
                if citation.is_linkable:
                    header = f"[{citation.label}]({citation.url})"
                else:
                    header = citation.label
                if citation.score is not None:
                    header += f" · relevance {citation.score:.2f}"
                st.markdown(header)
                if citation.excerpt:
                    st.caption(citation.excerpt)
                if citation.detail:
                    st.caption(f"↳ {citation.detail}")
                st.markdown("---")

    if structured:
        with st.expander(f"🔢 Structured evidence ({len(structured)})"):
            st.json(structured)


def show():
    """Display AI agent chat interface."""

    st.title("🤖 AI Financial Agent")
    st.markdown(
        "Ask questions in natural language. The agent will analyze data and provide insights."
    )

    st.markdown("---")

    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "agent_ready" not in st.session_state:
        try:
            settings = get_settings()
            response = httpx.get(f"{settings.api_base_url.rstrip('/')}/health/live", timeout=3)
            st.session_state.agent_ready = response.status_code == 200
        except Exception as e:
            st.session_state.agent_ready = False
            st.session_state.agent_error = str(e)

    # Sidebar for agent settings
    with st.sidebar:
        st.subheader("⚙️ Agent Settings")

        # Company context
        company_ticker = st.text_input(
            "Company Ticker", value="3661", help="Stock ticker for context"
        )
        company_name = st.text_input(
            "Company Name", value="世芯-KY", help="Company name for context"
        )

        # The period used to be hardcoded to 2025Q1 here, so every question was
        # answered about that quarter no matter what the user asked.
        period = period_input(company_ticker, key="agent_period")

        st.markdown("---")
        render_data_source()

        st.markdown("---")

        # Agent capabilities
        st.markdown("**Agent Capabilities**")
        st.info(
            """
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
        """
        )

        # Example queries
        st.markdown("---")
        st.markdown("**Example Queries**")

        example_queries = [
            "What is the financial snapshot for 世芯-KY 3661 in 2025Q1?",
            "How has revenue trended for 3661?",
            "Compare 3661 with 2330 and 2454 in 2025Q1",
            "What is the management quality score for 世芯-KY?",
            "Assess the earnings quality for 3661 in 2025Q1",
            "Calculate ROIC vs WACC analysis for 3661 in 2025Q1",
            "What are the factor exposures for 3661 in 2025Q1?",
            "Are there any early warning signals for 3661 in 2025Q1?",
            "Evaluate capital allocation decisions for 世芯-KY",
        ]

        for query in example_queries:
            if st.button(query, key=f"example_{query[:20]}", use_container_width=True):
                st.session_state.example_query = query

    # Check agent readiness
    if not st.session_state.agent_ready:
        st.error(
            f"⚠️ Agent initialization failed: {st.session_state.get('agent_error', 'Unknown error')}"
        )
        st.info(
            """
        **Troubleshooting:**
        - Ensure OpenAI API key is set in environment variables
        - Check that all dependencies are installed
        - Verify network connectivity
        """
        )
        # Without this the page stays on the error screen for the rest of the
        # session: agent_ready is only computed when the key is absent.
        if st.button("🔄 Retry connection"):
            st.session_state.pop("agent_ready", None)
            st.session_state.pop("agent_error", None)
            st.rerun()
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
        st.session_state.messages.append(
            {"role": "user", "content": query_input, "timestamp": datetime.now().isoformat()}
        )

        # Display user message
        with st.chat_message("user"):
            st.markdown(query_input)

        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Analyzing..."):
                try:
                    agent_query = AgentQuery(
                        query=query_input,
                        stock_code=company_ticker,
                        period=period,
                        context={"company_name": company_name},
                    )

                    response = query_agent_api(agent_query)

                    # Display response
                    st.markdown(response.answer)

                    if response.verdict:
                        verdict_col, confidence_col = st.columns(2)
                        verdict_col.metric("Verdict", response.verdict)
                        confidence_col.metric(
                            "Confidence", f"{response.confidence_score * 100:.0f}%"
                        )

                    render_pipeline_state(response)
                    render_blocked_tools(response)

                    validation_gaps, ordinary_gaps = split_data_gaps(response.data_gaps)
                    if (
                        response.risks
                        or response.contradictions
                        or validation_gaps
                        or ordinary_gaps
                    ):
                        with st.expander("Research Risks and Data Gaps", expanded=True):
                            # Validation failures mean the producer believes a
                            # number is wrong, which is a different problem from
                            # a field simply being absent.
                            if validation_gaps:
                                st.markdown("**Validation failures**")
                                for item in validation_gaps:
                                    st.error(item)
                            for risk in response.risks:
                                st.warning(risk)
                            for contradiction in response.contradictions:
                                st.warning(f"Contradiction: {contradiction}")
                            if ordinary_gaps:
                                st.markdown("**Data gaps**")
                                for gap in ordinary_gaps:
                                    st.info(gap)

                    render_citations(response)

                    # Display analysis steps if available
                    analysis_steps = response.analysis_steps
                    if analysis_steps:
                        with st.expander("🔬 Analysis Steps"):
                            for idx, step in enumerate(analysis_steps, 1):
                                st.markdown(f"**Step {idx}**: {step}")

                    # Display data used
                    data_used = response.data
                    if data_used:
                        with st.expander("📊 Data Used"):
                            st.json(data_used)

                    # Display sources
                    sources = response.sources
                    if sources:
                        with st.expander("🛠️ Data Sources"):
                            for source in sources:
                                st.markdown(f"- `{source}`")

                    # Add assistant message to chat
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": response.answer,
                            "metadata": {
                                "steps": analysis_steps,
                                "sources": sources,
                                "confidence": response.confidence,
                            },
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

                except Exception as e:  # noqa: BLE001 - surfaced to the user below
                    error_msg = f"❌ {describe_api_error(e)}"
                    st.error(error_msg)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": error_msg,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

    # Chat controls
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    with col2:
        st.download_button(
            label="💾 Export Chat",
            data=json.dumps(st.session_state.messages, indent=2, ensure_ascii=False),
            file_name=f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
            disabled=not st.session_state.messages,
        )

    with col3:
        st.caption(f"💬 {len(st.session_state.messages)} messages in conversation")

    # Usage tips
    st.markdown("---")
    st.subheader("💡 Usage Tips")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
        **Effective Queries:**
        - Be specific about the analysis type
        - Mention time periods when relevant
        - Ask follow-up questions for clarification
        - Request comparisons or benchmarks
        """
        )

    with col2:
        st.markdown(
            """
        **Best Practices:**
        - Review analysis steps for transparency
        - Verify data sources in metadata
        - Export important conversations
        - Provide context with ticker/company name
        """
        )

    # Debug info (collapsible)
    with st.expander("🐛 Debug Information"):
        st.markdown("**Session State:**")
        st.json(
            {
                "agent_ready": st.session_state.agent_ready,
                "message_count": len(st.session_state.messages),
                "company_ticker": company_ticker,
                "company_name": company_name,
            }
        )

        st.markdown("**Environment:**")
        try:
            settings = get_settings()
            st.json(
                {
                    "openai_available": bool(settings.openai_api_key),
                    "api_base_url": settings.api_base_url,
                }
            )
        except Exception as e:
            st.error(f"Settings error: {e}")

