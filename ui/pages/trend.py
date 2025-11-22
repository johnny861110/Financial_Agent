"""Trend Analysis page."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from app.services import TrendService


def show():
    """Display trend analysis page."""
    
    st.title("📉 Trend Analysis")
    st.markdown("Analyze financial trends across multiple periods.")
    
    # Input section
    stock_code = st.text_input(
        "Stock Code",
        value="2330",
        help="Enter the stock ticker code"
    )
    
    if st.button("📊 Analyze Trends", type="primary"):
        with st.spinner("Analyzing trends..."):
            service = TrendService()
            result = service.analyze_trend(stock_code)
            
            if result:
                display_trend_results(result)
            else:
                st.error("❌ Insufficient data for trend analysis. Please ensure multiple periods are available.")


def display_trend_results(result):
    """Display trend analysis results."""
    
    # Company info
    st.success(f"✅ Analyzed: **{result.company_name}** ({result.stock_code})")
    
    # Summary
    st.markdown("---")
    st.subheader("📝 Trend Summary")
    st.info(result.summary)
    
    # Metrics overview
    st.markdown("---")
    st.subheader("📊 Trend Indicators")
    
    improving = [m for m in result.metrics if m.trend_direction == "improving"]
    declining = [m for m in result.metrics if m.trend_direction == "declining"]
    stable = [m for m in result.metrics if m.trend_direction == "stable"]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Improving Metrics", len(improving), delta="positive")
        if improving:
            for m in improving:
                st.caption(f"✅ {m.metric_name}")
    
    with col2:
        st.metric("Declining Metrics", len(declining), delta="negative")
        if declining:
            for m in declining:
                st.caption(f"⬇️ {m.metric_name}")
    
    with col3:
        st.metric("Stable Metrics", len(stable))
        if stable:
            for m in stable:
                st.caption(f"➡️ {m.metric_name}")
    
    # Individual metric charts
    st.markdown("---")
    st.subheader("📈 Metric Trends")
    
    for metric in result.metrics:
        with st.expander(f"📊 {metric.metric_name}", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Latest Value", f"{metric.latest_value:.2f}")
            
            with col2:
                direction_emoji = {
                    "improving": "📈",
                    "declining": "📉",
                    "stable": "➡️"
                }
                st.metric("Trend", f"{direction_emoji.get(metric.trend_direction, '')} {metric.trend_direction.title()}")
            
            with col3:
                if metric.yoy_change is not None:
                    st.metric("YoY Change", f"{metric.yoy_change:+.2f}%")
                else:
                    st.metric("YoY Change", "N/A")
            
            # Line chart
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=metric.periods,
                y=metric.values,
                mode='lines+markers',
                name=metric.metric_name,
                line=dict(width=3),
                marker=dict(size=10)
            ))
            
            fig.update_layout(
                title=f"{metric.metric_name} Trend",
                xaxis_title="Period",
                yaxis_title="Value",
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Combined comparison chart
    st.markdown("---")
    st.subheader("🔄 Multi-Metric Comparison")
    
    selected_metrics = st.multiselect(
        "Select metrics to compare",
        [m.metric_name for m in result.metrics],
        default=[result.metrics[0].metric_name, result.metrics[1].metric_name] if len(result.metrics) >= 2 else [result.metrics[0].metric_name]
    )
    
    if selected_metrics:
        fig = go.Figure()
        
        for metric in result.metrics:
            if metric.metric_name in selected_metrics:
                fig.add_trace(go.Scatter(
                    x=metric.periods,
                    y=metric.values,
                    mode='lines+markers',
                    name=metric.metric_name
                ))
        
        fig.update_layout(
            title="Multi-Metric Trend Comparison",
            xaxis_title="Period",
            yaxis_title="Value",
            height=500,
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Data table
    st.markdown("---")
    st.subheader("📋 Detailed Data")
    
    # Create DataFrame for all metrics
    data_dict = {"Period": result.metrics[0].periods}
    for metric in result.metrics:
        data_dict[metric.metric_name] = metric.values
    
    df = pd.DataFrame(data_dict)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Download option
    if st.button("📥 Download Trend Data"):
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"{result.stock_code}_trend_analysis.csv",
            mime="text/csv"
        )
