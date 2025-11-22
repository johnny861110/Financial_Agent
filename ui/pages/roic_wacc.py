"""ROIC vs WACC Analysis page."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from app.services import ROICWACCService


def show():
    """Display ROIC vs WACC value creation analysis page."""
    
    st.title("💰 ROIC vs WACC Analysis")
    st.markdown("Evaluate value creation through return on invested capital vs cost of capital.")
    
    st.markdown("---")
    
    # Input form
    with st.form("roic_wacc_form"):
        st.subheader("📝 Financial Inputs")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Operating Performance**")
            nopat = st.number_input("NOPAT (M)", value=150.0, step=10.0, help="Net Operating Profit After Tax")
            invested_capital = st.number_input("Invested Capital (M)", value=1000.0, step=50.0, help="Total invested capital")
            
            st.markdown("**Capital Structure**")
            market_cap = st.number_input("Market Cap (M)", value=2000.0, step=100.0)
            total_debt = st.number_input("Total Debt (M)", value=500.0, step=50.0)
            
            st.markdown("**Tax Rate**")
            tax_rate = st.slider("Corporate Tax Rate", min_value=0.0, max_value=0.5, value=0.21, step=0.01, format="%.2f")
        
        with col2:
            st.markdown("**Cost of Equity Assumptions**")
            risk_free_rate = st.slider("Risk-free Rate", min_value=0.0, max_value=0.10, value=0.04, step=0.005, format="%.3f", help="10Y Treasury yield")
            market_risk_premium = st.slider("Market Risk Premium", min_value=0.0, max_value=0.15, value=0.07, step=0.005, format="%.3f")
            beta = st.number_input("Beta", min_value=0.0, max_value=3.0, value=1.2, step=0.1, help="Stock beta")
            
            st.markdown("**Cost of Debt**")
            cost_of_debt = st.slider("Cost of Debt (Pre-tax)", min_value=0.0, max_value=0.15, value=0.05, step=0.005, format="%.3f", help="Average interest rate on debt")
        
        submitted = st.form_submit_button("🧮 Calculate Analysis", type="primary")
    
    if submitted:
        with st.spinner("Calculating ROIC vs WACC analysis..."):
            from app.models import ROICWACCAnalysis
            
            # Calculate ROIC
            roic = nopat / invested_capital if invested_capital != 0 else 0
            
            # Calculate Cost of Equity (CAPM)
            cost_of_equity = risk_free_rate + beta * market_risk_premium
            
            # Calculate After-tax Cost of Debt
            after_tax_cost_of_debt = cost_of_debt * (1 - tax_rate)
            
            # Calculate WACC
            total_capital = market_cap + total_debt
            equity_weight = market_cap / total_capital if total_capital != 0 else 0
            debt_weight = total_debt / total_capital if total_capital != 0 else 0
            
            wacc = (equity_weight * cost_of_equity) + (debt_weight * after_tax_cost_of_debt)
            
            # Create analysis object
            analysis = ROICWACCAnalysis(
                nopat=nopat,
                invested_capital=invested_capital,
                roic=roic,
                cost_of_equity=cost_of_equity,
                cost_of_debt=after_tax_cost_of_debt,
                wacc=wacc,
                commentary=f"ROIC of {roic*100:.2f}% {'exceeds' if roic > wacc else 'falls short of'} WACC of {wacc*100:.2f}%, resulting in {'value creation' if roic > wacc else 'value destruction'}.",
                assumptions={
                    "market_cap": market_cap,
                    "total_debt": total_debt,
                    "equity_weight": equity_weight,
                    "debt_weight": debt_weight,
                    "beta": beta,
                    "risk_free_rate": risk_free_rate,
                    "market_risk_premium": market_risk_premium,
                    "tax_rate": tax_rate,
                    "cost_of_debt": cost_of_debt
                }
            )
            
            display_roic_wacc_analysis(analysis)


def display_roic_wacc_analysis(analysis):
    """Display ROIC vs WACC analysis results."""
    
    st.markdown("---")
    
    # Key metrics
    st.subheader("🎯 Key Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "ROIC",
            f"{analysis.roic * 100:.2f}%",
            help="Return on Invested Capital"
        )
    
    with col2:
        st.metric(
            "WACC",
            f"{analysis.wacc * 100:.2f}%",
            help="Weighted Average Cost of Capital"
        )
    
    with col3:
        delta_value = analysis.value_creation_gap * 100
        delta_color = "normal" if delta_value > 0 else "inverse"
        st.metric(
            "Value Creation Gap",
            f"{delta_value:.2f}%",
            delta=f"{delta_value:.2f}%",
            help="ROIC - WACC"
        )
    
    # Value creation assessment
    assessment = get_value_creation_assessment(analysis.value_creation_gap)
    if analysis.value_creation_gap > 0.05:
        st.success(f"✅ {assessment}")
    elif analysis.value_creation_gap > 0:
        st.info(f"ℹ️ {assessment}")
    else:
        st.error(f"⚠️ {assessment}")
    
    # ROIC vs WACC comparison chart
    st.markdown("---")
    st.subheader("📊 ROIC vs WACC Comparison")
    
    fig = go.Figure()
    
    # Bar chart
    fig.add_trace(go.Bar(
        x=['ROIC', 'WACC', 'Gap'],
        y=[analysis.roic * 100, analysis.wacc * 100, analysis.value_creation_gap * 100],
        marker_color=['green' if analysis.roic > analysis.wacc else 'red', 
                      'blue', 
                      'green' if analysis.value_creation_gap > 0 else 'red'],
        text=[f"{analysis.roic * 100:.2f}%", f"{analysis.wacc * 100:.2f}%", 
              f"{analysis.value_creation_gap * 100:.2f}%"],
        textposition='outside'
    ))
    
    fig.update_layout(
        title="Return vs Cost of Capital",
        yaxis_title="Percentage (%)",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # WACC breakdown
    st.markdown("---")
    st.subheader("🔍 WACC Components")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Cost of Equity",
            f"{analysis.cost_of_equity * 100:.2f}%",
            help="Required return on equity"
        )
    
    with col2:
        st.metric(
            "After-tax Cost of Debt",
            f"{analysis.cost_of_debt * 100:.2f}%",
            help="Cost of debt after tax shield"
        )
    
    # Capital structure weights from input
    equity_weight = analysis.assumptions.get('equity_weight', 0.7)
    debt_weight = analysis.assumptions.get('debt_weight', 0.3)
    
    # Pie chart for capital structure
    fig = go.Figure(data=[go.Pie(
        labels=['Equity', 'Debt'],
        values=[equity_weight * 100, debt_weight * 100],
        marker_colors=['lightblue', 'lightcoral'],
        hole=0.4,
        textinfo='label+percent',
        textposition='outside'
    )])
    
    fig.update_layout(
        title="Capital Structure Weights",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed calculation breakdown
    st.markdown("---")
    st.subheader("📋 Calculation Breakdown")
    
    calc_data = [
        {"Component": "NOPAT", "Value": f"${analysis.nopat:.2f}M"},
        {"Component": "Invested Capital", "Value": f"${analysis.invested_capital:.2f}M"},
        {"Component": "ROIC", "Value": f"{analysis.roic * 100:.2f}%"},
        {"Component": "", "Value": ""},
        {"Component": "Risk-free Rate", "Value": f"{analysis.assumptions.get('risk_free_rate', 0) * 100:.2f}%"},
        {"Component": "Beta", "Value": f"{analysis.assumptions.get('beta', 0):.2f}"},
        {"Component": "Market Risk Premium", "Value": f"{analysis.assumptions.get('market_risk_premium', 0) * 100:.2f}%"},
        {"Component": "Cost of Equity", "Value": f"{analysis.cost_of_equity * 100:.2f}%"},
        {"Component": "", "Value": ""},
        {"Component": "Cost of Debt (Pre-tax)", "Value": f"{analysis.assumptions.get('cost_of_debt_pretax', 0) * 100:.2f}%"},
        {"Component": "Tax Rate", "Value": f"{analysis.assumptions.get('tax_rate', 0) * 100:.2f}%"},
        {"Component": "After-tax Cost of Debt", "Value": f"{analysis.cost_of_debt * 100:.2f}%"},
        {"Component": "", "Value": ""},
        {"Component": "Equity Weight", "Value": f"{equity_weight * 100:.2f}%"},
        {"Component": "Debt Weight", "Value": f"{debt_weight * 100:.2f}%"},
        {"Component": "WACC", "Value": f"{analysis.wacc * 100:.2f}%"},
    ]
    
    calc_df = pd.DataFrame(calc_data)
    st.dataframe(calc_df, use_container_width=True, hide_index=True)
    
    # Commentary
    st.markdown("---")
    st.subheader("💬 Analysis Commentary")
    st.write(analysis.commentary)
    
    # Investment implications
    st.markdown("---")
    st.subheader("💡 Investment Implications")
    
    implications = get_investment_implications(analysis)
    for implication in implications:
        st.markdown(f"- {implication}")
    
    # Sensitivity analysis info
    st.markdown("---")
    st.subheader("🔬 Sensitivity Considerations")
    
    st.info("""
    **Key Sensitivities to Monitor:**
    - ROIC is sensitive to NOPAT margins and asset turnover
    - WACC changes with interest rates, equity risk premium, and capital structure
    - Beta fluctuates with market conditions and company-specific factors
    - Tax rate changes impact after-tax cost of debt
    """)


def get_value_creation_assessment(gap):
    """Get assessment based on value creation gap."""
    if gap > 0.10:
        return "Exceptional value creation - ROIC significantly exceeds WACC"
    elif gap > 0.05:
        return "Strong value creation - Company generating returns above cost of capital"
    elif gap > 0:
        return "Modest value creation - Returns marginally exceed cost of capital"
    elif gap > -0.05:
        return "Value neutral - Returns approximately equal cost of capital"
    else:
        return "Value destruction - Returns below cost of capital"


def get_investment_implications(analysis):
    """Generate investment implications based on analysis."""
    implications = []
    
    gap = analysis.value_creation_gap
    
    if gap > 0.10:
        implications.append("✅ **Strong Buy Signal** - Substantial value creation indicates competitive advantages")
        implications.append("📈 Company has pricing power or operational excellence to generate superior returns")
        implications.append("🎯 Consider increasing position size if valuation is reasonable")
    elif gap > 0.05:
        implications.append("✅ **Positive** - Company creates shareholder value consistently")
        implications.append("📊 Monitor sustainability of ROIC and potential for margin expansion")
    elif gap > 0:
        implications.append("⚠️ **Marginal** - Limited value creation suggests competitive pressures")
        implications.append("🔍 Investigate potential for ROIC improvement or WACC reduction")
    else:
        implications.append("🔴 **Concern** - Value destruction indicates fundamental issues")
        implications.append("📉 Company may be overinvesting in low-return projects")
        implications.append("⚡ Consider exit or significant position reduction")
    
    # Cost of equity considerations
    if analysis.cost_of_equity > 0.15:
        implications.append("⚠️ High cost of equity suggests elevated risk perception")
    
    # Leverage considerations
    total_cap = analysis.details.get('market_cap', 0) + analysis.details.get('total_debt', 0)
    debt_ratio = analysis.details.get('total_debt', 0) / total_cap if total_cap > 0 else 0
    
    if debt_ratio > 0.5:
        implications.append("⚠️ High leverage increases financial risk and WACC")
    elif debt_ratio < 0.2:
        implications.append("💡 Conservative capital structure - potential for optimization")
    
    return implications
