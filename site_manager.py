import streamlit as st
import site_urls

projects = site_urls.projects # Expose the projects data for other modules

def render_project_list(category_filter, projects=projects):
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
                st.link_button("Visit 🔗", p['url'], use_container_width=True)
