import streamlit as st

def header(title):
    st.markdown(f"""
    <div style="padding:1rem;border-radius:14px;
    background:linear-gradient(90deg,#4F46E5,#6366F1);
    color:white;margin-bottom:1rem">
        <h2>{title}</h2>
    </div>
    """, unsafe_allow_html=True)