"""Financial Snapshot page."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from app.services import SnapshotService


def show():
    """Display financial snapshot analysis page."""
    
    st.title("📈 Financial Snapshot Analysis")
    st.markdown("Analyze single-period financial metrics and derived ratios.")
    
    # Input section
    col1, col2 = st.columns(2)
    
    with col1:
        stock_code = st.text_input(
            "Stock Code",
            value="2330",
            help="Enter the stock ticker code"
        )
    
    with col2:
        period = st.text_input(
            "Period",
            value="2023Q3",
            help="Enter the reporting period (e.g., 2023Q3)"
        )
    
    if st.button("🔍 Analyze", type="primary"):
        with st.spinner("Loading financial data..."):
            service = SnapshotService()
            result = service.get_summary(stock_code, period)
            
            if result:
                display_snapshot_results(result)
            else:
                st.error("❌ Data not found. Please check the stock code and period.")


def display_snapshot_results(result):
    """Display snapshot analysis results."""
    
    # Company info
    st.success(f"✅ Loaded: **{result['identification']['company_name']}** - {result['identification']['period']}")
    
    # Key metrics overview
    st.markdown("---")
    st.subheader("📊 Key Metrics Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        revenue = result['income_statement']['net_revenue']
        st.metric("Net Revenue", f"{revenue:,.0f}", help="Net revenue for the period")
    
    with col2:
        net_income = result['income_statement']['net_income']
        st.metric("Net Income", f"{net_income:,.0f}", help="Net income for the period")
    
    with col3:
        eps = result['income_statement']['eps']
        st.metric("EPS", f"{eps:.2f}", help="Earnings per share")
    
    with col4:
        assets = result['balance_sheet']['total_assets']
        st.metric("Total Assets", f"{assets:,.0f}", help="Total assets")
    
    # Margins
    st.markdown("---")
    st.subheader("📈 Profitability Margins")
    
    margins = result['margins']
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Gross Margin", f"{margins['gross_margin']:.2f}%", delta=None)
    
    with col2:
        st.metric("Operating Margin", f"{margins['operating_margin']:.2f}%", delta=None)
    
    with col3:
        st.metric("Net Margin", f"{margins['net_margin']:.2f}%", delta=None)
    
    # Margin chart
    fig = go.Figure(data=[
        go.Bar(
            x=['Gross Margin', 'Operating Margin', 'Net Margin'],
            y=[margins['gross_margin'], margins['operating_margin'], margins['net_margin']],
            marker_color=['#1f77b4', '#ff7f0e', '#2ca02c'],
            text=[f"{margins['gross_margin']:.1f}%", 
                  f"{margins['operating_margin']:.1f}%", 
                  f"{margins['net_margin']:.1f}%"],
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title="Profitability Margins (%)",
        xaxis_title="Metric",
        yaxis_title="Percentage (%)",
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Financial Structure
    st.markdown("---")
    st.subheader("🏦 Financial Structure")
    
    structure = result['financial_structure']
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Debt Ratio", f"{structure['debt_ratio']:.2f}%", help="Total liabilities / Total assets")
    
    with col2:
        st.metric("Equity Ratio", f"{structure['equity_ratio']:.2f}%", help="Equity / Total assets")
    
    with col3:
        if structure['current_ratio']:
            st.metric("Current Ratio", f"{structure['current_ratio']:.2f}", help="Current assets / Current liabilities")
        else:
            st.metric("Current Ratio", "N/A")
    
    # Structure pie chart
    fig = go.Figure(data=[
        go.Pie(
            labels=['Liabilities', 'Equity'],
            values=[structure['debt_ratio'], structure['equity_ratio']],
            hole=0.4,
            marker_colors=['#ff7f0e', '#2ca02c']
        )
    ])
    
    fig.update_layout(
        title="Capital Structure",
        height=400,
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Returns
    st.markdown("---")
    st.subheader("💰 Return Metrics")
    
    returns = result['returns']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("ROA (Annualized)", f"{returns['roa']:.2f}%", help="Return on Assets")
    
    with col2:
        st.metric("ROE (Annualized)", f"{returns['roe']:.2f}%", help="Return on Equity")
    
    # Balance Sheet Details
    st.markdown("---")
    st.subheader("📋 Balance Sheet Details")
    
    balance_sheet_df = pd.DataFrame({
        "Item": ["Total Assets", "Total Liabilities", "Equity", "Cash & Equivalents"],
        "Amount": [
            result['balance_sheet']['total_assets'],
            result['balance_sheet']['total_liabilities'],
            result['balance_sheet']['equity'],
            result['balance_sheet']['cash_and_equivalents'],
        ]
    })
    
    st.dataframe(balance_sheet_df, use_container_width=True, hide_index=True)
    
    # Income Statement Details
    st.markdown("---")
    st.subheader("💵 Income Statement Details")
    
    income_df = pd.DataFrame({
        "Item": ["Net Revenue", "Gross Profit", "Operating Income", "Net Income", "EPS"],
        "Amount": [
            result['income_statement']['net_revenue'],
            result['income_statement']['gross_profit'],
            result['income_statement']['operating_income'],
            result['income_statement']['net_income'],
            result['income_statement']['eps'],
        ]
    })
    
    st.dataframe(income_df, use_container_width=True, hide_index=True)
    
    # Download option
    st.markdown("---")
    if st.button("📥 Download Full Report"):
        import json
        json_str = json.dumps(result, indent=2, ensure_ascii=False)
        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name=f"{result['identification']['stock_code']}_{result['identification']['period']}_snapshot.json",
            mime="application/json"
        )
