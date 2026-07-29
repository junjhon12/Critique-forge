import streamlit as st
from dotenv import load_dotenv

from src.ai_client import GENRE_PRESETS
from src.structure import STRUCTURE_TEMPLATES, PLATFORM_WORD_COUNT_NORMS, BeatDefinition
from src.user_presets import load_user_presets, save_genre_preset, save_structure_template
from src.views import render_query_letter_mode, render_agent_read_mode, render_full_manuscript_mode, render_retention_sim_mode

_ = load_dotenv()


def _parse_beats(raw: str) -> list[BeatDefinition]:
    beats: list[BeatDefinition] = []
    for line in raw.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3 or not parts[0]:
            continue
        try:
            expected_pct = float(parts[1])
        except ValueError:
            continue
        beats.append({"name": parts[0], "expected_pct": expected_pct, "description": parts[2]})
    return beats


# --- PAGE CONFIG & SIDEBAR ---
st.set_page_config(page_title="Critique-Forge AI", layout="wide")

_ = st.sidebar.title("⚙️ Editor Settings")
manuscript_name: str = st.sidebar.text_input("Manuscript name (for version history)", value="Untitled")

_user_presets = load_user_presets()
all_genre_presets = {**GENRE_PRESETS, **_user_presets["genres"]}
all_structure_templates = {**STRUCTURE_TEMPLATES, **_user_presets["structure_templates"]}

with st.sidebar.expander("+ Add custom genre/format"):
    new_genre_name = st.text_input("Name", key="new_genre_name")
    new_genre_guidance = st.text_area(
        "Guidance for the AI critic (same style as built-in presets)",
        key="new_genre_guidance",
        help="E.g. 'GENRE FOCUS: This is ... Judge X heavily on Y.'",
    )
    if st.button("Save genre preset") and new_genre_name.strip():
        save_genre_preset(new_genre_name.strip(), new_genre_guidance.strip())
        st.rerun()

with st.sidebar.expander("+ Add custom structure template"):
    new_template_name = st.text_input("Name", key="new_template_name")
    beats_raw = st.text_area(
        "One beat per line: Name | expected % | description",
        key="new_template_beats",
        help="Example: Inciting Incident | 10 | The event that sets the story in motion.",
    )
    if st.button("Save structure template") and new_template_name.strip():
        save_structure_template(new_template_name.strip(), _parse_beats(beats_raw))
        st.rerun()

writing_for: str = st.sidebar.radio(
    "Writing for:",
    ["Web Novel / Serial", "Traditional Publishing"],
    help="Web Novel / Serial hides the query-letter and literary-agent simulation modes, which "
         "only apply to querying literary agents for traditional publication.",
)
_is_web_novel_track = writing_for == "Web Novel / Serial"

_mode_options = (
    ["Full Manuscript", "Chapter One Retention Simulator"]
    if _is_web_novel_track
    else ["Full Manuscript", "Query Letter / Synopsis", "Read Like an Agent (First Page)"]
)
analysis_mode: str = st.sidebar.radio("Analysis mode:", _mode_options)

selected_persona: str = "Ruthless Critic"
custom_prompt: str = ""
selected_genre: str = "None / General"
selected_structure_template: str = "None / General"
platform_min_words: int = 0
platform_max_words: int = 0
manuscript_format: str = "Web Novel"
selected_platform: str = "None"
li_names: list[str] = []

_web_novel_genres = [k for k in all_genre_presets if k.startswith("Web Novel") or k == "None / General"]

if analysis_mode == "Full Manuscript":
    if _is_web_novel_track:
        manuscript_format = "Web Novel"
    else:
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

    genre_options = _web_novel_genres if _is_web_novel_track else list(all_genre_presets.keys())
    selected_genre = st.sidebar.selectbox("Genre / format:", genre_options)
    selected_structure_template = st.sidebar.selectbox(
        "Structure template (optional):", list(all_structure_templates.keys())
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

        if selected_genre == "Web Novel: Harem / Reverse Harem":
            li_names_raw = st.sidebar.text_input(
                "Love interest names (comma-separated, optional):",
                help="Enables a screen-time balance check that flags love interests at risk of "
                     "feeling forgotten relative to the rest of the cast.",
            )
            li_names = [n.strip() for n in li_names_raw.split(",") if n.strip()]
elif analysis_mode == "Read Like an Agent (First Page)":
    selected_genre = st.sidebar.selectbox("Genre / format:", list(all_genre_presets.keys()))
elif analysis_mode == "Chapter One Retention Simulator":
    selected_genre = st.sidebar.selectbox("Genre / format:", _web_novel_genres)

# --- MAIN UI ---
_ = st.title("Critique-Forge AI: Developmental Editor")

if analysis_mode == "Query Letter / Synopsis":
    render_query_letter_mode()
elif analysis_mode == "Read Like an Agent (First Page)":
    render_agent_read_mode(manuscript_name, selected_genre)
elif analysis_mode == "Chapter One Retention Simulator":
    render_retention_sim_mode(manuscript_name, selected_genre)
else:
    render_full_manuscript_mode(
        manuscript_name, selected_persona, custom_prompt, selected_genre, selected_structure_template,
        platform_min_words, platform_max_words, manuscript_format, selected_platform, li_names,
    )
