"""Management Quality Score page."""

import streamlit as st
import plotly.graph_objects as go
from app.services import ManagementService


def show():
    """Display management quality scoring page."""
    
    st.title("⭐ Management Quality Score")
    st.markdown("Evaluate management quality based on governance, tenure, and alignment.")
    
    st.markdown("---")
    
    # Input form
    with st.form("management_form"):
        st.subheader("📝 Management Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Executive Tenure**")
            ceo_tenure = st.number_input("CEO Tenure (years)", min_value=0.0, max_value=50.0, value=5.0, step=0.5)
            cfo_tenure = st.number_input("CFO Tenure (years)", min_value=0.0, max_value=50.0, value=4.0, step=0.5)
            
            st.markdown("**Board Composition**")
            board_independence = st.slider("Board Independence Ratio", min_value=0.0, max_value=1.0, value=0.4, step=0.05)
            independent_directors = st.number_input("Independent Directors", min_value=0, max_value=20, value=3)
            total_directors = st.number_input("Total Directors", min_value=1, max_value=30, value=9)
        
        with col2:
            st.markdown("**Insider Trading**")
            insider_buys = st.number_input("Insider Buy Transactions", min_value=0, max_value=100, value=3)
            insider_sells = st.number_input("Insider Sell Transactions", min_value=0, max_value=100, value=1)
            
            st.markdown("**Governance Concerns**")
            governance_incidents = st.number_input("Governance Incidents", min_value=0, max_value=20, value=0)
            audit_issues = st.number_input("Audit Issues", min_value=0, max_value=20, value=0)
            related_party = st.number_input("Related Party Transaction Concerns", min_value=0, max_value=20, value=0)
        
        family_controlled = st.checkbox("Family Controlled Company")
        
        submitted = st.form_submit_button("🧮 Calculate Score", type="primary")
    
    if submitted:
        with st.spinner("Calculating management quality score..."):
            service = ManagementService()
            score = service.calculate_score(
                ceo_tenure_years=ceo_tenure,
                cfo_tenure_years=cfo_tenure,
                board_independence_ratio=board_independence,
                independent_directors=independent_directors,
                total_directors=total_directors,
                family_controlled=family_controlled,
                insider_buys=insider_buys,
                insider_sells=insider_sells,
                governance_incidents=governance_incidents,
                audit_issues=audit_issues,
                related_party_transactions=related_party,
            )
            
            display_management_score(score)


def display_management_score(score):
    """Display management score results."""
    
    st.markdown("---")
    
    # Overall score
    st.subheader("🎯 Overall Management Quality Score")
    
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
                {'range': [0, 40], 'color': "lightgray"},
                {'range': [40, 60], 'color': "lightyellow"},
                {'range': [60, 80], 'color': "lightgreen"},
                {'range': [80, 100], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)
    
    # Interpretation
    interpretation = get_score_interpretation(score.total)
    st.info(f"**Interpretation:** {interpretation}")
    
    # Component scores
    st.markdown("---")
    st.subheader("📊 Component Scores")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Tenure Stability",
            f"{score.tenure_stability:.1f}",
            help="Executive tenure and stability"
        )
    
    with col2:
        st.metric(
            "Board Independence",
            f"{score.board_independence:.1f}",
            help="Board independence and governance"
        )
    
    with col3:
        st.metric(
            "Insider Alignment",
            f"{score.insider_alignment:.1f}",
            help="Insider trading behavior"
        )
    
    with col4:
        st.metric(
            "Governance",
            f"{score.governance_red_flags:.1f}",
            help="Absence of governance issues"
        )
    
    # Component radar chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=[score.tenure_stability, score.board_independence, 
           score.insider_alignment, score.governance_red_flags],
        theta=['Tenure Stability', 'Board Independence', 
               'Insider Alignment', 'Governance'],
        fill='toself',
        name='Scores'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=False,
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Commentary
    st.markdown("---")
    st.subheader("💬 Analysis Commentary")
    st.write(score.commentary)
    
    # Details
    if score.details:
        st.markdown("---")
        st.subheader("📋 Detailed Information")
        
        for key, value in score.details.items():
            st.text(f"{key.replace('_', ' ').title()}: {value}")
    
    # Recommendations
    st.markdown("---")
    st.subheader("💡 Recommendations")
    
    recommendations = get_recommendations(score)
    for rec in recommendations:
        st.markdown(f"- {rec}")


def get_score_color(score):
    """Get color based on score."""
    if score >= 80:
        return "darkgreen"
    elif score >= 60:
        return "green"
    elif score >= 40:
        return "orange"
    else:
        return "red"


def get_score_interpretation(score):
    """Get interpretation based on score."""
    if score >= 80:
        return "🟢 Excellent - Strong management team with robust governance"
    elif score >= 60:
        return "🟡 Good - Competent management with some areas for improvement"
    elif score >= 40:
        return "🟠 Fair - Management quality concerns warrant closer monitoring"
    else:
        return "🔴 Poor - Significant management and governance issues identified"


def get_recommendations(score):
    """Generate recommendations based on score components."""
    recs = []
    
    if score.tenure_stability < 50:
        recs.append("⚠️ Short executive tenure indicates potential instability. Monitor management changes closely.")
    
    if score.board_independence < 50:
        recs.append("⚠️ Low board independence raises governance concerns. Seek companies with stronger board oversight.")
    
    if score.insider_alignment < 40:
        recs.append("🔴 Negative insider trading pattern. Executives may lack confidence in company prospects.")
    
    if score.governance_red_flags < 70:
        recs.append("🔴 Governance issues detected. Conduct thorough due diligence before investing.")
    
    if not recs:
        recs.append("✅ Strong management quality across all dimensions. Continue monitoring for any changes.")
    
    return recs
