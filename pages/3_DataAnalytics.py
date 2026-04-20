import streamlit as st
from site_manager import render_project_list

st.title("📊 Data Analytics Portfolio")
st.write("Data Analytics and Advanced Data Analytics and Data Science Projects")

# Just call the shared function with the specific filter
render_project_list("DataAnalytics")