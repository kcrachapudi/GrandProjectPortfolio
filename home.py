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


