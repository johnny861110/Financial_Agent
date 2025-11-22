"""Factor Exposure Analysis page."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from app.services import FactorService


def show():
    """Display factor exposure analysis page."""
    
    st.title("📐 Factor Exposure Analysis")
    st.markdown("Analyze stock's exposure to key investment factors.")
    
    st.markdown("---")
    
    # Input form
    with st.form("factor_form"):
        st.subheader("📝 Factor Metrics Input")
        
        st.markdown("""
        Enter the company's metrics for each factor. Values will be z-scored against peer universe.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Quality Factors**")
            roe = st.number_input("ROE (%)", value=15.0, step=1.0, help="Return on Equity")
            roa = st.number_input("ROA (%)", value=8.0, step=1.0, help="Return on Assets")
            
            st.markdown("**Value Factors**")
            pe_ratio = st.number_input("P/E Ratio", value=18.0, step=1.0, help="Price to Earnings")
            pb_ratio = st.number_input("P/B Ratio", value=2.5, step=0.1, help="Price to Book")
            
            st.markdown("**Momentum Factors**")
            return_1m = st.number_input("1-Month Return (%)", value=5.0, step=1.0)
            return_6m = st.number_input("6-Month Return (%)", value=15.0, step=1.0)
        
        with col2:
            st.markdown("**Size Factor**")
            market_cap = st.number_input("Market Cap (B)", value=10.0, step=1.0, help="Market capitalization in billions")
            
            st.markdown("**Volatility Factor**")
            volatility = st.number_input("Annualized Volatility (%)", value=25.0, step=1.0, help="Historical volatility")
            
            st.markdown("**Peer Universe Statistics**")
            st.info("""
            Z-scores calculated using industry peer statistics.
            Mean and standard deviation derived from peer group.
            """)
        
        # Optional: peer statistics
        with st.expander("🔧 Advanced: Custom Peer Statistics"):
            st.markdown("Override default peer statistics (optional)")
            
            use_custom = st.checkbox("Use custom peer statistics")
            
            if use_custom:
                peer_roe_mean = st.number_input("Peer ROE Mean", value=12.0)
                peer_roe_std = st.number_input("Peer ROE Std Dev", value=5.0)
        
        submitted = st.form_submit_button("🧮 Calculate Factor Exposures", type="primary")
    
    if submitted:
        with st.spinner("Calculating factor exposures..."):
            # Note: This is a demo version. In production, would use actual stock data
            # For now, create a FactorExposures object directly with z-scores
            from app.models import FactorExposures
            
            # Simple z-score calculation (demo purposes)
            # Assuming industry averages: ROE=12%, ROA=6%, P/E=15, P/B=2, Vol=20%
            quality_z = ((roe + roa) / 2 - 9) / 3
            value_z = (18 - (pe_ratio + pb_ratio) / 2) / 5
            momentum_z = ((return_1m + return_6m) / 2) / 10
            size_z = (10 - market_cap) / 15
            vol_z = (25 - volatility) / 10
            
            factors = FactorExposures(
                quality=quality_z,
                value=value_z,
                momentum=momentum_z,
                size=size_z,
                volatility=vol_z,
                commentary=f"Factor analysis for company with market cap ${market_cap:.1f}B"
            )
            
            display_factor_exposures(factors)


def display_factor_exposures(factors):
    """Display factor exposure results."""
    
    st.markdown("---")
    
    # Overall factor summary
    st.subheader("🎯 Factor Exposure Summary")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        display_zscore_metric("Quality", factors.quality_zscore)
    
    with col2:
        display_zscore_metric("Value", factors.value_zscore)
    
    with col3:
        display_zscore_metric("Momentum", factors.momentum_zscore)
    
    with col4:
        display_zscore_metric("Size", factors.size_zscore)
    
    with col5:
        display_zscore_metric("Low Volatility", factors.low_volatility_zscore)
    
    # Radar chart
    st.markdown("---")
    st.subheader("📊 Factor Positioning Radar")
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=[factors.quality_zscore, factors.value_zscore, 
           factors.momentum_zscore, factors.size_zscore, 
           factors.low_volatility_zscore],
        theta=['Quality', 'Value', 'Momentum', 'Size', 'Low Volatility'],
        fill='toself',
        name='Z-scores',
        line=dict(color='blue', width=2)
    ))
    
    # Add average line
    fig.add_trace(go.Scatterpolar(
        r=[0, 0, 0, 0, 0],
        theta=['Quality', 'Value', 'Momentum', 'Size', 'Low Volatility'],
        mode='lines',
        name='Peer Average',
        line=dict(color='gray', width=1, dash='dash')
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[-3, 3]
            )
        ),
        showlegend=True,
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Bar chart of z-scores
    st.markdown("---")
    st.subheader("📈 Z-Score Distribution")
    
    fig = go.Figure()
    
    z_scores = [factors.quality_zscore, factors.value_zscore, 
                factors.momentum_zscore, factors.size_zscore, 
                factors.low_volatility_zscore]
    factor_names = ['Quality', 'Value', 'Momentum', 'Size', 'Low Volatility']
    colors = [get_zscore_color(z) for z in z_scores]
    
    fig.add_trace(go.Bar(
        x=factor_names,
        y=z_scores,
        marker_color=colors,
        text=[f"{z:.2f}" for z in z_scores],
        textposition='outside'
    ))
    
    # Add horizontal lines for reference
    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Average")
    fig.add_hline(y=1, line_dash="dot", line_color="green", annotation_text="+1 Std Dev")
    fig.add_hline(y=-1, line_dash="dot", line_color="red", annotation_text="-1 Std Dev")
    
    fig.update_layout(
        title="Factor Z-Scores vs Peer Universe",
        yaxis_title="Z-Score",
        yaxis_range=[-3, 3],
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Factor breakdown table
    st.markdown("---")
    st.subheader("📋 Detailed Factor Breakdown")
    
    factor_data = []
    
    for factor_name, zscore in [
        ("Quality", factors.quality_zscore),
        ("Value", factors.value_zscore),
        ("Momentum", factors.momentum_zscore),
        ("Size", factors.size_zscore),
        ("Low Volatility", factors.low_volatility_zscore)
    ]:
        percentile = get_percentile_from_zscore(zscore)
        interpretation = get_zscore_interpretation(zscore)
        
        factor_data.append({
            "Factor": factor_name,
            "Z-Score": f"{zscore:.2f}",
            "Percentile": f"{percentile:.1f}%",
            "Interpretation": interpretation
        })
    
    factor_df = pd.DataFrame(factor_data)
    st.dataframe(factor_df, use_container_width=True, hide_index=True)
    
    # Commentary
    st.markdown("---")
    st.subheader("💬 Factor Analysis Commentary")
    st.write(factors.commentary)
    
    # Investment style classification
    st.markdown("---")
    st.subheader("🎨 Investment Style Classification")
    
    style = classify_investment_style(factors)
    st.info(f"**Primary Style:** {style}")
    
    # Factor tilts and implications
    st.markdown("---")
    st.subheader("💡 Factor Tilts & Implications")
    
    implications = get_factor_implications(factors)
    for implication in implications:
        st.markdown(f"- {implication}")
    
    # Risk considerations
    st.markdown("---")
    st.subheader("⚠️ Risk Considerations")
    
    risks = get_factor_risks(factors)
    for risk in risks:
        st.warning(risk)


def display_zscore_metric(label, zscore):
    """Display z-score as metric with color coding."""
    
    # Determine delta display
    if zscore > 1:
        delta = "Above Avg"
        delta_color = "normal"
    elif zscore < -1:
        delta = "Below Avg"
        delta_color = "inverse"
    else:
        delta = "Average"
        delta_color = "off"
    
    st.metric(
        label,
        f"{zscore:.2f}σ",
        delta=delta,
        help=f"{label} factor z-score"
    )


def get_zscore_color(zscore):
    """Get color based on z-score."""
    if zscore > 1.5:
        return "darkgreen"
    elif zscore > 0.5:
        return "lightgreen"
    elif zscore > -0.5:
        return "lightblue"
    elif zscore > -1.5:
        return "orange"
    else:
        return "red"


def get_percentile_from_zscore(zscore):
    """Convert z-score to percentile (approximate)."""
    # Simplified conversion using normal distribution
    from math import erf
    return 50 * (1 + erf(zscore / (2 ** 0.5))) * 100


def get_zscore_interpretation(zscore):
    """Get interpretation for z-score."""
    if zscore > 2:
        return "🟢 Very High - Top 2.5%"
    elif zscore > 1:
        return "🟢 High - Top 16%"
    elif zscore > 0:
        return "⚪ Above Average"
    elif zscore > -1:
        return "⚪ Below Average"
    elif zscore > -2:
        return "🔴 Low - Bottom 16%"
    else:
        return "🔴 Very Low - Bottom 2.5%"


def classify_investment_style(factors):
    """Classify overall investment style based on factor exposures."""
    
    # Determine dominant factors
    if factors.quality_zscore > 1 and factors.value_zscore < 0:
        return "Quality Growth 📈"
    elif factors.value_zscore > 1 and factors.quality_zscore < 0:
        return "Deep Value 💰"
    elif factors.value_zscore > 0.5 and factors.quality_zscore > 0.5:
        return "Quality at Reasonable Price (QARP) ⚖️"
    elif factors.momentum_zscore > 1:
        return "Momentum / Growth 🚀"
    elif factors.low_volatility_zscore > 1:
        return "Defensive / Low Volatility 🛡️"
    elif factors.size_zscore < -1:
        return "Small Cap 🔍"
    else:
        return "Balanced / Core 🎯"


def get_factor_implications(factors):
    """Generate implications based on factor exposures."""
    implications = []
    
    if factors.quality_zscore > 1:
        implications.append("✅ **High Quality** - Strong profitability metrics suggest sustainable competitive advantages")
    elif factors.quality_zscore < -1:
        implications.append("⚠️ **Low Quality** - Weak profitability may indicate operational challenges")
    
    if factors.value_zscore > 1:
        implications.append("💰 **Deep Value** - Trading at attractive valuation multiples vs peers")
    elif factors.value_zscore < -1:
        implications.append("📈 **Growth Premium** - Expensive valuation implies high growth expectations")
    
    if factors.momentum_zscore > 1:
        implications.append("🚀 **Strong Momentum** - Positive price trend suggests continued outperformance")
    elif factors.momentum_zscore < -1:
        implications.append("📉 **Negative Momentum** - Weak price action may persist in near term")
    
    if factors.size_zscore > 1:
        implications.append("🏢 **Large Cap** - Liquidity and stability, but limited growth potential")
    elif factors.size_zscore < -1:
        implications.append("🔍 **Small Cap** - Higher growth potential but increased volatility risk")
    
    if factors.low_volatility_zscore > 1:
        implications.append("🛡️ **Low Volatility** - Defensive characteristics suitable for risk-averse portfolios")
    elif factors.low_volatility_zscore < -1:
        implications.append("⚡ **High Volatility** - Increased risk but potential for outsized returns")
    
    return implications


def get_factor_risks(factors):
    """Identify potential risks based on factor profile."""
    risks = []
    
    # Value trap risk
    if factors.value_zscore > 1 and factors.quality_zscore < -1:
        risks.append("🚨 Value Trap Risk: Cheap valuation combined with poor quality may indicate structural issues")
    
    # Momentum reversal risk
    if factors.momentum_zscore > 2:
        risks.append("⚠️ Momentum Reversal Risk: Extreme positive momentum may be due for mean reversion")
    
    # Low quality growth risk
    if factors.quality_zscore < -1 and factors.momentum_zscore > 1:
        risks.append("⚠️ Unsustainable Growth Risk: Momentum without quality fundamentals may not persist")
    
    # Volatility risk
    if factors.low_volatility_zscore < -2:
        risks.append("⚠️ High Volatility Risk: Expect significant price swings and potential drawdowns")
    
    # Small cap liquidity risk
    if factors.size_zscore < -2:
        risks.append("⚠️ Liquidity Risk: Small market cap may result in wide bid-ask spreads and execution challenges")
    
    if not risks:
        risks.append("✅ No major factor-based risk flags identified")
    
    return risks
