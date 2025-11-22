"""Earnings Quality Score page."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from app.services import EarningsQualityService


def show():
    """Display earnings quality scoring page."""
    
    st.title("💎 Earnings Quality Score")
    st.markdown("Assess earnings quality and identify accounting red flags.")
    
    st.markdown("---")
    
    # Input form
    with st.form("earnings_quality_form"):
        st.subheader("📝 Financial Data Input")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Income Statement**")
            net_income = st.number_input("Net Income (M)", value=100.0, step=10.0)
            operating_cf = st.number_input("Operating Cash Flow (M)", value=120.0, step=10.0)
            revenue = st.number_input("Revenue (M)", value=1000.0, step=50.0)
            
            st.markdown("**Working Capital**")
            ar_change = st.number_input("AR Change (M)", value=10.0, step=5.0, help="Accounts Receivable change")
            inventory_change = st.number_input("Inventory Change (M)", value=5.0, step=5.0)
            ap_change = st.number_input("AP Change (M)", value=-8.0, step=5.0, help="Accounts Payable change")
        
        with col2:
            st.markdown("**Non-Recurring Items**")
            one_time_gains = st.number_input("One-time Gains (M)", value=0.0, step=5.0)
            one_time_losses = st.number_input("One-time Losses (M)", value=0.0, step=5.0)
            restructuring = st.number_input("Restructuring Charges (M)", value=0.0, step=5.0)
            
            st.markdown("**Historical Volatility**")
            earnings_std = st.number_input("Earnings Std Dev (M)", value=15.0, step=5.0, help="Standard deviation of earnings")
            avg_earnings = st.number_input("Average Earnings (M)", value=100.0, step=10.0, help="Mean earnings over period")
        
        st.markdown("**Depreciation & Amortization**")
        depreciation_amort = st.number_input("D&A (M)", value=50.0, step=5.0)
        
        submitted = st.form_submit_button("🧮 Calculate Score", type="primary")
    
    if submitted:
        with st.spinner("Calculating earnings quality score..."):
            from app.models import EarningsQualityScore
            
            # Calculate component scores
            # Accrual Quality: Compare net income to operating cash flow
            accrual_ratio = abs(net_income - operating_cf) / net_income if net_income != 0 else 0
            accrual_score = max(0, 100 - accrual_ratio * 200)  # Lower accruals = higher quality
            
            # Working Capital Behavior: Abnormal changes
            wc_change = ar_change + inventory_change - ap_change
            wc_ratio = abs(wc_change) / revenue if revenue != 0 else 0
            wc_score = max(0, 100 - wc_ratio * 500)
            
            # One-off Dependency: Reliance on non-recurring items
            one_off_total = abs(one_time_gains - one_time_losses + restructuring)
            one_off_ratio = one_off_total / abs(net_income) if net_income != 0 else 0
            one_off_score = max(0, 100 - one_off_ratio * 200)
            
            # Earnings Stability: Based on volatility
            volatility_coef = earnings_std / avg_earnings if avg_earnings != 0 else 0
            stability_score = max(0, 100 - volatility_coef * 100)
            
            # Create score object
            score = EarningsQualityScore(
                accrual_quality=accrual_score,
                working_capital_behavior=wc_score,
                one_off_dependency=one_off_score,
                earnings_stability=stability_score,
                commentary=f"Overall earnings quality score calculated from {len([s for s in [accrual_score, wc_score, one_off_score, stability_score] if s < 60])} concerning metrics."
            )
            
            # Detect red flags
            red_flags = []
            if accrual_ratio > 0.3:
                red_flags.append("High accruals: Net income significantly exceeds cash flow")
            if wc_ratio > 0.15:
                red_flags.append("Abnormal working capital changes detected")
            if one_off_ratio > 0.25:
                red_flags.append("Heavy reliance on one-time items")
            if volatility_coef > 0.5:
                red_flags.append("High earnings volatility indicates instability")
            if operating_cf < 0:
                red_flags.append("Negative operating cash flow")
            
            score = EarningsQualityScore(
                accrual_quality=accrual_score,
                working_capital_behavior=wc_score,
                one_off_dependency=one_off_score,
                earnings_stability=stability_score,
                red_flags=red_flags,
                commentary=f"Earnings quality analysis based on {len(red_flags)} red flags detected.",
                details={
                    "accrual_ratio": accrual_ratio,
                    "wc_change": wc_change,
                    "one_off_ratio": one_off_ratio,
                    "volatility_coef": volatility_coef
                }
            )
            
            display_earnings_quality_score(score)


def display_earnings_quality_score(score):
    """Display earnings quality score results."""
    
    st.markdown("---")
    
    # Overall score
    st.subheader("🎯 Overall Earnings Quality Score")
    
    # Score gauge
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score.total,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Overall Score"},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': get_score_color(score.total)},
            'steps': [
                {'range': [0, 40], 'color': "lightcoral"},
                {'range': [40, 60], 'color': "lightyellow"},
                {'range': [60, 80], 'color': "lightgreen"},
                {'range': [80, 100], 'color': "darkgreen"}
            ],
            'threshold': {
                'line': {'color': "blue", 'width': 4},
                'thickness': 0.75,
                'value': 70
            }
        }
    ))
    
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)
    
    # Interpretation
    interpretation = get_score_interpretation(score.total)
    if score.total < 50:
        st.error(f"**{interpretation}**")
    elif score.total < 70:
        st.warning(f"**{interpretation}**")
    else:
        st.success(f"**{interpretation}**")
    
    # Component scores
    st.markdown("---")
    st.subheader("📊 Component Scores")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_color = "inverse" if score.accrual_quality < 60 else "normal"
        st.metric(
            "Accrual Quality",
            f"{score.accrual_quality:.1f}",
            help="Quality of accruals vs cash earnings"
        )
    
    with col2:
        st.metric(
            "Working Capital",
            f"{score.working_capital_quality:.1f}",
            help="Working capital management quality"
        )
    
    with col3:
        st.metric(
            "One-off Dependency",
            f"{score.one_off_dependency:.1f}",
            help="Reliance on non-recurring items"
        )
    
    with col4:
        st.metric(
            "Earnings Stability",
            f"{score.earnings_stability:.1f}",
            help="Consistency of earnings over time"
        )
    
    # Component bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=['Accrual Quality', 'Working Capital', 'One-off Dependency', 'Earnings Stability'],
        y=[score.accrual_quality, score.working_capital_quality, 
           score.one_off_dependency, score.earnings_stability],
        marker_color=[get_score_color(score.accrual_quality), 
                      get_score_color(score.working_capital_quality),
                      get_score_color(score.one_off_dependency),
                      get_score_color(score.earnings_stability)],
        text=[f"{score.accrual_quality:.1f}", f"{score.working_capital_quality:.1f}",
              f"{score.one_off_dependency:.1f}", f"{score.earnings_stability:.1f}"],
        textposition='outside'
    ))
    
    fig.update_layout(
        title="Component Score Breakdown",
        yaxis_title="Score",
        yaxis_range=[0, 105],
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Red flags
    red_flags = score.red_flags
    if red_flags:
        st.markdown("---")
        st.subheader("🚩 Red Flags Detected")
        
        for flag in red_flags:
            st.error(f"⚠️ {flag}")
    else:
        st.success("✅ No significant red flags detected")
    
    # Commentary
    st.markdown("---")
    st.subheader("💬 Analysis Commentary")
    st.write(score.commentary)
    
    # Detailed metrics
    if score.details:
        st.markdown("---")
        st.subheader("📋 Detailed Metrics")
        
        details_df = pd.DataFrame([
            {"Metric": key.replace('_', ' ').title(), "Value": f"{value:.2f}" if isinstance(value, (int, float)) else value}
            for key, value in score.details.items()
        ])
        
        st.dataframe(details_df, use_container_width=True, hide_index=True)
    
    # Action items
    st.markdown("---")
    st.subheader("✅ Action Items")
    
    action_items = get_action_items(score)
    for item in action_items:
        st.markdown(f"- {item}")


def get_score_color(score):
    """Get color based on score."""
    if score >= 70:
        return "darkgreen"
    elif score >= 50:
        return "green"
    elif score >= 40:
        return "orange"
    else:
        return "red"


def get_score_interpretation(score):
    """Get interpretation based on score."""
    if score >= 80:
        return "🟢 Excellent - High-quality earnings with strong cash generation"
    elif score >= 70:
        return "🟢 Good - Solid earnings quality with minor concerns"
    elif score >= 50:
        return "🟡 Fair - Moderate earnings quality, requires monitoring"
    elif score >= 40:
        return "🟠 Poor - Low earnings quality with accounting concerns"
    else:
        return "🔴 Critical - Severe earnings quality issues detected"


def get_action_items(score):
    """Generate action items based on score."""
    items = []
    
    if score.accrual_quality < 50:
        items.append("🔍 Deep dive into accrual components - review revenue recognition and expense timing")
    
    if score.working_capital_quality < 50:
        items.append("📊 Analyze working capital trends - investigate AR aging and inventory turnover")
    
    if score.one_off_dependency < 50:
        items.append("⚠️ Scrutinize non-recurring items - verify if truly one-time or recurring pattern")
    
    if score.earnings_stability < 50:
        items.append("📈 Review earnings volatility drivers - assess business model stability")
    
    if len(score.red_flags) >= 3:
        items.append("🚨 Consider reducing position size due to multiple red flags")
    
    if score.total < 50:
        items.append("🔴 Schedule management Q&A call to discuss earnings quality concerns")
    
    if not items:
        items.append("✅ Continue regular monitoring - earnings quality is acceptable")
    
    return items
