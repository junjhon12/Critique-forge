import streamlit as st
import PyPDF2
import docx
from dotenv import load_dotenv
from typing import TypedDict, cast
from streamlit.runtime.uploaded_file_manager import UploadedFile
from src.chunker import user_text
from src.ai_client import analyze_chunk, CritiqueResult, CharacterData, PillarData

_ = load_dotenv()

PILLAR_KEYS: list[str] = ["agency", "conflict_and_stakes", "compelling_arcs", "tight_scene_structure"]


def _pillar_data(result: CritiqueResult, pillar: str) -> PillarData:
    """Look up a pillar's data by a runtime key without the result widening to Any."""
    return cast(PillarData, result.get(pillar, {}))


def _format_pillar_label(pillar: str) -> str:
    return pillar.replace("_", " ").title()


class SniperHit(TypedDict):
    section: int
    bad_quote: str
    rewritten_example: str


# --- HELPER FUNCTIONS ---
def extract_text_from_file(uploaded_file: UploadedFile) -> str:
    """Safely extracts text based on file extension."""
    filename: str = cast(str, uploaded_file.name).lower()
    if filename.endswith(".pdf"):
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            text += (extracted or "") + "\n"
        return text
    elif filename.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        # Fallback for plain text like .txt or .md
        return uploaded_file.getvalue().decode("utf-8")


def generate_markdown_report(
    avg_scores: dict[str, int],
    all_results: list[CritiqueResult],
    all_characters: dict[str, CharacterData] | None = None,
    prose_snipers: list[SniperHit] | None = None,
    section_scores: list[float] | None = None,
) -> str:
    """Generates a downloadable text report."""
    md = "# Critique-Forge Analysis Report\n\n"
    md += f"*Analyzed {len(all_results)} section(s).*\n\n"
    md += "## Final Average Scores\n"
    md += f"- **Agency:** {avg_scores['agency']} / 100\n"
    md += f"- **Conflict & Stakes:** {avg_scores['conflict_and_stakes']} / 100\n"
    md += f"- **Compelling Arcs:** {avg_scores['compelling_arcs']} / 100\n"
    md += f"- **Tight Scene Structure:** {avg_scores['tight_scene_structure']} / 100\n\n"

    # --- WEAKEST SECTION ---
    if section_scores:
        weakest_idx = section_scores.index(min(section_scores))
        md += f"**🔻 Weakest Section:** Section {weakest_idx + 1} (avg {section_scores[weakest_idx]:.0f}/100)\n\n"

    # --- CHARACTER CODEX ---
    if all_characters:
        md += "---\n## 📖 Character Codex\n\n"
        for name, details in all_characters.items():
            md += f"### {name.title()}\n"
            md += f"- **Traits:** {details.get('physical_traits', 'None detected')}\n"
            md += f"- **Current Motivation:** {details.get('current_motivation', 'Unknown')}\n\n"

    # --- PROSE SNIPER GALLERY ---
    if prose_snipers:
        md += "---\n## 🎯 Prose Sniper Gallery\n\n"
        for hit in prose_snipers:
            md += f"**Section {hit['section']}:**\n"
            md += f"- *Telling / Passive:* \"{hit.get('bad_quote', '')}\"\n"
            md += f"- *Showing / Active Rewrite:* \"{hit.get('rewritten_example', '')}\"\n\n"

    md += "---\n## Detailed Chunk Breakdown\n\n"

    for i, result in enumerate(all_results):
        md += f"### Section {i+1}\n"
        for pillar in PILLAR_KEYS:
            data = _pillar_data(result, pillar)
            md += f"**{_format_pillar_label(pillar)} ({data.get('score', 0)}/100):**\n"
            md += f"> *Analysis:* {data.get('analysis', '')}\n>\n"
            md += f"> *Actionable Tip:* {data.get('actionable_advice', '')}\n\n"
        md += "---\n"
    return md


# --- PAGE CONFIG & SIDEBAR ---
st.set_page_config(page_title="Critique-Forge AI", layout="wide")

_ = st.sidebar.title("⚙️ Editor Settings")
selected_persona: str = st.sidebar.radio(
    "Choose your editor's tone:",
    ["Ruthless Critic", "Encouraging Mentor", "Grammar & Prose Stickler", "Custom"]
)

custom_prompt: str = ""
if selected_persona == "Custom":
    custom_prompt = st.sidebar.text_area("Write your own persona prompt:", height=200)
    if not custom_prompt.strip():
        _ = st.sidebar.warning("Enter a custom persona prompt to use it during analysis.")

# --- MAIN UI ---
_ = st.title("Critique-Forge AI: Developmental Editor")
_ = st.markdown("Upload your manuscript to analyze its structural integrity.")

# Accept pdf and docx alongside plain text
uploaded_file: UploadedFile | None = st.file_uploader(
    "Import document here", type=["txt", "md", "pdf", "docx"]
)
text_input: str = st.text_area("Or paste the content here:", height=200)

if st.button("Analyze Manuscript"):
    raw_text: str = ""
    if uploaded_file is not None:
        try:
            raw_text = extract_text_from_file(uploaded_file)
        except Exception as e:
            _ = st.error(f"Error reading file: {e}")
    elif text_input.strip():
        raw_text = text_input

    if not raw_text:
        _ = st.error("Please upload a file or paste text to analyze.")
    else:
        chunks: list[str] = user_text(raw_text)

        # State trackers for the full manuscript
        all_results: list[CritiqueResult] = []
        pacing_data: dict[str, list[int]] = {
            "agency": [],
            "conflict_and_stakes": [],
            "compelling_arcs": [],
            "tight_scene_structure": [],
        }
        avg_scores: dict[str, int] = {
            "agency": 0,
            "conflict_and_stakes": 0,
            "compelling_arcs": 0,
            "tight_scene_structure": 0,
        }
        all_characters: dict[str, CharacterData] = {}  # Tracks entities across chunks
        prose_snipers: list[SniperHit] = []  # Tracks every flagged sentence across chunks
        section_scores: list[float] = []  # Tracks each section's overall average, to find the weakest

        progress_bar = st.progress(0, text="Initializing Editor...")

        try:
            # Process the Entire Manuscript Loop
            for i, chunk in enumerate(chunks):
                _ = progress_bar.progress(
                    (i) / len(chunks), text=f"Analyzing Section {i+1} of {len(chunks)}..."
                )
                result: CritiqueResult = analyze_chunk(
                    chunk,
                    persona=selected_persona,
                    custom_system_prompt=custom_prompt if selected_persona == "Custom" else None,
                )
                all_results.append(result)

                # Store pacing data for every pillar
                for pillar in pacing_data.keys():
                    pacing_data[pillar].append(_pillar_data(result, pillar).get("score", 0))

                # --- TRACK WEAKEST SECTION ---
                section_avg = sum(_pillar_data(result, p).get("score", 0) for p in PILLAR_KEYS) / 4
                section_scores.append(section_avg)

                # Accumulate scores
                for pillar in avg_scores.keys():
                    avg_scores[pillar] += _pillar_data(result, pillar).get("score", 0)

                # --- COLLECT PROSE SNIPER GALLERY ---
                sniper_hit = result.get("prose_sniper", {})  # type: ignore[assignment]
                if sniper_hit and sniper_hit.get("bad_quote"):
                    prose_snipers.append({
                        "section": i + 1,
                        "bad_quote": sniper_hit.get("bad_quote", ""),
                        "rewritten_example": sniper_hit.get("rewritten_example", "")
                    })

                # --- UPDATE CHARACTER CODEX ---
                codex: list[CharacterData] = result.get("character_codex", [])  # type: ignore[assignment]
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

            _ = progress_bar.progress(1.0, text="Analysis Complete!")

            # --- RENDER SIDEBAR CODEX ---
            _ = st.sidebar.markdown("---")
            _ = st.sidebar.subheader("📖 Dynamic Character Codex")
            if all_characters:
                for name, details in all_characters.items():
                    with st.sidebar.expander(f"👤 {name.title()}"):
                        _ = st.write(f"**Traits:** {details.get('physical_traits', 'None detected')}")
                        _ = st.write(f"**Current Motivation:** {details.get('current_motivation', 'Unknown')}")
            else:
                _ = st.sidebar.info("No distinct characters detected.")

            # Calculate final averages
            for pillar in avg_scores.keys():
                avg_scores[pillar] = int(avg_scores[pillar] / len(chunks))

            _ = st.success("Grading Complete!")

            # --- TENSION LINE GRAPH ---
            if len(pacing_data["agency"]) > 1:
                _ = st.subheader("📈 Manuscript Pacing")
                pillar_choice: str = st.selectbox(
                    "Chart which pillar?",
                    PILLAR_KEYS,
                    format_func=_format_pillar_label,
                    index=1,  # defaults to Conflict & Stakes, matching old behavior
                )
                _ = st.line_chart(pacing_data[pillar_choice])
                _ = st.caption(
                    "A healthy story usually features rising tension (peaks) followed by "
                    + "brief moments of resolution (valleys). Flat lines indicate pacing issues."
                )

                # --- PACING LULL DETECTION ---
                lull_threshold = 50
                lull_sections = [
                    i + 1 for i, score in enumerate(pacing_data[pillar_choice]) if score < lull_threshold
                ]
                if lull_sections:
                    section_list = ", ".join(str(s) for s in lull_sections)
                    _ = st.warning(
                        f"⚠️ **Pacing lull detected** in {_format_pillar_label(pillar_choice)}: "
                        + f"Section(s) {section_list} scored below {lull_threshold}/100."
                    )

            _ = st.header("Average Content Grades")
            col1, col2 = st.columns(2)

            final_chunk: CritiqueResult = all_results[-1]

            with col1:
                _ = st.subheader("Agency & Conflict")
                _ = st.write("**Character Agency (Avg)**")
                _ = st.progress(avg_scores["agency"])
                _ = st.success(f"**Tip from Final Scene:** {_pillar_data(final_chunk, 'agency').get('actionable_advice', '')}")

                _ = st.write("---")
                _ = st.write("**Conflict & Stakes (Avg)**")
                _ = st.progress(avg_scores["conflict_and_stakes"])
                _ = st.warning(f"**Tip from Final Scene:** {_pillar_data(final_chunk, 'conflict_and_stakes').get('actionable_advice', '')}")

            with col2:
                _ = st.subheader("Structure & Arcs")
                _ = st.write("**Compelling Arcs (Avg)**")
                _ = st.progress(avg_scores["compelling_arcs"])
                _ = st.info(f"**Tip from Final Scene:** {_pillar_data(final_chunk, 'compelling_arcs').get('actionable_advice', '')}")

                _ = st.write("---")
                _ = st.write("**Tight Scene Structure (Avg)**")
                _ = st.progress(avg_scores["tight_scene_structure"])
                _ = st.success(f"**Tip from Final Scene:** {_pillar_data(final_chunk, 'tight_scene_structure').get('actionable_advice', '')}")

            # --- PROSE SNIPER GALLERY ---
            _ = st.write("---")
            _ = st.subheader("🎯 The 'Show, Don't Tell' Prose Sniper Gallery")

            if prose_snipers:
                _ = st.caption(f"{len(prose_snipers)} flagged sentence(s) across {len(chunks)} section(s).")
                for hit in prose_snipers:
                    with st.expander(f"Section {hit['section']}: Target Acquired"):
                        _ = st.error(f"**Telling / Passive Voice:**\n> \"{hit['bad_quote']}\"")
                        _ = st.success(f"**Sniper Rewrite (Showing / Active Voice):**\n> \"{hit['rewritten_example']}\"")
            else:
                _ = st.info("No major prose violations detected across the manuscript. Clean writing!")

            # --- WEAKEST SECTION FINDER ---
            _ = st.write("---")
            _ = st.subheader("🔻 Weakest Section")

            weakest_idx = section_scores.index(min(section_scores))
            weakest_score = section_scores[weakest_idx]
            weakest_result = all_results[weakest_idx]

            _ = st.warning(
                f"**Section {weakest_idx + 1}** scored lowest overall, averaging **{weakest_score:.0f}/100** across all four pillars."
            )
            for pillar in PILLAR_KEYS:
                pillar_data = _pillar_data(weakest_result, pillar)
                with st.expander(f"{_format_pillar_label(pillar)} ({pillar_data.get('score', 0)}/100)"):
                    _ = st.write(f"**Analysis:** {pillar_data.get('analysis', '')}")
                    _ = st.write(f"**Actionable Tip:** {pillar_data.get('actionable_advice', '')}")

            # --- DOWNLOAD REPORT ---
            report_str = generate_markdown_report(
                avg_scores, all_results, all_characters, prose_snipers, section_scores
            )
            _ = st.download_button(
                label="📥 Download Full Offline Report",
                data=report_str,
                file_name="CritiqueForge_Report.md",
                mime="text/markdown"
            )

        except Exception as e:
            _ = st.error(f"An error occurred during grading: {str(e)}")