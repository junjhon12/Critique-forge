import streamlit as st
import os
import PyPDF2
import docx
from dotenv import load_dotenv
from src.chunker import user_text
from src.ai_client import analyze_chunk

load_dotenv()

# --- HELPER FUNCTIONS ---
def extract_text_from_file(uploaded_file):
    """Safely extracts text based on file extension."""
    filename = uploaded_file.name.lower()
    if filename.endswith(".pdf"):
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    elif filename.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        # Fallback for plain text like .txt or .md
        return uploaded_file.getvalue().decode("utf-8")

def generate_markdown_report(avg_scores, all_results, pacing_data):
    """Generates a downloadable text report."""
    md = "# Critique-Forge Analysis Report\n\n## Final Average Scores\n"
    md += f"- **Agency:** {avg_scores['agency']} / 100\n"
    md += f"- **Conflict & Stakes:** {avg_scores['conflict_and_stakes']} / 100\n"
    md += f"- **Compelling Arcs:** {avg_scores['compelling_arcs']} / 100\n"
    md += f"- **Tight Scene Structure:** {avg_scores['tight_scene_structure']} / 100\n\n"
    md += "---\n## Detailed Chunk Breakdown\n\n"
    
    for i, result in enumerate(all_results):
        md += f"### Section {i+1}\n"
        for pillar in ["agency", "conflict_and_stakes", "compelling_arcs", "tight_scene_structure"]:
            data = result.get(pillar, {})
            md += f"**{pillar.replace('_', ' ').title()} ({data.get('score', 0)}/100):**\n"
            md += f"> *Analysis:* {data.get('analysis', '')}\n>\n"
            md += f"> *Actionable Tip:* {data.get('actionable_advice', '')}\n\n"
        md += "---\n"
    return md

# --- PAGE CONFIG & SIDEBAR ---
st.set_page_config(page_title="Critique-Forge AI", layout="wide")

st.sidebar.title("⚙️ Editor Settings")
selected_persona = st.sidebar.radio(
    "Choose your editor's tone:",
    ["Ruthless Critic", "Encouraging Mentor", "Grammar & Prose Stickler"]
)

# --- MAIN UI ---
st.title("Critique-Forge AI: Developmental Editor")
st.markdown("Upload your manuscript to analyze its structural integrity.")

# Accept pdf and docx alongside plain text
uploaded_file = st.file_uploader("Import document here", type=["txt", "md", "pdf", "docx"])
text_input = st.text_area("Or paste the content here:", height=200)

if st.button("Analyze Manuscript"):
    raw_text = ""
    if uploaded_file is not None:
        try:
            raw_text = extract_text_from_file(uploaded_file)
        except Exception as e:
            st.error(f"Error reading file: {e}")
    elif text_input.strip():
        raw_text = text_input
    
    if not raw_text:
        st.error("Please upload a file or paste text to analyze.")
    else:
        chunks = user_text(raw_text)
        
        # State trackers for the full manuscript
        all_results = []
        pacing_data = [] 
        avg_scores = {"agency": 0, "conflict_and_stakes": 0, "compelling_arcs": 0, "tight_scene_structure": 0}
        all_characters = {} # Tracks entities across chunks
        
        progress_bar = st.progress(0, text="Initializing Editor...")
        
        try:
            # Process the Entire Manuscript Loop
            for i, chunk in enumerate(chunks):
                progress_bar.progress((i) / len(chunks), text=f"Analyzing Section {i+1} of {len(chunks)}...")
                result = analyze_chunk(chunk, persona=selected_persona)
                all_results.append(result)
                
                # Store pacing data
                pacing_data.append(result.get("conflict_and_stakes", {}).get("score", 0))
                
                # Accumulate scores
                for pillar in avg_scores.keys():
                    avg_scores[pillar] += result.get(pillar, {}).get("score", 0)

                # --- UPDATE CHARACTER CODEX ---
                codex = result.get("character_codex", [])
                for char in codex:
                    name = char.get("name", "Unknown")
                    if name and name.lower() != "unknown":
                        if name in all_characters:
                            # Update existing character motivation, append traits if new
                            if char.get("physical_traits"):
                                all_characters[name]["physical_traits"] += f", {char.get('physical_traits')}"
                            all_characters[name]["current_motivation"] = char.get("current_motivation", "")
                        else:
                            # Add new character
                            all_characters[name] = char

            progress_bar.progress(1.0, text="Analysis Complete!")
            
            # --- RENDER SIDEBAR CODEX ---
            st.sidebar.markdown("---")
            st.sidebar.subheader("📖 Dynamic Character Codex")
            if all_characters:
                for name, details in all_characters.items():
                    with st.sidebar.expander(f"👤 {name.title()}"):
                        st.write(f"**Traits:** {details.get('physical_traits', 'None detected')}")
                        st.write(f"**Current Motivation:** {details.get('current_motivation', 'Unknown')}")
            else:
                st.sidebar.info("No distinct characters detected.")

            # Calculate final averages
            for pillar in avg_scores.keys():
                avg_scores[pillar] = int(avg_scores[pillar] / len(chunks))

            st.success("Grading Complete!")
            
            # --- TENSION LINE GRAPH ---
            if len(pacing_data) > 1:
                st.subheader("📈 Manuscript Tension Pacing (Conflict & Stakes)")
                st.line_chart(pacing_data)
                st.caption("A healthy story usually features rising tension (peaks) followed by brief moments of resolution (valleys). Flat lines indicate pacing issues.")

            st.header("Average Content Grades")
            col1, col2 = st.columns(2)
            
            final_chunk = all_results[-1] 

            with col1:
                st.subheader("Agency & Conflict")
                st.write("**Character Agency (Avg)**")
                st.progress(avg_scores["agency"])
                st.success(f"**Tip from Final Scene:** {final_chunk.get('agency', {}).get('actionable_advice', '')}")

                st.write("---")
                st.write("**Conflict & Stakes (Avg)**")
                st.progress(avg_scores["conflict_and_stakes"])
                st.warning(f"**Tip from Final Scene:** {final_chunk.get('conflict_and_stakes', {}).get('actionable_advice', '')}")
                
            with col2:
                st.subheader("Structure & Arcs")
                st.write("**Compelling Arcs (Avg)**")
                st.progress(avg_scores["compelling_arcs"])
                st.info(f"**Tip from Final Scene:** {final_chunk.get('compelling_arcs', {}).get('actionable_advice', '')}")
                
                st.write("---")
                st.write("**Tight Scene Structure (Avg)**")
                st.progress(avg_scores["tight_scene_structure"])
                st.success(f"**Tip from Final Scene:** {final_chunk.get('tight_scene_structure', {}).get('actionable_advice', '')}")
            
            # --- PROSE SNIPER SECTION ---
            st.write("---")
            st.subheader("🎯 The 'Show, Don't Tell' Prose Sniper")
            sniper = final_chunk.get("prose_sniper", {})
            
            if sniper and sniper.get("bad_quote"):
                st.error(f"**Target Acquired (Telling / Passive Voice):**\n> \"{sniper.get('bad_quote')}\"")
                st.success(f"**Sniper Rewrite (Showing / Active Voice):**\n> \"{sniper.get('rewritten_example')}\"")
            else:
                st.info("No major prose violations detected in this section. Clean writing!")

            # --- DOWNLOAD REPORT ---
            report_str = generate_markdown_report(avg_scores, all_results, pacing_data)
            st.download_button(
                label="📥 Download Full Offline Report",
                data=report_str,
                file_name="CritiqueForge_Report.md",
                mime="text/markdown"
            )
            
        except Exception as e:
            st.error(f"An error occurred during grading: {str(e)}")