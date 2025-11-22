"""Peer Comparison page."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from app.services import PeerService


def show():
    """Display peer comparison page."""
    
    st.title("👥 Peer Comparison")
    st.markdown("Compare multiple companies on key financial metrics.")
    
    # Input section
    st.subheader("📝 Input Companies")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        stock_codes = st.text_input(
            "Stock Codes (comma-separated)",
            value="2330,2454,3711",
            help="Enter multiple stock codes separated by commas"
        )
    
    with col2:
        period = st.text_input(
            "Period",
            value="2023Q3",
            help="Reporting period"
        )
    
    # Metric selection
    available_metrics = [
        "Gross Margin",
        "Operating Margin",
        "Net Margin",
        "ROE",
        "ROA",
        "Debt Ratio",
        "Current Ratio"
    ]
    
    selected_metrics = st.multiselect(
        "Select Metrics to Compare",
        available_metrics,
        default=["Gross Margin", "Operating Margin", "ROE", "Debt Ratio"]
    )
    
    if st.button("🔍 Compare", type="primary"):
        if not selected_metrics:
            st.warning("⚠️ Please select at least one metric to compare.")
            return
        
        with st.spinner("Comparing companies..."):
            codes = [c.strip() for c in stock_codes.split(',')]
            service = PeerService()
            result = service.compare_peers(codes, period, selected_metrics)
            
            if result:
                display_peer_results(result)
            else:
                st.error("❌ Insufficient data for comparison. Please check the stock codes and period.")


def display_peer_results(result):
    """Display peer comparison results."""
    
    st.success(f"✅ Comparison for period: **{result.period}**")
    
    # Summary
    st.markdown("---")
    st.subheader("📊 Summary")
    st.info(result.summary)
    
    # Individual metric comparisons
    st.markdown("---")
    st.subheader("📈 Metric Comparisons")
    
    for comp in result.comparisons:
        with st.expander(f"📊 {comp.metric_name}", expanded=True):
            # Metrics overview
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Best Performer", comp.best_performer, delta="🏆")
            
            with col2:
                st.metric("Worst Performer", comp.worst_performer, delta="⚠️")
            
            # Bar chart
            fig = go.Figure()
            
            # Color code by ranking
            colors = ['#2ca02c' if r == 1 else '#ff7f0e' if r == len(comp.ranking) else '#1f77b4' 
                      for r in comp.ranking]
            
            fig.add_trace(go.Bar(
                x=comp.companies,
                y=comp.values,
                marker_color=colors,
                text=[f"{v:.2f}" for v in comp.values],
                textposition='auto',
            ))
            
            fig.update_layout(
                title=f"{comp.metric_name} Comparison",
                xaxis_title="Company",
                yaxis_title="Value",
                height=400,
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Ranking table
            ranking_df = pd.DataFrame({
                "Rank": comp.ranking,
                "Company": comp.companies,
                "Value": [f"{v:.2f}" for v in comp.values]
            }).sort_values("Rank")
            
            st.dataframe(ranking_df, use_container_width=True, hide_index=True)
    
    # Radar chart for overall comparison
    st.markdown("---")
    st.subheader("🎯 Overall Performance Radar")
    
    if len(result.comparisons) >= 3:
        fig = go.Figure()
        
        for i, company in enumerate(result.comparisons[0].companies):
            values = []
            for comp in result.comparisons:
                idx = comp.companies.index(company)
                # Normalize to 0-100 scale for better visualization
                max_val = max(comp.values)
                min_val = min(comp.values)
                if max_val != min_val:
                    normalized = ((comp.values[idx] - min_val) / (max_val - min_val)) * 100
                else:
                    normalized = 50
                values.append(normalized)
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=[comp.metric_name for comp in result.comparisons],
                fill='toself',
                name=company
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            showlegend=True,
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Comparison matrix
    st.markdown("---")
    st.subheader("📋 Comparison Matrix")
    
    matrix_data = {"Metric": [comp.metric_name for comp in result.comparisons]}
    for company in result.comparisons[0].companies:
        values = []
        for comp in result.comparisons:
            idx = comp.companies.index(company)
            values.append(f"{comp.values[idx]:.2f} (#{comp.ranking[idx]})")
        matrix_data[company] = values
    
    matrix_df = pd.DataFrame(matrix_data)
    st.dataframe(matrix_df, use_container_width=True, hide_index=True)
    
    # Download option
    if st.button("📥 Download Comparison Report"):
        csv = matrix_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"peer_comparison_{result.period}.csv",
            mime="text/csv"
        )
