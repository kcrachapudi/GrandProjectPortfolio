import streamlit as st

# Page Config
st.set_page_config(page_title="DE Portfolio | Your Name", layout="wide")

# --- SIDEBAR (Contact & Resume) ---
with st.sidebar:
    st.title("Kalyan Rachapudi")
    st.write("Masters in Computer Science | Bacherlors in Science ")
    st.divider()
    st.write("📧 [Email](mailto:kcrachapudi@gmail.com)")
# --- MAIN HEADER ---
st.title("Project Portfolio")
st.write("Software, Data Dngineering and Data Analytics Projects across Domains.")

# Define the pages and point them to the files in your pages folder
pg = st.navigation([
    st.Page("streamlit_app.py", title="Portfolio", icon="🏠"),
    st.Page("home.py", title="Home", icon="🏠", default=True),
    st.Page("pages/1_BioMedTech.py", title="BioMedTech", icon="🧬"),
    st.Page("pages/2_FinTech.py", title="FinTech", icon="💰"),
    st.Page("pages/3_DataAnalytics.py", title="Data Analytics", icon="📊")
])

# --- DATA (Kept here for simplicity, but you can move to projects_db.py) ---
projects = [
    {"title": "Cerner PathNet ETL Pipeline", "category": "BioMedTech", "url": "https://url1.com", "tech": ["CCL", "Python", "Oracle"], "desc": "Automated extraction of lab results into a HIPAA-compliant Postgres warehouse."},
    {"title": "HL7 Message Parser", "category": "BioMedTech", "url": "https://url2.com", "tech": ["Python", "FastAPI"], "desc": "Real-time parsing of HL7v2 messages for clinical decision support."},
    
    {"title": "Real-time Ledger Sync", "category": "FinTech", "url": "https://url3.com", "tech": ["Kafka", "Go", "Postgres"], "desc": "Distributed system for synchronizing multi-currency ledgers with 99.99% uptime."},
    {"title": "Fraud Detection Engine", "category": "FinTech", "url": "https://url4.com", "tech": ["Spark", "Python", "Scikit-Learn"], "desc": "Streaming analytics pipeline to identify suspicious transaction patterns."},

    {"title": "Supply Chain Optimizer", "category": "Data Analytics", "url": "https://url5.com", "tech": ["Snowflake", "dbt", "Airflow"], "desc": "End-to-end ELT pipeline optimizing warehouse inventory levels."},
    {"title": "Recruiter Dashboard Analytics", "category": "Data Analytics", "url": "https://rad-kalyan-rachapudi-recruiter.streamlit.app/", "tech": ["Python", "Pandas", "Plotly"], "desc": "Recruiter Analytics Dashboard for visualizing hiring metrics."},
]

# --- TABBED INTERFACE ---
tab1, tab2, tab3 = st.tabs(["🧬 BioMedTech", "💰 FinTech", "📊 Data Analytics"])

def render_category(category_name):
    filtered = [p for p in projects if p['category'] == category_name]
    if not filtered:
        st.write("_Projects coming soon..._")
    for p in filtered:
        # Use expander for a clean "List" feel
        with st.expander(p['title'], expanded=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(p['desc'])
                # Tech tags as inline code
                st.markdown(" ".join([f"`{t}`" for t in p['tech']]))
            with col2:
                st.link_button("Open Project 🔗", p['url'], use_container_width=True)

with tab1:
    render_category("BioMedTech")

with tab2:
    render_category("FinTech")

with tab3:
    render_category("Data Analytics")
