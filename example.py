"""Example script demonstrating how to use the Financial Agent."""

import asyncio
from app.agents import FinancialAgent
from app.models.agent_models import AgentQuery
from app.services import (
    SnapshotService,
    ManagementService,
    EarningsQualityService,
    ROICWACCService,
)


def example_snapshot_analysis():
    """Example: Get financial snapshot."""
    print("\n=== Example 1: Financial Snapshot ===")
    
    service = SnapshotService()
    result = service.get_summary("2330", "2023Q3")
    
    if result:
        print(f"Company: {result['identification']['company_name']}")
        print(f"Period: {result['identification']['period']}")
        print(f"\nMargins:")
        print(f"  Gross Margin: {result['margins']['gross_margin']}%")
        print(f"  Operating Margin: {result['margins']['operating_margin']}%")
        print(f"  Net Margin: {result['margins']['net_margin']}%")
        print(f"\nReturns:")
        print(f"  ROA: {result['returns']['roa']}%")
        print(f"  ROE: {result['returns']['roe']}%")
    else:
        print("Data not found. Please add sample data files.")


def example_management_score():
    """Example: Calculate management quality score."""
    print("\n=== Example 2: Management Quality Score ===")
    
    service = ManagementService()
    score = service.calculate_score(
        ceo_tenure_years=5,
        cfo_tenure_years=4,
        board_independence_ratio=0.4,
        insider_buys=3,
        insider_sells=1,
        governance_incidents=0,
        audit_issues=0,
        related_party_transactions=0,
    )
    
    print(f"Total Score: {score.total:.1f}/100")
    print(f"\nComponents:")
    print(f"  Tenure Stability: {score.tenure_stability:.1f}")
    print(f"  Board Independence: {score.board_independence:.1f}")
    print(f"  Insider Alignment: {score.insider_alignment:.1f}")
    print(f"  Governance: {score.governance_red_flags:.1f}")
    print(f"\nCommentary: {score.commentary}")


def example_earnings_quality():
    """Example: Calculate earnings quality score."""
    print("\n=== Example 3: Earnings Quality Score ===")
    
    service = EarningsQualityService()
    score = service.calculate_score("2330", "2023Q3")
    
    if score:
        print(f"Total Score: {score.total:.1f}/100")
        print(f"\nComponents:")
        print(f"  Accrual Quality: {score.accrual_quality:.1f}")
        print(f"  Working Capital: {score.working_capital_behavior:.1f}")
        print(f"  One-off Dependency: {score.one_off_dependency:.1f}")
        print(f"  Earnings Stability: {score.earnings_stability:.1f}")
        
        if score.red_flags:
            print(f"\nRed Flags:")
            for flag in score.red_flags:
                print(f"  - {flag}")
        
        print(f"\nCommentary: {score.commentary}")
    else:
        print("Data not found. Please add sample data files.")


def example_roic_wacc():
    """Example: ROIC vs WACC analysis."""
    print("\n=== Example 4: ROIC vs WACC Analysis ===")
    
    service = ROICWACCService()
    analysis = service.analyze("2330", "2023Q3", market_beta=1.2)
    
    if analysis:
        print(f"ROIC: {analysis.roic:.2f}%")
        print(f"WACC: {analysis.wacc:.2f}%")
        print(f"Value Creation Gap: {analysis.value_creation_gap:.2f}%")
        print(f"Creating Value: {'Yes' if analysis.is_value_creating else 'No'}")
        print(f"\nCommentary: {analysis.commentary}")
    else:
        print("Data not found. Please add sample data files.")


def example_agent_query():
    """Example: Using the LangGraph agent."""
    print("\n=== Example 5: Agent Natural Language Query ===")
    
    try:
        agent = FinancialAgent()
        
        query = AgentQuery(
            query="What are the key financial metrics for TSMC in Q3 2023?",
            stock_code="2330",
            period="2023Q3"
        )
        
        response = agent.query(query)
        
        print(f"Query: {response.query}")
        print(f"\nAnswer: {response.answer}")
        print(f"\nSources: {', '.join(response.sources)}")
        print(f"Confidence: {response.confidence}")
    except Exception as e:
        print(f"Agent error: {e}")
        print("Note: Make sure OPENAI_API_KEY is set in your .env file")


def main():
    """Run all examples."""
    print("=" * 60)
    print("Financial Report Agent - Examples")
    print("=" * 60)
    
    # Run examples
    example_snapshot_analysis()
    example_management_score()
    example_earnings_quality()
    example_roic_wacc()
    example_agent_query()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
