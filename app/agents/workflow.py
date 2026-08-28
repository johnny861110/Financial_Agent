"""LangGraph agent workflow for financial analysis."""

import json
import logging
from typing import Any, TypedDict, Annotated, Sequence

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from app.core import DataLoader, get_settings
from app.agents.contracts import ResearchFinding, ResearchReport, ToolResult
from app.agents.tools import TOOL_REGISTRY, evaluate_eligibility, required_fields_for_planning
from app.data.context import CanonicalFinancialContext
from app.data.readiness import DataReadinessService
from app.models.agent_models import AgentQuery, AgentResponse, IntentClassification


logger = logging.getLogger(__name__)


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
    mode: str
    context: dict
    data_readiness: dict
    research_plan: list[str]
    tool_results: dict[str, dict]
    evidence: list[dict]
    contradictions: list[str]
    report: dict
    field_states: dict[str, str]
    failed_rules: list[str]


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
        self.data_loader = DataLoader()
        from app.agents.tools import configure_tool_services

        configure_tool_services(self.data_loader)
        self.langfuse_client = None
        self.langfuse_handler = self._build_langfuse_handler()
        self.graph = self._build_graph()

    def _build_langfuse_handler(self):
        """Create the Langfuse LangChain callback handler when configured."""
        if not self.settings.langfuse_enabled:
            return None

        if not self.settings.langfuse_public_key or not self.settings.langfuse_secret_key:
            message = (
                "LANGFUSE_ENABLED is true, but LANGFUSE_PUBLIC_KEY or "
                "LANGFUSE_SECRET_KEY is missing."
            )
            if self.settings.langfuse_required:
                raise RuntimeError(message)
            logger.warning("%s Langfuse tracing is disabled.", message)
            return None

        try:
            from langfuse import Langfuse, get_client
            from langfuse.langchain import CallbackHandler

            client_kwargs = {
                "public_key": self.settings.langfuse_public_key,
                "secret_key": self.settings.langfuse_secret_key,
            }
            base_url = self.settings.langfuse_base_url or self.settings.langfuse_host
            if base_url:
                client_kwargs["base_url"] = base_url

            Langfuse(**client_kwargs)
            self.langfuse_client = get_client()
            return CallbackHandler()
        except Exception as exc:
            message = f"Failed to initialize Langfuse tracing: {exc}"
            if self.settings.langfuse_required:
                raise RuntimeError(message) from exc
            logger.warning("%s Langfuse tracing is disabled.", message)
            return None

    def _langfuse_config(self, query: AgentQuery | None = None) -> dict:
        """Build per-run LangChain config for Langfuse traces."""
        if self.langfuse_handler is None:
            return {}

        metadata: dict[str, Any] = {"langfuse_tags": ["financial-agent"]}
        if query:
            metadata["stock_code"] = query.stock_code
            metadata["period"] = query.period
            metadata.update(query.context or {})

            user_id = query.context.get("user_id") if query.context else None
            session_id = query.context.get("session_id") if query.context else None
            if user_id:
                metadata["langfuse_user_id"] = user_id
            if session_id:
                metadata["langfuse_session_id"] = session_id

        return {
            "callbacks": [self.langfuse_handler],
            "metadata": metadata,
            "run_name": "financial-agent-query",
        }

    def _build_graph(self) -> Any:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AgentState)

        workflow.add_node("intent_router", self._intent_router_node)
        workflow.add_node("data_readiness", self._data_readiness_node)
        workflow.add_node("research_planner", self._research_planner_node)
        workflow.add_node("research_executor", self._research_executor_node)
        workflow.add_node("answer_composer", self._answer_composer_node)

        workflow.set_entry_point("intent_router")
        workflow.add_edge("intent_router", "data_readiness")
        workflow.add_edge("data_readiness", "research_planner")
        workflow.add_edge("research_planner", "research_executor")
        workflow.add_edge("research_executor", "answer_composer")
        workflow.add_edge("answer_composer", END)

        return workflow.compile()

    def _default_stock_period(self) -> tuple[str, str]:
        """Return the latest locally available stock/period pair."""
        stocks = self.data_loader.list_all_stocks()
        if not stocks:
            return "3661", "2025Q1"

        latest_stock = stocks[0]
        latest_period = ""
        for stock in stocks:
            periods = self.data_loader.list_available_periods(stock)
            if periods and periods[-1] > latest_period:
                latest_stock = stock
                latest_period = periods[-1]

        return latest_stock, latest_period or "2025Q1"

    def _keyword_classification(self, query: str) -> tuple[str, dict]:
        """Classify common financial intents without relying on the LLM."""
        import re

        query_lower = query.lower()
        if any(word in query_lower for word in ["roic", "wacc", "value creation", "資本報酬"]):
            intent = "roic_wacc"
        elif any(word in query_lower for word in ["trend", "growth", "over time", "趨勢", "成長"]):
            intent = "trend"
        elif any(word in query_lower for word in ["peer", "compare", "comparison", "同業", "比較"]):
            intent = "peer"
        elif any(
            word in query_lower
            for word in ["management", "governance", "ceo", "cfo", "管理層", "公司治理"]
        ):
            intent = "management"
        elif any(
            word in query_lower for word in ["earnings quality", "accrual", "盈餘品質", "應計"]
        ):
            intent = "earnings_quality"
        elif any(word in query_lower for word in ["factor", "exposure", "因子", "曝險"]):
            intent = "factor"
        elif any(
            word in query_lower
            for word in [
                "capital allocation",
                "dividend",
                "buyback",
                "capex",
                "資本配置",
                "股利",
                "回購",
                "資本支出",
            ]
        ):
            intent = "capital_allocation"
        elif any(
            word in query_lower
            for word in ["warning", "risk", "red flag", "ews", "風險", "警訊", "預警"]
        ):
            intent = "ews"
        else:
            intent = "snapshot"

        entities: dict[str, Any] = {}
        stock_matches = re.findall(r"\b\d{3,6}\b", query)
        if stock_matches:
            entities["stock_code"] = stock_matches[0]
        if len(stock_matches) > 1:
            entities["peer_stocks"] = stock_matches
        period_match = re.search(r"\b20\d{2}Q[1-4]\b", query, re.IGNORECASE)
        if period_match:
            entities["period"] = period_match.group(0).upper()
        beta_match = re.search(r"\bbeta(?:\s+of|\s*=|\s+is)?\s+([0-9]+(?:\.[0-9]+)?)", query_lower)
        if beta_match:
            entities["beta"] = float(beta_match.group(1))

        return intent, entities

    def _data_readiness_node(self, state: AgentState) -> AgentState:
        """Load source status and evidence before any financial tool runs."""
        if state.get("intent") == "management":
            state["data_readiness"] = {
                "status": "not_required",
                "available": True,
                "warnings": ["Management analysis uses caller-supplied assumptions"],
            }
            state["evidence"] = []
            state["field_states"] = {}
            state["failed_rules"] = []
            return state

        readiness_service = DataReadinessService(self.data_loader.provider)
        readiness = readiness_service.check(state["stock_code"], state["period"])
        state["data_readiness"] = readiness.model_dump(mode="json")

        record = (
            self.data_loader.load_record(state["stock_code"], state["period"])
            if readiness.available
            else None
        )
        if record:
            evidence = record.agent_evidence()
            if not evidence and record.snapshot:
                evidence = [
                    {
                        "source_type": record.source,
                        "stock_code": state["stock_code"],
                        "period": state["period"],
                    }
                ]
            state["evidence"] = evidence

            # Resolve every field any tool may gate on in one pass. The canonical
            # context reports per-field state for both providers: it falls back to
            # inspecting the snapshot when the producer supplies no
            # field_availability, so this works where the previous gate -- which
            # read producer-reported quality.missing_fields -- could not.
            context = CanonicalFinancialContext(record)
            state["field_states"] = context.field_states(required_fields_for_planning())
            state["failed_rules"] = [
                failure.rule_name for failure in context.failed_validations(severities=["error"])
            ]
        else:
            state["evidence"] = []
            state["field_states"] = {}
            state["failed_rules"] = []

        if (
            readiness.status == "missing"
            and self.settings.auto_refresh_missing_data
            and self.settings.data_provider == "financial_reports"
        ):
            try:
                refresh = readiness_service.request_refresh(state["stock_code"], state["period"])
                state["data_readiness"].update(
                    {"status": "processing", "job_id": refresh.get("job_id")}
                )
            except Exception as exc:
                state["data_readiness"].setdefault("warnings", []).append(str(exc))
        return state

    def _research_planner_node(self, state: AgentState) -> AgentState:
        """Build a deterministic, auditable tool plan."""
        intent = state.get("intent", "snapshot")
        mode = state.get("mode", "auto")
        query = state.get("query", "").lower()
        broad_terms = [
            "financial health",
            "worth",
            "hold",
            "invest",
            "complete analysis",
            "完整分析",
            "值得",
            "持有",
            "投資",
            "財務健康",
        ]
        broad_question = mode == "research" or any(term in query for term in broad_terms)

        if mode == "quick" or not broad_question:
            plan = [intent if intent != "default" else "snapshot"]
        else:
            plan = ["snapshot", "trend", "earnings_quality", "roic_wacc", "ews"]
            peer_stocks = state.get("entities", {}).get("peer_stocks") or state.get(
                "context", {}
            ).get("peer_stocks")
            if peer_stocks and len(peer_stocks) >= 2:
                plan.extend(["peer", "factor"])

        seen: set[str] = set()
        unique_plan: list[str] = []
        for item in plan:
            if item not in seen:
                seen.add(item)
                unique_plan.append(item)
        state["research_plan"] = unique_plan
        return state

    def _tool_arguments(self, tool_name: str, state: AgentState) -> dict[str, Any]:
        stock_code = state["stock_code"]
        period = state["period"]
        entities = state.get("entities", {})
        context = state.get("context", {})
        peers = entities.get("peer_stocks") or context.get("peer_stocks", [])

        if tool_name == "trend":
            return {"stock_code": stock_code}
        if tool_name == "peer":
            codes = peers or [stock_code]
            return {"stock_codes": ",".join(map(str, codes)), "period": period}
        if tool_name == "management":
            return {
                "ceo_tenure": context.get("ceo_tenure", 0),
                "cfo_tenure": context.get("cfo_tenure", 0),
                "board_independence": context.get("board_independence", 0.3),
                "insider_buys": context.get("insider_buys", 0),
                "insider_sells": context.get("insider_sells", 0),
                "governance_incidents": context.get("governance_incidents", 0),
            }
        if tool_name == "roic_wacc":
            return {
                "stock_code": stock_code,
                "period": period,
                "beta": entities.get("beta", context.get("beta", 1.0)),
            }
        if tool_name == "factor":
            return {
                "stock_code": stock_code,
                "period": period,
                "peers": ",".join(map(str, peers)),
            }
        if tool_name == "capital_allocation":
            return {
                "stock_code": stock_code,
                "period": period,
                "dividends": context.get("dividends", 0),
                "buybacks": context.get("buybacks", 0),
                "capex": context.get("capex", 0),
            }
        if tool_name == "sentiment":
            return {"text": context.get("text", state.get("query", ""))}
        return {"stock_code": stock_code, "period": period}

    def _research_executor_node(self, state: AgentState) -> AgentState:
        """Execute every planned tool and normalize failures."""
        tools = TOOL_REGISTRY
        readiness = state.get("data_readiness", {})
        if not readiness.get("available", False):
            status = readiness.get("status", "failed")
            error = f"Financial data is {status}"
            state["tool_results"] = {
                "data_readiness": ToolResult(
                    tool="data_readiness",
                    status="not_found" if status == "missing" else "failed",
                    finding=error,
                    warnings=readiness.get("warnings", []),
                    error=error,
                ).model_dump(mode="json")
            }
        else:
            results: dict[str, dict] = {}
            field_states = state.get("field_states", {})
            failed_rules = state.get("failed_rules", [])
            for tool_name in state.get("research_plan", []):
                selected = tools.get(tool_name)
                if selected is None:
                    continue
                blocked = evaluate_eligibility(
                    tool_name,
                    field_states,
                    quality_score=readiness.get("quality_score"),
                    is_stale=readiness.get("status") == "stale",
                    failed_rules=failed_rules,
                )
                if blocked is not None:
                    results[tool_name] = blocked
                    continue
                try:
                    result = selected.invoke(self._tool_arguments(tool_name, state))
                    if not result.get("evidence"):
                        result["evidence"] = state.get("evidence", [])
                    results[tool_name] = result
                except Exception as exc:
                    results[tool_name] = ToolResult(
                        tool=tool_name,
                        status="failed",
                        finding=str(exc),
                        error=str(exc),
                    ).model_dump(mode="json")
            state["tool_results"] = results

        state["contradictions"] = self._detect_contradictions(state["tool_results"])
        report = self._build_research_report(state)
        state["report"] = report.model_dump(mode="json")
        state["analysis_data"] = {
            "success": bool(report.findings),
            "status": "success" if report.findings else "insufficient_data",
            "data_readiness": state.get("data_readiness", {}),
            "tools": state["tool_results"],
            "report": state["report"],
        }
        return state

    @staticmethod
    def _detect_contradictions(results: dict[str, dict]) -> list[str]:
        contradictions: list[str] = []
        roic = results.get("roic_wacc", {}).get("data", {})
        ews = results.get("ews", {}).get("data", {})
        earnings = results.get("earnings_quality", {}).get("data", {})
        if roic.get("creating_value") and ews.get("warning_level") in {"high", "critical"}:
            contradictions.append(
                "ROIC exceeds WACC, but the early-warning system reports high risk"
            )
        if roic.get("creating_value") and earnings.get("total_score", 100) < 50:
            contradictions.append("Capital returns appear positive while earnings quality is weak")
        return contradictions

    # Confidence penalties. Each is bounded and strictly positive: a degraded
    # signal must lower confidence without collapsing it to zero, which would be
    # indistinguishable from "no analysis was possible at all".
    STALE_DATA_PENALTY = 0.9
    FAILED_VALIDATION_PENALTY = 0.85
    DATA_GAP_PENALTY = 0.8
    NO_EVIDENCE_PENALTY = 0.75

    def _confidence_multiplier(
        self, state: AgentState, findings: list[ResearchFinding], has_gaps: bool
    ) -> float:
        """Scale confidence by data quality, freshness, validation, and evidence.

        Answers the Phase C criterion that confidence reflect the state of the
        source data, not only the per-tool constants the tools report.
        """
        readiness = state.get("data_readiness", {})
        multiplier = 1.0

        quality = readiness.get("quality_score")
        if quality is not None:
            multiplier *= float(quality)
        if readiness.get("status") == "stale":
            multiplier *= self.STALE_DATA_PENALTY
        if state.get("failed_rules"):
            multiplier *= self.FAILED_VALIDATION_PENALTY
        if has_gaps:
            multiplier *= self.DATA_GAP_PENALTY

        # Evidence coverage: a finding with no supporting evidence is weaker
        # than the same finding backed by filing facts.
        if findings:
            supported = sum(1 for finding in findings if finding.evidence)
            coverage = supported / len(findings)
            multiplier *= self.NO_EVIDENCE_PENALTY + (1 - self.NO_EVIDENCE_PENALTY) * coverage

        return multiplier

    def _build_research_report(self, state: AgentState) -> ResearchReport:
        results = state.get("tool_results", {})
        findings: list[ResearchFinding] = []
        readiness = state.get("data_readiness", {})
        risks: list[str] = list(readiness.get("warnings", []))
        gaps: list[str] = list(readiness.get("missing_fields", []))
        evidence: list[dict] = []
        confidence_values: list[float] = []

        for tool_name, result in results.items():
            if result.get("success"):
                finding = result.get("finding") or f"{tool_name} analysis completed"
                findings.append(
                    ResearchFinding(
                        tool=tool_name,
                        finding=finding,
                        confidence=float(result.get("confidence", 0)),
                        evidence=result.get("evidence", []),
                        warnings=result.get("warnings", []),
                    )
                )
                confidence_values.append(float(result.get("confidence", 0)))
                risks.extend(result.get("warnings", []))
                evidence.extend(result.get("evidence", []))
            else:
                gaps.extend(result.get("missing_fields", []))
                if result.get("error"):
                    gaps.append(f"{tool_name}: {result['error']}")

        ews_level = results.get("ews", {}).get("data", {}).get("warning_level")
        roic_creating = results.get("roic_wacc", {}).get("data", {}).get("creating_value")
        earnings_score = results.get("earnings_quality", {}).get("data", {}).get("total_score")
        if ews_level in {"high", "critical"} or earnings_score is not None and earnings_score < 50:
            verdict = "警戒"
        elif roic_creating is True and findings:
            verdict = "偏正向"
        elif findings:
            verdict = "中性"
        else:
            verdict = "資料不足"

        base_confidence = (
            sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
        )
        base_confidence *= self._confidence_multiplier(state, findings, bool(gaps))

        unique_evidence = list(
            {json.dumps(item, sort_keys=True): item for item in evidence}.values()
        )
        unique_risks = list(dict.fromkeys(risks))
        unique_gaps = list(dict.fromkeys(gaps))
        thesis = "；".join(item.finding for item in findings[:3]) or "目前沒有足夠資料形成投資論點"
        watch_items = list(dict.fromkeys(unique_risks + state.get("contradictions", [])))[:8]
        return ResearchReport(
            verdict=verdict,
            investment_thesis=thesis,
            findings=findings,
            supporting_evidence=unique_evidence,
            contradictions=state.get("contradictions", []),
            key_risks=unique_risks,
            data_gaps=unique_gaps,
            watch_items=watch_items,
            confidence=round(max(0.0, min(1.0, base_confidence)), 3),
        )

    def _intent_router_node(self, state: AgentState) -> AgentState:
        """Classify user intent and extract entities using LLM."""
        query = state["query"]

        fallback_intent, fallback_entities = self._keyword_classification(query)
        if not self.settings.openai_api_key:
            state["intent"] = fallback_intent
            state["entities"] = fallback_entities
            if "stock_code" in fallback_entities:
                state["stock_code"] = str(fallback_entities["stock_code"])
            if "period" in fallback_entities:
                state["period"] = str(fallback_entities["period"])
            return state

        prompt = PromptTemplate(
            template="Analyze the following financial query and classify the intent and extract relevant entities (stock_code, period, etc.).\n{format_instructions}\nQuery: {query}\n",
            input_variables=["query"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )

        chain = prompt | self.llm | self.parser

        try:
            result = chain.invoke({"query": query}, config=self._langfuse_config())
            state["intent"] = result.intent_type
            state["entities"] = result.entities

            # Update stock_code and period if found in entities
            if "stock_code" in result.entities and result.entities["stock_code"]:
                state["stock_code"] = str(result.entities["stock_code"])
            if "period" in result.entities and result.entities["period"]:
                state["period"] = str(result.entities["period"])

        except Exception:
            state["intent"] = fallback_intent
            state["entities"] = fallback_entities
            if "stock_code" in fallback_entities:
                state["stock_code"] = str(fallback_entities["stock_code"])
            if "period" in fallback_entities:
                state["period"] = str(fallback_entities["period"])

        return state

    def _route_by_intent(self, state: AgentState) -> str:
        """Route to appropriate node based on intent."""
        return state.get("intent", "default")

    def _snapshot_node(self, state: AgentState) -> AgentState:
        """Execute snapshot analysis."""
        from app.agents.tools import tool_snapshot

        result = tool_snapshot.invoke(
            {"stock_code": state["stock_code"], "period": state["period"]}
        )

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
        if isinstance(stock_codes, list):
            stock_codes = ",".join(str(code) for code in stock_codes)

        result = tool_peer_compare.invoke({"stock_codes": stock_codes, "period": state["period"]})

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

        result = tool_earnings_quality_score.invoke(
            {"stock_code": state["stock_code"], "period": state["period"]}
        )

        state["analysis_data"] = result
        return state

    def _roic_wacc_node(self, state: AgentState) -> AgentState:
        """Execute ROIC/WACC analysis."""
        from app.agents.tools import tool_roic_wacc

        result = tool_roic_wacc.invoke(
            {
                "stock_code": state["stock_code"],
                "period": state["period"],
                "beta": float(state["entities"].get("beta", 1.0)),
            }
        )

        state["analysis_data"] = result
        return state

    def _factor_node(self, state: AgentState) -> AgentState:
        """Execute factor exposure analysis."""
        from app.agents.tools import tool_factor_exposure

        peers = state["entities"].get("peers", "")
        if isinstance(peers, list):
            peers = ",".join(str(peer) for peer in peers)

        result = tool_factor_exposure.invoke(
            {"stock_code": state["stock_code"], "period": state["period"], "peers": peers}
        )

        state["analysis_data"] = result
        return state

    def _capital_allocation_node(self, state: AgentState) -> AgentState:
        """Execute capital allocation analysis."""
        from app.agents.tools import tool_capital_allocation

        result = tool_capital_allocation.invoke(
            {
                "stock_code": state["stock_code"],
                "period": state["period"],
                "dividends": float(state["entities"].get("dividends", 0)),
                "buybacks": float(state["entities"].get("buybacks", 0)),
                "capex": float(state["entities"].get("capex", 0)),
            }
        )

        state["analysis_data"] = result
        return state

    def _ews_node(self, state: AgentState) -> AgentState:
        """Execute early warning system analysis."""
        from app.agents.tools import tool_ews

        result = tool_ews.invoke({"stock_code": state["stock_code"], "period": state["period"]})

        state["analysis_data"] = result
        return state

    def _answer_composer_node(self, state: AgentState) -> AgentState:
        """Compose an evidence-constrained answer from the research report."""
        report = state.get("report", {})
        if not report.get("findings"):
            gaps = report.get("data_gaps", [])
            detail = "；".join(gaps) if gaps else "找不到可用的財務資料"
            state["final_answer"] = f"Data not available / 無法完成分析：{detail}。"
            return state

        if not self.settings.openai_api_key:
            answer_parts = [
                f"結論：{report.get('verdict', '資料不足')}",
                f"投資論點：{report.get('investment_thesis', '')}",
            ]
            if report.get("key_risks"):
                answer_parts.append("主要風險：" + "；".join(report["key_risks"][:3]))
            if report.get("contradictions"):
                answer_parts.append("矛盾訊號：" + "；".join(report["contradictions"][:3]))
            if report.get("data_gaps"):
                answer_parts.append("資料缺口：" + "；".join(report["data_gaps"][:3]))
            state["final_answer"] = "\n\n".join(answer_parts)
            return state

        prompt = f"""
You are a professional financial analyst. Write a concise Traditional Chinese
answer using only the structured research report below.

User question: {state.get('query', '')}
Stock: {state.get('stock_code')}
Period: {state.get('period')}
Research report: {json.dumps(report, ensure_ascii=False)}

Requirements:
- State the verdict and investment thesis.
- Separate evidence, risks, contradictions, and data gaps.
- Do not add prices, forecasts, recommendations, or facts absent from the report.
- Explicitly qualify low-confidence or assumption-based findings.
"""

        response = self.llm.invoke(
            [HumanMessage(content=prompt)],
            config=self._langfuse_config(),
        )
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
        default_stock, default_period = self._default_stock_period()

        # Initialize state with latest local data fallback if not provided
        initial_state = AgentState(
            messages=[HumanMessage(content=query.query)],
            query=query.query,
            stock_code=query.stock_code or default_stock,
            period=query.period or default_period,
            intent="",
            entities={},
            analysis_data={},
            final_answer="",
            mode=query.mode,
            context=query.context,
            data_readiness={},
            research_plan=[],
            tool_results={},
            evidence=[],
            contradictions=[],
            report={},
            field_states={},
            failed_rules=[],
        )

        # Run the workflow
        final_state = self.graph.invoke(
            initial_state,
            config=self._langfuse_config(query),
        )

        # Build response
        report = final_state.get("report", {})
        score = float(report.get("confidence", 0.0))
        if score >= 0.75:
            confidence = "high"
        elif score >= 0.45:
            confidence = "medium"
        else:
            confidence = "low"

        return AgentResponse(
            query=query.query,
            answer=final_state["final_answer"],
            sources=list(
                dict.fromkeys(
                    evidence.get("source_type", "unknown")
                    for evidence in report.get("supporting_evidence", [])
                )
            ),
            analysis_steps=[
                f"Detected intent: {final_state['intent']}",
                f"Extracted entities: {final_state.get('entities')}",
                f"Data readiness: {final_state.get('data_readiness', {}).get('status')}",
                f"Research plan: {', '.join(final_state.get('research_plan', []))}",
            ],
            data=final_state.get("analysis_data", {}),
            confidence=confidence,
            confidence_score=score,
            verdict=report.get("verdict"),
            research_plan=final_state.get("research_plan", []),
            findings=report.get("findings", []),
            evidence=report.get("supporting_evidence", []),
            risks=report.get("key_risks", []),
            contradictions=report.get("contradictions", []),
            data_gaps=report.get("data_gaps", []),
            watch_items=report.get("watch_items", []),
        )
