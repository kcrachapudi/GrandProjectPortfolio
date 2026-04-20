import streamlit as st

# 1. Page Config
st.set_page_config(page_title="DE Portfolio | Kalyan Rachapudi", layout="wide")

# 2. Navigation Definition
pg = st.navigation([
    st.Page("home.py", title="Home", icon="🏠", default=True), # Points to your root file
    st.Page("pages/1_BioMedTech.py", title="BioMedTech", icon="🧬"),
    st.Page("pages/2_FinTech.py", title="FinTech", icon="💰"),
    st.Page("pages/3_DataAnalytics.py", title="Data Analytics", icon="📊")
])

# 3. Global Sidebar
with st.sidebar:
    st.title("Kalyan Rachapudi")
    st.write("Masters in CS | Bachelors in Science")
    st.divider()
    st.write("📧 [Email](mailto:kcrachapudi@gmail.com)")

# 4. Run it
pg.run()
