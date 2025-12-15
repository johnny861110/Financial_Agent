"""Early Warning System page."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from app.services import EarlyWarningService


def show():
    """Display early warning system page."""
    
    st.title("🚨 Early Warning System")
    st.markdown("Real-time monitoring of financial health and risk signals.")
    
    st.markdown("---")
    
    # Input form
    with st.form("ews_form"):
        st.subheader("📝 Financial Health Indicators")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Liquidity Indicators**")
            current_ratio = st.number_input("Current Ratio", value=1.5, step=0.1, help="Current Assets / Current Liabilities")
            quick_ratio = st.number_input("Quick Ratio", value=1.0, step=0.1, help="(Current Assets - Inventory) / Current Liabilities")
            cash_ratio = st.number_input("Cash Ratio", value=0.5, step=0.1, help="Cash / Current Liabilities")
            
            st.markdown("**Profitability Trends**")
            revenue_growth = st.number_input("Revenue Growth YoY (%)", value=5.0, step=1.0)
            margin_trend = st.number_input("Margin Change YoY (bps)", value=50.0, step=10.0, help="Basis points change")
            earnings_decline = st.number_input("Earnings Decline Quarters", min_value=0, max_value=8, value=0, help="Consecutive quarters of decline")
        
        with col2:
            st.markdown("**Leverage & Solvency**")
            debt_to_equity = st.number_input("Debt to Equity", value=0.8, step=0.1)
            interest_coverage = st.number_input("Interest Coverage", value=5.0, step=0.5, help="EBIT / Interest Expense")
            debt_maturity = st.number_input("Debt Maturing < 1Y (%)", value=20.0, step=5.0)
            
            st.markdown("**Cash Flow & Operations**")
            fcf_margin = st.number_input("FCF Margin (%)", value=8.0, step=1.0, help="Free Cash Flow / Revenue")
            capex_to_revenue = st.number_input("CapEx to Revenue (%)", value=5.0, step=1.0)
            working_capital_days = st.number_input("Working Capital Days", value=60.0, step=5.0)
        
        st.markdown("**External Factors**")
        col3, col4 = st.columns(2)
        
        with col3:
            analyst_downgrades = st.number_input("Analyst Downgrades (3M)", min_value=0, max_value=20, value=0)
            credit_rating_change = st.selectbox("Credit Rating Change", 
                                                ["Upgrade", "Stable", "Downgrade", "Watch Negative"])
        
        with col4:
            covenant_breach = st.checkbox("Debt Covenant Breach")
            audit_qualification = st.checkbox("Audit Qualification")
            management_turnover = st.checkbox("Key Management Turnover")
        
        submitted = st.form_submit_button("🔍 Run Warning Detection", type="primary")
    
    if submitted:
        with st.spinner("Analyzing financial health indicators..."):
            # Note: This is a demo version. In production, would use actual stock data
            # For now, create an EarlyWarningSystem object directly
            from app.models import EarlyWarningSystem
            
            # Detect warning signals based on thresholds
            signals = []
            
            # Liquidity checks
            if current_ratio < 1.0:
                signals.append({"signal_name": "Low Current Ratio", "severity": "high", "current_value": current_ratio, "threshold_value": 1.0, "description": f"Current ratio {current_ratio:.2f} below 1.0"})
            if quick_ratio < 0.5:
                signals.append({"signal_name": "Liquidity Crisis", "severity": "critical", "current_value": quick_ratio, "threshold_value": 0.5, "description": f"Quick ratio {quick_ratio:.2f} critically low"})
            
            # Leverage checks
            if debt_to_equity > 2.0:
                signals.append({"signal_name": "High Leverage", "severity": "high", "current_value": debt_to_equity, "threshold_value": 2.0, "description": f"D/E ratio {debt_to_equity:.2f} exceeds 2.0"})
            if interest_coverage < 2.0:
                signals.append({"signal_name": "Interest Coverage Risk", "severity": "high", "current_value": interest_coverage, "threshold_value": 2.0, "description": f"Coverage {interest_coverage:.2f}x below safe level"})
            
            # Profitability checks
            if revenue_growth < -10:
                signals.append({"signal_name": "Revenue Decline", "severity": "medium", "current_value": revenue_growth, "threshold_value": -10.0, "description": f"Revenue declining {revenue_growth:.1f}% YoY"})
            if earnings_decline >= 2:
                signals.append({"signal_name": "Earnings Deterioration", "severity": "high", "current_value": float(earnings_decline), "threshold_value": 2.0, "description": f"{earnings_decline} quarters of declining earnings"})
            if fcf_margin < 0:
                signals.append({"signal_name": "Negative FCF", "severity": "critical", "current_value": fcf_margin, "threshold_value": 0.0, "description": "Company burning cash"})
            
            # Governance checks
            if covenant_breach:
                signals.append({"signal_name": "Covenant Breach", "severity": "critical", "current_value": 1.0, "threshold_value": 0.0, "description": "Debt covenant violation detected"})
            if audit_qualification:
                signals.append({"signal_name": "Audit Issues", "severity": "critical", "current_value": 1.0, "threshold_value": 0.0, "description": "Qualified audit opinion"})
            if management_turnover:
                signals.append({"signal_name": "Management Turnover", "severity": "medium", "current_value": 1.0, "threshold_value": 0.0, "description": "Key management changes"})
            
            # Analyst sentiment
            if analyst_downgrades >= 3:
                signals.append({"signal_name": "Analyst Downgrades", "severity": "medium", "current_value": float(analyst_downgrades), "threshold_value": 3.0, "description": f"{analyst_downgrades} downgrades in 3 months"})
            
            # Determine overall level
            critical_count = sum(1 for s in signals if s.get('severity') == 'critical')
            high_count = sum(1 for s in signals if s.get('severity') == 'high')
            
            if critical_count >= 2 or len(signals) >= 6:
                overall_level = "critical"
            elif critical_count >= 1 or high_count >= 2:
                overall_level = "high"
            elif len(signals) >= 2:
                overall_level = "medium"
            else:
                overall_level = "low"
            
            warnings = EarlyWarningSystem(
                warning_level=overall_level,
                triggered_signals=signals,
                recommendation=f"Total of {len(signals)} warning signals detected. Review financial health metrics closely and consider risk mitigation strategies.",
                recommendations=[f"Total of {len(signals)} warning signals detected", "Review financial health metrics closely", "Consider risk mitigation strategies"],
                commentary=f"Early warning system detected {len(signals)} signals at {overall_level} level."
            )
            
            display_warning_results(warnings)


def display_warning_results(warnings):
    """Display warning system results."""
    
    st.markdown("---")
    
    # Overall warning level
    st.subheader("⚠️ Overall Warning Level")
    
    level_color = get_warning_color(warnings.overall_level)
    level_emoji = get_warning_emoji(warnings.overall_level)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"### {level_emoji} {warnings.overall_level.upper()}")
    
    with col2:
        st.metric("Total Signals", len(warnings.triggered_signals))
    
    with col3:
        critical_count = sum(1 for s in warnings.triggered_signals if s.severity == 'critical')
        st.metric("Critical Signals", critical_count)
    
    # Warning level gauge
    level_value = {"low": 25, "medium": 50, "high": 75, "critical": 95}[warnings.overall_level]
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=level_value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Warning Level"},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': level_color},
            'steps': [
                {'range': [0, 25], 'color': "lightgreen"},
                {'range': [25, 50], 'color': "lightyellow"},
                {'range': [50, 75], 'color': "orange"},
                {'range': [75, 100], 'color': "red"}
            ],
            'threshold': {
                'line': {'color': "darkred", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)
    
    # Display based on warning level
    if warnings.overall_level == "critical":
        st.error("🚨 **CRITICAL WARNING**: Immediate attention required. Multiple severe risk factors detected.")
    elif warnings.overall_level == "high":
        st.warning("⚠️ **HIGH WARNING**: Significant concerns identified. Close monitoring recommended.")
    elif warnings.overall_level == "medium":
        st.info("ℹ️ **MEDIUM WARNING**: Some risk factors present. Monitor developments.")
    else:
        st.success("✅ **LOW WARNING**: Financial health appears stable. Continue regular monitoring.")
    
    # Triggered signals
    if warnings.triggered_signals:
        st.markdown("---")
        st.subheader("🚩 Triggered Warning Signals")
        
        # Group by severity
        critical_signals = [s for s in warnings.triggered_signals if s.severity == 'critical']
        high_signals = [s for s in warnings.triggered_signals if s.severity == 'high']
        medium_signals = [s for s in warnings.triggered_signals if s.severity == 'medium']
        
        if critical_signals:
            st.error("**CRITICAL SIGNALS**")
            for signal in critical_signals:
                display_signal(signal, "critical")
        
        if high_signals:
            st.warning("**HIGH PRIORITY SIGNALS**")
            for signal in high_signals:
                display_signal(signal, "high")
        
        if medium_signals:
            st.info("**MEDIUM PRIORITY SIGNALS**")
            for signal in medium_signals:
                display_signal(signal, "medium")
        
        # Signals timeline
        st.markdown("---")
        st.subheader("📅 Signal Timeline")
        
        display_signal_timeline(warnings.triggered_signals)
    else:
        st.success("✅ No warning signals triggered. Financial health indicators within acceptable ranges.")
    
    # Recommendations
    st.markdown("---")
    st.subheader("💡 Recommendations")
    
    for rec in warnings.recommendations:
        st.markdown(f"- {rec}")
    
    # Commentary
    st.markdown("---")
    st.subheader("💬 Analysis Commentary")
    st.write(warnings.commentary)
    
    # Action plan
    st.markdown("---")
    st.subheader("📋 Suggested Action Plan")
    
    action_plan = get_action_plan(warnings)
    for idx, action in enumerate(action_plan, 1):
        st.markdown(f"{idx}. {action}")
    
    # Historical tracking
    st.markdown("---")
    st.subheader("📊 Warning Level History")
    
    st.info("""
    **Best Practices:**
    - Review warning signals daily for critical-level situations
    - Conduct weekly deep dives for high-level warnings
    - Monthly reviews sufficient for low-level warnings
    - Document all signal triggers and management responses
    - Set up automated alerts for critical threshold breaches
    """)


def display_signal(signal, severity):
    """Display individual warning signal."""
    
    severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡"}
    
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"{severity_emoji.get(severity, '⚪')} **{signal.signal_name}**")
            st.caption(signal.description)
        
        with col2:
            st.caption(f"Severity: {severity.upper()}")


def display_signal_timeline(signals):
    """Display signals as timeline."""
    
    # Create mock timeline data
    timeline_data = []
    base_date = datetime.now()
    
    for idx, signal in enumerate(signals):
        timeline_data.append({
            "Date": (base_date - timedelta(days=idx*7)).strftime("%Y-%m-%d"),
            "Signal": signal.signal_name,
            "Severity": signal.severity.upper(),
            "Status": "Active"
        })
    
    timeline_df = pd.DataFrame(timeline_data)
    
    # Create Gantt-style chart
    fig = go.Figure()
    
    for idx, row in timeline_df.iterrows():
        color = {"CRITICAL": "red", "HIGH": "orange", "MEDIUM": "yellow"}.get(row['Severity'], "blue")
        
        fig.add_trace(go.Scatter(
            x=[row['Date']],
            y=[row['Signal']],
            mode='markers',
            marker=dict(size=15, color=color),
            name=row['Severity'],
            showlegend=(idx == 0),
            hovertext=f"{row['Signal']}<br>Severity: {row['Severity']}<br>Date: {row['Date']}"
        ))
    
    fig.update_layout(
        title="Warning Signals Over Time",
        xaxis_title="Date",
        yaxis_title="Signal Type",
        height=400,
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)


def get_warning_color(level):
    """Get color for warning level."""
    colors = {
        "low": "green",
        "medium": "yellow",
        "high": "orange",
        "critical": "red"
    }
    return colors.get(level, "gray")


def get_warning_emoji(level):
    """Get emoji for warning level."""
    emojis = {
        "low": "✅",
        "medium": "⚠️",
        "high": "🔶",
        "critical": "🚨"
    }
    return emojis.get(level, "⚪")


def get_action_plan(warnings):
    """Generate action plan based on warning level."""
    
    actions = []
    
    if warnings.overall_level == "critical":
        actions.extend([
            "🚨 **IMMEDIATE**: Schedule emergency board meeting to discuss financial situation",
            "📞 Contact legal and financial advisors to assess restructuring options",
            "💰 Secure additional liquidity sources or credit facilities",
            "📊 Prepare detailed cash flow projections for next 12 months",
            "🔍 Conduct comprehensive asset review for potential divestitures",
            "📢 Prepare stakeholder communication plan (investors, creditors, employees)"
        ])
    
    elif warnings.overall_level == "high":
        actions.extend([
            "⚡ Schedule management meeting within 48 hours to address concerns",
            "📊 Request detailed variance analysis from finance team",
            "🔍 Conduct focused review of problematic areas",
            "💼 Consider engaging external consultants for specific issues",
            "📈 Develop action plan with concrete milestones and accountability",
            "👥 Increase reporting frequency to board and key stakeholders"
        ])
    
    elif warnings.overall_level == "medium":
        actions.extend([
            "📅 Schedule follow-up review in 2-4 weeks",
            "📊 Request additional analysis on flagged metrics",
            "💬 Discuss concerns in next regular management meeting",
            "🎯 Set specific targets for improvement",
            "📈 Monitor trends closely over next quarter"
        ])
    
    else:
        actions.extend([
            "✅ Continue standard monitoring procedures",
            "📊 Maintain regular reporting cadence",
            "🔍 Stay alert for emerging risk factors",
            "📈 Focus on sustaining positive trends"
        ])
    
    # Add signal-specific actions
    if any(s.signal_name == 'Liquidity Crisis' for s in warnings.triggered_signals):
        actions.append("💰 Priority: Address liquidity issues through working capital optimization or financing")
    
    if any(s.signal_name == 'Covenant Breach' for s in warnings.triggered_signals):
        actions.append("📄 Priority: Engage with lenders immediately to negotiate covenant waivers")
    
    if any(s.signal_name == 'Audit Issues' for s in warnings.triggered_signals):
        actions.append("🔍 Priority: Work with auditors to resolve qualification issues")
    
    return actions
