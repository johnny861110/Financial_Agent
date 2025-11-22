# Financial Report Agent - Streamlit UI

"""
Main Streamlit application for Financial Report Agent.
Provides a user-friendly interface for financial analysis.
"""

import streamlit as st
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure page
st.set_page_config(
    page_title="Financial Report Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        padding-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .stButton>button {
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# Main page
def main():
    """Main page with navigation."""
    
    # Header
    st.markdown('<div class="main-header">📊 Financial Report Agent</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">AI-Powered Financial Analysis for Professional Fund Managers</div>',
        unsafe_allow_html=True
    )
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "Select Analysis Type",
        [
            "🏠 Home",
            "📈 Financial Snapshot",
            "📉 Trend Analysis",
            "👥 Peer Comparison",
            "⭐ Management Score",
            "💎 Earnings Quality",
            "💰 ROIC vs WACC",
            "🎯 Factor Exposure",
            "🚨 Early Warning System",
            "🤖 AI Agent Chat",
        ]
    )
    
    # Settings in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("Settings")
    
    # Data directory
    data_dir = st.sidebar.text_input(
        "Data Directory",
        value="./data/financial_reports",
        help="Directory containing financial data JSON files"
    )
    
    # API status
    st.sidebar.markdown("---")
    st.sidebar.subheader("API Status")
    
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            st.sidebar.success("✅ API Connected")
        else:
            st.sidebar.error("❌ API Error")
    except:
        st.sidebar.warning("⚠️ API Not Running")
        st.sidebar.caption("Start with: `uvicorn app.main:app`")
    
    # Route to pages
    if page == "🏠 Home":
        show_home()
    elif page == "📈 Financial Snapshot":
        from ui.pages import snapshot
        snapshot.show()
    elif page == "📉 Trend Analysis":
        from ui.pages import trend
        trend.show()
    elif page == "👥 Peer Comparison":
        from ui.pages import peer
        peer.show()
    elif page == "⭐ Management Score":
        from ui.pages import management
        management.show()
    elif page == "💎 Earnings Quality":
        from ui.pages import earnings_quality
        earnings_quality.show()
    elif page == "💰 ROIC vs WACC":
        from ui.pages import roic_wacc
        roic_wacc.show()
    elif page == "🎯 Factor Exposure":
        from ui.pages import factor
        factor.show()
    elif page == "🚨 Early Warning System":
        from ui.pages import ews
        ews.show()
    elif page == "🤖 AI Agent Chat":
        from ui.pages import agent
        agent.show()


def show_home():
    """Show home page with overview."""
    
    # Feature cards
    st.markdown("## 🎯 Key Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 📊 Core Analytics
        - Financial Snapshot Analysis
        - Multi-period Trend Analysis
        - Peer Comparison
        - Comprehensive Metrics
        """)
    
    with col2:
        st.markdown("""
        ### ⭐ Professional Scoring
        - Management Quality Score
        - Earnings Quality Score
        - ROIC vs WACC Analysis
        - Factor Exposure Analysis
        """)
    
    with col3:
        st.markdown("""
        ### 🤖 AI-Powered
        - Natural Language Queries
        - Automated Analysis
        - Risk Detection
        - Intelligent Insights
        """)
    
    st.markdown("---")
    
    # Quick Start
    st.markdown("## 🚀 Quick Start")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 1. Prepare Your Data
        Place your financial data JSON files in the data directory:
        ```
        data/financial_reports/
        ├── 2330_2023Q3_enhanced.json
        ├── 2454_2023Q3_enhanced.json
        └── ...
        ```
        """)
        
        st.markdown("""
        ### 2. Start the API Server
        ```bash
        uvicorn app.main:app --reload
        ```
        """)
    
    with col2:
        st.markdown("""
        ### 3. Use the Interface
        - Select an analysis type from the sidebar
        - Enter stock code and period
        - View comprehensive results
        - Export analysis reports
        """)
        
        st.markdown("""
        ### 4. AI Agent Chat
        Ask questions in natural language:
        - "What is the financial health of TSMC?"
        - "Compare TSMC with MediaTek"
        - "Show me the management quality"
        """)
    
    st.markdown("---")
    
    # Sample Data
    st.markdown("## 📝 Sample Data Format")
    
    with st.expander("View Sample JSON Structure"):
        st.code("""
{
  "stock_code": "2330",
  "company_name": "TSMC",
  "report_year": 2023,
  "report_season": 3,
  "report_period": "2023Q3",
  "currency": "TWD",
  "unit": "thousand",
  
  "cash_and_equivalents": 1500000000,
  "accounts_receivable": 300000000,
  "inventory": 200000000,
  "total_assets": 5000000000,
  "total_liabilities": 2000000000,
  "equity": 3000000000,
  
  "net_revenue": 800000000,
  "gross_profit": 400000000,
  "operating_income": 350000000,
  "net_income": 300000000,
  "eps": 9.65
}
        """, language="json")
    
    st.markdown("---")
    
    # About
    st.markdown("## ℹ️ About")
    
    st.info("""
    **Financial Report Agent v2.0**
    
    This application provides professional-grade financial analysis tools designed for fund managers 
    and investment professionals. It combines structured analytics with AI-powered insights to help 
    you make informed investment decisions.
    
    **Tech Stack:** FastAPI, LangGraph, OpenAI GPT, Streamlit
    
    **License:** MIT
    """)
    
    # Footer
    st.markdown("---")
    st.markdown(
        '<div style="text-align: center; color: #666;">Built with ❤️ using Streamlit</div>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
