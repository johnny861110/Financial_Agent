import pytest
from app.agents.workflow import FinancialAgent
from app.models.agent_models import AgentQuery

def test_agent_intent_and_entity_extraction():
    agent = FinancialAgent()
    
    # Test 1: Complex ROIC/WACC query with parameters
    query1 = AgentQuery(
        query="Analyze the ROIC vs WACC for 2330 in 2023Q3, assuming a beta of 1.2",
        stock_code="2330",
        period="2023Q3"
    )
    response1 = agent.query(query1)
    print(f"\nTest 1 Query: {query1.query}")
    print(f"Detected Intent: {response1.analysis_steps[0]}")
    print(f"Extracted Entities: {response1.analysis_steps[1]}")
    print(f"Answer Preview: {response1.answer[:100]}...")
    
    assert "roic_wacc" in response1.analysis_steps[0].lower()
    
    # Test 2: Management query with implied parameters
    query2 = AgentQuery(
        query="What is the management quality score? Assume CEO tenure is 10 years and 5 insider buys.",
        stock_code="2330",
        period="2023Q3"
    )
    response2 = agent.query(query2)
    print(f"\nTest 2 Query: {query2.query}")
    print(f"Detected Intent: {response2.analysis_steps[0]}")
    print(f"Extracted Entities: {response2.analysis_steps[1]}")
    
    assert "management" in response2.analysis_steps[0].lower()
    # Check if data was used (not just defaults)
    if response2.data.get("success"):
        details = response2.data.get("data", {}).get("components", {})
        print(f"Tenure Score: {details.get('tenure_stability')}")

def test_agent_fallback_mechanism():
    agent = FinancialAgent()
    
    # Test 3: Query for non-existent stock to test error handling
    query3 = AgentQuery(
        query="Give me a snapshot of NON_EXISTENT_STOCK for 2025Q4",
    )
    response3 = agent.query(query3)
    print(f"\nTest 3 (Error Handling): {response3.answer}")
    assert "issue" in response3.answer.lower() or "not available" in response3.answer.lower()

if __name__ == "__main__":
    # Manually run tests if needed
    test_agent_intent_and_entity_extraction()
    test_agent_fallback_mechanism()
