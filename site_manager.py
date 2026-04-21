import streamlit as st

# --- DATA (Kept here for simplicity, but you can move to projects_db.py) ---
projects = [
    {"title": "MediStream-AI-Ready-Medical-Imaging-Pipeline", "category": "BioMedTech", "url": "https://medistream-ai-ready-medical-imaging-pipeline.streamlit.app/", "tech": ["Python", "pydicom", "pandas"], "desc": "Automated extraction of lab results into a HIPAA-compliant Postgres warehouse."},
    {"title": "HL7 Message Parser", "category": "BioMedTech", "url": "https://url2.com", "tech": ["Python", "FastAPI"], "desc": "Real-time parsing of HL7v2 messages for clinical decision support."},
    
    {"title": "Real-time Ledger Sync", "category": "FinTech", "url": "https://url3.com", "tech": ["Kafka", "Go", "Postgres"], "desc": "Distributed system for synchronizing multi-currency ledgers with 99.99% uptime."},
    {"title": "Fraud Detection Engine", "category": "FinTech", "url": "https://url4.com", "tech": ["Spark", "Python", "Scikit-Learn"], "desc": "Streaming analytics pipeline to identify suspicious transaction patterns."},

    {"title": "Supply Chain Optimizer", "category": "DataAnalytics", "url": "https://url5.com", "tech": ["Snowflake", "dbt", "Airflow"], "desc": "End-to-end ELT pipeline optimizing warehouse inventory levels."},
    {"title": "Recruiter Dashboard Analytics", "category": "DataAnalytics", "url": "https://rad-kalyan-rachapudi-recruiter.streamlit.app/", "tech": ["Python", "Pandas", "Plotly"], "desc": "Recruiter Analytics Dashboard for visualizing hiring metrics."},
]

def render_project_list(category_filter):
    """The single source of truth for rendering project cards"""
    filtered = [p for p in projects if p['category'] == category_filter]
    
    for p in filtered:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(p['title'])
                st.write(p['desc'])
                st.markdown(" ".join([f"`{t}`" for t in p['tech']]))
            with col2:
                st.write("##") # Vertical spacer
                st.link_button("View Code 🔗", p['url'], use_container_width=True)
