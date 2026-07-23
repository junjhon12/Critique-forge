import streamlit as st
from dotenv import load_dotenv

from src.ai_client import GENRE_PRESETS
from src.structure import STRUCTURE_TEMPLATES, PLATFORM_WORD_COUNT_NORMS
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
platform_min_words: int = 0
platform_max_words: int = 0
manuscript_format: str = "Web Novel"
selected_platform: str = "None"

if analysis_mode == "Full Manuscript":
    manuscript_format = st.sidebar.radio(
        "Manuscript format:",
        ["Web Novel", "Screenplay"],
        help="Web Novel unlocks chapter-ending cliffhanger scoring, platform pacing targets, "
             "and a release-readiness checklist. Screenplay skips those serialized-fiction checks.",
    )

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

    if manuscript_format == "Web Novel":
        selected_platform = st.sidebar.selectbox(
            "Platform word-count target (optional):", list(PLATFORM_WORD_COUNT_NORMS.keys())
        )
        if selected_platform == "Custom":
            platform_min_words = st.sidebar.number_input("Min words per chapter", min_value=0, value=1500, step=100)
            platform_max_words = st.sidebar.number_input("Max words per chapter", min_value=0, value=3000, step=100)
        elif selected_platform != "None":
            platform_min_words, platform_max_words = PLATFORM_WORD_COUNT_NORMS[selected_platform]
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
        platform_min_words, platform_max_words, manuscript_format, selected_platform,
    )
