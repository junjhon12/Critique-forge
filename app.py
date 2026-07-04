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
uploaded_file = st.file_uploader("Import text file here", type = ["txt","md","log","csv","json"])
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
                
                # Fetch the dynamic results from the AI
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Agency & Conflict")
                    
                    # --- Dynamic Agency Pillar ---
                    agency = results.get("agency", {})
                    st.write("**Character Agency**")
                    st.progress(agency.get("score", 0))
                    st.info(agency.get("analysis", "No analysis provided."))
                    st.success(f"**Actionable Tip:** {agency.get('actionable_advice', '')}")

                    st.write("---")
                    
                    # --- Dynamic Conflict Pillar ---
                    conflict = results.get("conflict_and_stakes", {})
                    st.write("**Conflict & Stakes**")
                    st.progress(conflict.get("score", 0))
                    st.warning(conflict.get("analysis", "No analysis provided."))
                    st.success(f"**Actionable Tip:** {conflict.get('actionable_advice', '')}")
                    
                with col2:
                    st.subheader("Structure & Arcs")
                    
                    # --- Dynamic Arcs Pillar ---
                    arcs = results.get("compelling_arcs", {})
                    st.write("**Compelling Arcs**")
                    st.progress(arcs.get("score", 0))
                    st.info(arcs.get("analysis", "No analysis provided."))
                    st.success(f"**Actionable Tip:** {arcs.get('actionable_advice', '')}")
                    
                    st.write("---")
                    
                    # --- Dynamic Structure Pillar ---
                    structure = results.get("tight_scene_structure", {})
                    st.write("**Tight Scene Structure**")
                    st.progress(structure.get("score", 0))
                    st.info(structure.get("analysis", "No analysis provided."))
                    st.success(f"**Actionable Tip:** {structure.get('actionable_advice', '')}")
                    
            except Exception as e:
                st.error(f"An error occurred during grading: {str(e)}")