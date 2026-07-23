import streamlit as st
from dotenv import load_dotenv

from src.ai_client import GENRE_PRESETS
from src.structure import STRUCTURE_TEMPLATES
from src.views import render_query_letter_mode, render_agent_read_mode, render_full_manuscript_mode

_ = load_dotenv()

# --- PAGE CONFIG & SIDEBAR ---
st.set_page_config(page_title="Critique-Forge AI", layout="wide")

_ = st.sidebar.title("⚙️ Editor Settings")
manuscript_name: str = st.sidebar.text_input("Manuscript name (for version history)", value="Untitled")
analysis_mode: str = st.sidebar.radio(
    "Analysis mode:",
    ["Full Manuscript", "Query Letter / Synopsis", "Read Like an Agent (First Page)"],
)

selected_persona: str = "Ruthless Critic"
custom_prompt: str = ""
selected_genre: str = "None / General"
selected_structure_template: str = "None / General"

if analysis_mode == "Full Manuscript":
    selected_persona = st.sidebar.radio(
        "Choose your editor's tone:",
        ["Ruthless Critic", "Encouraging Mentor", "Grammar & Prose Stickler", "Custom"]
    )

    if selected_persona == "Custom":
        custom_prompt = st.sidebar.text_area("Write your own persona prompt:", height=200)
        if not custom_prompt.strip():
            _ = st.sidebar.warning("Enter a custom persona prompt to use it during analysis.")

    selected_genre = st.sidebar.selectbox("Genre / format:", list(GENRE_PRESETS.keys()))
    selected_structure_template = st.sidebar.selectbox(
        "Structure template (optional):", list(STRUCTURE_TEMPLATES.keys())
    )
elif analysis_mode == "Read Like an Agent (First Page)":
    selected_genre = st.sidebar.selectbox("Genre / format:", list(GENRE_PRESETS.keys()))

# --- MAIN UI ---
_ = st.title("Critique-Forge AI: Developmental Editor")

if analysis_mode == "Query Letter / Synopsis":
    render_query_letter_mode()
elif analysis_mode == "Read Like an Agent (First Page)":
    render_agent_read_mode(manuscript_name, selected_genre)
else:
    render_full_manuscript_mode(
        manuscript_name, selected_persona, custom_prompt, selected_genre, selected_structure_template,
    )
