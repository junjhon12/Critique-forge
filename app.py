import streamlit as st
import os
from dotenv import load_dotenv

#load API keys
load_dotenv()

# Page Config
st.set_page_config(page_title = "Critique-Forge AI", layout="wide")

st.title("Critique-Forge AI: Developmental Editor")
st.markdown("Upload your manuscript to analyze its structural integrity.")

# Ingestion Zone
uploaded_file = st.file_uploader("Import text file here", type = ["txt","md","log","csv","json","docx","rtf","odt","pdf"])
text_input = st.text_area("Or paste the content here:", height=250)

if st.button("Analyze Text Content"):
    with st.spinner("Grading content..."):
        # TODO: Route to chunker and LLM API here
        st.success("Grading Complete!")
        st.header("Content Grade")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Agency & Conflict")
            st.write("Character Agency")
            st.progress(85)
            st.info("The protagonist actively chooses to confront the antagonist.")
            
            st.write("Conflict & Stakes")
            st.progress(60)
            st.warning("Physical conflict is clear; emotional stakes are undefined.")
            
        with col2:
            st.subheader("Structure & Arcs")
            st.write("Compelling Arcs")
            st.progress(75)
            st.info("Clear shift in perspective post-inciting incident.")
            
            st.write("Tight Scene Structure")
            st.progress(90)
            st.success("Excellent pacing with no unnecessary exposition.")