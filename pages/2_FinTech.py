import streamlit as st
from site_manager import render_project_list

st.title("💰 FinTech Portfolio")
st.write("Specialized ETL pipelines and LIS integrations for financial environments.")

# Just call the shared function with the specific filter
render_project_list("FinTech")