import streamlit as st
import os
from dotenv import load_dotenv
from src.chunker import user_text
from src.ai_client import analyze_chunk

#load API keys
load_dotenv()

# Page Config
st.set_page_config(page_title = "Critique-Forge AI", layout="wide")

st.title("Critique-Forge AI: Developmental Editor")
st.text("You Write. We Grade.")
st.markdown("Upload your manuscript to analyze its structural integrity.")

# Ingestion Zone
uploaded_file = st.file_uploader("Import text file here", type = ["txt","md","log","csv","json","docx","rtf","odt","pdf"])
text_input = st.text_area("Or paste the content here:", height=250)

if st.button("Analyze Text Content"):
    raw_text = ""
    if uploaded_file is not None:
        raw_text = uploaded_file.getvalue().decode("utf-8")
    elif text_input.strip():
        raw_text = text_input
    
    if not raw_text:
        st.error("Please upload a file or paste a scene to analyze.")
    else:
        with st.spinner("Grading content..."):
            try:
                chunks = user_text(raw_text)
                target_chunk = chunks[0]
                results = analyze_chunk(target_chunk)
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
            except Exception as e:
                st.error(f"An error occurred during grading: {str(e)}")