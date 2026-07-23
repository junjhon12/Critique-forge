import streamlit as st
import PyPDF2
import docx
from datetime import datetime
from dotenv import load_dotenv
from typing import TypedDict, cast
from streamlit.runtime.uploaded_file_manager import UploadedFile
from src.chunker import user_text
from src.ai_client import (
    analyze_chunk, analyze_hook, analyze_query_letter,
    CritiqueResult, CharacterData, PillarData, GENRE_PRESETS,
    HookCritiqueResult, QueryLetterResult,
)
from src.cache import _cache_key, load_cache, save_cache
from src.history import manuscript_id as _manuscript_id, load_history, append_history
from src.diff import render_diff_html
from src.style_audit import audit_filter_words, detect_pov_tense, PovTenseFlag
from src.structure import (
    detect_scenes, map_beats_to_scenes, analyze_pacing_weight,
    analyze_chapter_length_consistency, STRUCTURE_TEMPLATES,
    SceneInfo, BeatMatch, PacingFlag, ChapterLengthFlag,
)

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
    filter_word_counts: dict[str, int] | None = None,
    pov_tense_flags: list[PovTenseFlag] | None = None,
    scenes: list[SceneInfo] | None = None,
    beat_matches: list[BeatMatch] | None = None,
    pacing_flags: list[PacingFlag] | None = None,
    chapter_length_flags: list[ChapterLengthFlag] | None = None,
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

    # --- STYLE & CONSISTENCY AUDIT ---
    shift_flags = [f for f in (pov_tense_flags or []) if f["shifted_pov"] or f["shifted_tense"]]
    if filter_word_counts or shift_flags:
        md += "---\n## 📝 Style & Consistency Audit\n\n"
        if filter_word_counts:
            md += "**Filter word / crutch word counts:**\n\n"
            for term, count in list(filter_word_counts.items())[:15]:
                md += f"- \"{term}\": {count}\n"
            md += "\n"
        if shift_flags:
            md += "**Possible POV/tense shifts (heuristic):**\n\n"
            for flag in shift_flags:
                prev_flag = (pov_tense_flags or [])[flag["chunk_index"] - 1]
                details: list[str] = []
                if flag["shifted_pov"]:
                    details.append(f"POV shifted from {prev_flag['dominant_pov']}-person to {flag['dominant_pov']}-person")
                if flag["shifted_tense"]:
                    details.append(f"tense shifted from {prev_flag['dominant_tense']} to {flag['dominant_tense']}")
                md += f"- Section {flag['chunk_index'] + 1}: {' and '.join(details)}\n"
            md += "\n"

    # --- STRUCTURAL OVERLAY ---
    if scenes and len(scenes) >= 2:
        missing_beats = [b for b in (beat_matches or []) if b["matched_scene_index"] is None]
        pacing_issues = [p for p in (pacing_flags or []) if p["flag"] != "ok"]
        length_issues = [c for c in (chapter_length_flags or []) if c["flag"] != "ok"]
        if missing_beats or pacing_issues or length_issues:
            md += "---\n## 🧭 Structural Overlay\n\n"
            if missing_beats:
                md += "**Missing beats:**\n\n"
                for beat in missing_beats:
                    md += f"- \"{beat['beat_name']}\" expected around {beat['expected_pct']:.0f}% — no scene found nearby\n"
                md += "\n"
            if pacing_issues:
                md += "**Pacing vs. narrative weight:**\n\n"
                for p in pacing_issues:
                    md += f"- Scene {p['scene_index'] + 1} ({p['word_count']} words): flagged as {p['flag'].replace('_', ' ')}\n"
                md += "\n"
            if length_issues:
                md += "**Chapter-length outliers:**\n\n"
                for c in length_issues:
                    md += f"- Scene {c['scene_index'] + 1} ({c['word_count']} words, avg {c['mean_word_count']:.0f}): {c['flag'].replace('_', ' ')}\n"
                md += "\n"

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


def generate_checklist_report(
    all_results: list[CritiqueResult],
    scenes: list[SceneInfo] | None = None,
) -> str:
    """Generates a flat actionable-advice checklist, skipping scores and analysis."""
    md = "# Critique-Forge Action Checklist\n\n"
    for i, result in enumerate(all_results):
        heading = None
        if scenes and i < len(scenes):
            heading = scenes[i].get("heading")
        md += f"## {heading if heading else f'Section {i + 1}'}\n"
        for pillar in PILLAR_KEYS:
            advice = _pillar_data(result, pillar).get("actionable_advice", "").strip()
            if advice:
                md += f"- [ ] {_format_pillar_label(pillar)}: {advice}\n"
        md += "\n"
    return md


def generate_hook_report(result: HookCritiqueResult) -> str:
    """Generates a short report for the 'Read Like an Agent' first-page analysis."""
    md = "# Critique-Forge: Read Like an Agent Report\n\n"
    verdict = "✅ Would request more pages" if result.get("would_request_more") else "❌ Would pass on this submission"
    md += f"**Verdict:** {verdict}\n\n"
    hook = result.get("hook_strength", {})
    md += f"## Hook Strength ({hook.get('score', 0)}/100)\n"
    md += f"> *Analysis:* {hook.get('analysis', '')}\n>\n"
    md += f"> *Actionable Tip:* {hook.get('actionable_advice', '')}\n\n"
    voice = result.get("voice_and_clarity", {})
    md += f"## Voice & Clarity ({voice.get('score', 0)}/100)\n"
    md += f"> *Analysis:* {voice.get('analysis', '')}\n>\n"
    md += f"> *Actionable Tip:* {voice.get('actionable_advice', '')}\n\n"
    reasons = result.get("rejection_reasons", [])
    if reasons:
        md += "## Rejection Reasons\n"
        for reason in reasons:
            md += f"- {reason}\n"
        md += "\n"
    return md


def generate_query_letter_report(result: QueryLetterResult) -> str:
    """Generates a short report for the Query Letter / Synopsis analysis."""
    md = "# Critique-Forge: Query Letter / Synopsis Report\n\n"
    md += f"**Overall Verdict:** {result.get('overall_verdict', '')}\n\n"
    for pillar, label in [
        ("hook_strength", "Hook Strength"),
        ("genre_clarity", "Genre Clarity"),
        ("stakes_clarity", "Stakes Clarity"),
    ]:
        data = result.get(pillar, {})
        md += f"## {label} ({data.get('score', 0)}/100)\n"
        md += f"> *Analysis:* {data.get('analysis', '')}\n>\n"
        md += f"> *Actionable Tip:* {data.get('actionable_advice', '')}\n\n"
    md += f"## Suggested One-Line Pitch\n\n> {result.get('one_line_pitch_rewrite', '')}\n"
    return md


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
    _ = st.markdown("Paste your query letter or synopsis to critique its hook, genre clarity, and stakes.")

    query_text: str = st.text_area("Paste your query letter or synopsis:", height=250)

    if st.button("Analyze Query Letter"):
        if not query_text.strip():
            _ = st.error("Paste a query letter or synopsis to analyze.")
        else:
            try:
                query_cache = load_cache()
                query_key = _cache_key(query_text, "Query Letter", "")
                if query_key in query_cache:
                    query_result: QueryLetterResult = query_cache[query_key]
                else:
                    query_result = analyze_query_letter(query_text)
                    query_cache[query_key] = query_result
                    save_cache(query_cache)

                _ = st.success("Analysis Complete!")
                _ = st.header(f"Overall Verdict: {query_result.get('overall_verdict', '')}")

                for pillar, label in [
                    ("hook_strength", "Hook Strength"),
                    ("genre_clarity", "Genre Clarity"),
                    ("stakes_clarity", "Stakes Clarity"),
                ]:
                    data = query_result.get(pillar, {})
                    _ = st.subheader(f"{label} ({data.get('score', 0)}/100)")
                    _ = st.progress(data.get("score", 0))
                    _ = st.write(f"**Analysis:** {data.get('analysis', '')}")
                    _ = st.write(f"**Actionable Tip:** {data.get('actionable_advice', '')}")

                _ = st.write("---")
                _ = st.info(f"**Suggested one-line pitch:** {query_result.get('one_line_pitch_rewrite', '')}")

                query_report_str = generate_query_letter_report(query_result)
                _ = st.download_button(
                    label="📥 Download Query Letter Report",
                    data=query_report_str,
                    file_name="CritiqueForge_QueryLetter_Report.md",
                    mime="text/markdown",
                )
            except Exception as e:
                _ = st.error(f"An error occurred during grading: {str(e)}")

elif analysis_mode == "Read Like an Agent (First Page)":
    _ = st.markdown("Upload or paste your opening page/chapter to see if it would earn a full request from an agent.")

    uploaded_file: UploadedFile | None = st.file_uploader(
        "Import document here", type=["txt", "md", "pdf", "docx"]
    )
    text_input: str = st.text_area("Or paste the content here:", height=200)

    if st.button("Analyze Opening"):
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
            try:
                chunks = user_text(raw_text)
                scenes = detect_scenes(raw_text, chunks)
                first_chunk = chunks[0]

                hook_cache = load_cache()
                hook_key = _cache_key(first_chunk, "Read Like an Agent", selected_genre)
                if hook_key in hook_cache:
                    hook_result: HookCritiqueResult = hook_cache[hook_key]
                else:
                    hook_result = analyze_hook(first_chunk, genre=selected_genre)
                    hook_cache[hook_key] = hook_result
                    save_cache(hook_cache)

                _ = st.success("Analysis Complete!")

                if hook_result.get("would_request_more"):
                    _ = st.success("✅ **This agent would request more pages.**")
                else:
                    _ = st.error("❌ **This agent would pass on this submission.**")

                hook_data = hook_result.get("hook_strength", {})
                _ = st.subheader(f"Hook Strength ({hook_data.get('score', 0)}/100)")
                _ = st.progress(hook_data.get("score", 0))
                _ = st.write(f"**Analysis:** {hook_data.get('analysis', '')}")
                _ = st.write(f"**Actionable Tip:** {hook_data.get('actionable_advice', '')}")

                voice_data = hook_result.get("voice_and_clarity", {})
                _ = st.subheader(f"Voice & Clarity ({voice_data.get('score', 0)}/100)")
                _ = st.progress(voice_data.get("score", 0))
                _ = st.write(f"**Analysis:** {voice_data.get('analysis', '')}")
                _ = st.write(f"**Actionable Tip:** {voice_data.get('actionable_advice', '')}")

                rejection_reasons = hook_result.get("rejection_reasons", [])
                if rejection_reasons:
                    _ = st.write("---")
                    _ = st.subheader("Rejection Reasons")
                    for reason in rejection_reasons:
                        _ = st.warning(reason)

                current_manuscript_id = _manuscript_id(manuscript_name)
                append_history(current_manuscript_id, {
                    "timestamp": datetime.now().isoformat(),
                    "persona": "Read Like an Agent",
                    "genre": selected_genre,
                    "avg_scores": {
                        "agency": 0, "conflict_and_stakes": 0,
                        "compelling_arcs": 0, "tight_scene_structure": 0,
                    },
                    "num_sections": 1,
                })

                hook_report_str = generate_hook_report(hook_result)
                _ = st.download_button(
                    label="📥 Download Agent Read Report",
                    data=hook_report_str,
                    file_name="CritiqueForge_AgentRead_Report.md",
                    mime="text/markdown",
                )
            except Exception as e:
                _ = st.error(f"An error occurred during grading: {str(e)}")

else:
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

            # --- LOCAL STYLE & CONSISTENCY AUDIT (no LLM call, runs on every analysis) ---
            filter_word_counts: dict[str, int] = audit_filter_words(raw_text)
            pov_tense_flags: list[PovTenseFlag] = detect_pov_tense(chunks)

            # --- STRUCTURAL/OUTLINE-LEVEL ANALYSIS (no LLM call, runs on every analysis) ---
            scenes: list[SceneInfo] = detect_scenes(raw_text, chunks)
            beat_matches: list[BeatMatch] = map_beats_to_scenes(scenes, selected_structure_template)
            pacing_flags: list[PacingFlag] = analyze_pacing_weight(
                scenes,
                selected_structure_template if selected_structure_template != "None / General" else None,
            )
            chapter_length_flags: list[ChapterLengthFlag] = analyze_chapter_length_consistency(scenes)

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
            cache = load_cache()

            try:
                # Process the Entire Manuscript Loop
                for i, chunk in enumerate(chunks):
                    _ = progress_bar.progress(
                        (i) / len(chunks), text=f"Analyzing Section {i+1} of {len(chunks)}..."
                    )
                    cache_persona = custom_prompt if selected_persona == "Custom" else selected_persona
                    key = _cache_key(chunk, cache_persona, selected_genre)
                    if key in cache:
                        result: CritiqueResult = cache[key]
                    else:
                        result = analyze_chunk(
                            chunk,
                            persona=selected_persona,
                            custom_system_prompt=custom_prompt if selected_persona == "Custom" else None,
                            genre=selected_genre,
                        )
                        cache[key] = result
                        save_cache(cache)
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

                # --- PERSIST FOR REVISION WORKFLOW ---
                current_manuscript_id = _manuscript_id(manuscript_name)
                append_history(current_manuscript_id, {
                    "timestamp": datetime.now().isoformat(),
                    "persona": cache_persona,
                    "genre": selected_genre,
                    "avg_scores": avg_scores,
                    "num_sections": len(chunks),
                })
                st.session_state["manuscript_id"] = current_manuscript_id
                st.session_state["last_chunks"] = chunks
                st.session_state["last_results"] = all_results
                st.session_state["last_persona"] = selected_persona
                st.session_state["last_custom_prompt"] = custom_prompt
                st.session_state["last_genre"] = selected_genre
                st.session_state["last_scenes"] = scenes

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

                # --- STYLE & CONSISTENCY AUDIT (local, no LLM) ---
                _ = st.write("---")
                _ = st.subheader("📝 Style & Consistency Audit")

                shift_flags = [f for f in pov_tense_flags if f["shifted_pov"] or f["shifted_tense"]]

                if filter_word_counts:
                    _ = st.caption("Crutch words and filter-word counts across the manuscript (local scan, no LLM).")
                    _ = st.dataframe(
                        [{"Term": term, "Count": count} for term, count in list(filter_word_counts.items())[:15]],
                        use_container_width=True,
                    )
                if shift_flags:
                    for flag in shift_flags:
                        prev_flag = pov_tense_flags[flag["chunk_index"] - 1]
                        details: list[str] = []
                        if flag["shifted_pov"]:
                            details.append(f"POV shifted from {prev_flag['dominant_pov']}-person to {flag['dominant_pov']}-person")
                        if flag["shifted_tense"]:
                            details.append(f"tense shifted from {prev_flag['dominant_tense']} to {flag['dominant_tense']}")
                        _ = st.warning(
                            f"**Section {flag['chunk_index'] + 1}:** possible {' and '.join(details)}. "
                            "(Heuristic detection — may be an intentional POV/tense change.)"
                        )
                if not filter_word_counts and not shift_flags:
                    _ = st.info("No notable filter-word overuse or POV/tense shifts detected.")

                # --- STRUCTURAL OVERLAY (local, no LLM) ---
                _ = st.write("---")
                _ = st.subheader("🧭 Structural Overlay")

                if len(scenes) < 2:
                    _ = st.info(
                        "Manuscript too short or no scene/chapter breaks detected — "
                        "structural analysis needs at least 2 scenes."
                    )
                else:
                    if all(s["heading"] is None for s in scenes):
                        _ = st.caption(
                            "No chapter/scene headings or break markers detected — using "
                            "token-based sections as pseudo-scenes for structural analysis."
                        )

                    _ = st.write("**Beat Sheet**")
                    if selected_structure_template == "None / General":
                        _ = st.info("Select a structure template in the sidebar to enable beat-sheet mapping.")
                    else:
                        _ = st.dataframe(
                            [
                                {
                                    "Beat": b["beat_name"],
                                    "Expected %": f"{b['expected_pct']:.0f}%",
                                    "Matched Scene": (b["matched_scene_index"] + 1) if b["matched_scene_index"] is not None else "—",
                                }
                                for b in beat_matches
                            ],
                            use_container_width=True,
                        )
                        for b in beat_matches:
                            if b["matched_scene_index"] is None:
                                _ = st.warning(
                                    f"Missing beat: \"{b['beat_name']}\" expected around "
                                    f"{b['expected_pct']:.0f}% — no scene found nearby."
                                )

                    _ = st.write("**Pacing vs. Narrative Weight**")
                    pacing_issues = [p for p in pacing_flags if p["flag"] != "ok"]
                    _ = st.dataframe(
                        [
                            {
                                "Scene": p["scene_index"] + 1,
                                "Words": p["word_count"],
                                "Actual Weight": f"{p['actual_weight'] * 100:.1f}%",
                                "Expected Weight": f"{p['expected_weight'] * 100:.1f}%",
                                "Flag": p["flag"],
                            }
                            for p in pacing_flags
                        ],
                        use_container_width=True,
                    )
                    for p in pacing_issues:
                        _ = st.warning(f"Scene {p['scene_index'] + 1} flagged as **{p['flag'].replace('_', ' ')}** relative to its expected narrative weight.")

                    _ = st.write("**Chapter-Length Consistency**")
                    length_issues = [c for c in chapter_length_flags if c["flag"] != "ok"]
                    _ = st.dataframe(
                        [
                            {
                                "Scene": c["scene_index"] + 1,
                                "Words": c["word_count"],
                                "Manuscript Avg": f"{c['mean_word_count']:.0f}",
                                "Deviation": f"{c['pct_deviation']:+.0f}%",
                                "Flag": c["flag"],
                            }
                            for c in chapter_length_flags
                        ],
                        use_container_width=True,
                    )
                    for c in length_issues:
                        _ = st.warning(f"Scene {c['scene_index'] + 1} is a length **{c['flag'].replace('_', ' ')}** ({c['pct_deviation']:+.0f}% vs. manuscript average).")

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
                    avg_scores, all_results, all_characters, prose_snipers, section_scores,
                    filter_word_counts, pov_tense_flags,
                    scenes, beat_matches, pacing_flags, chapter_length_flags,
                )
                _ = st.download_button(
                    label="📥 Download Full Offline Report",
                    data=report_str,
                    file_name="CritiqueForge_Report.md",
                    mime="text/markdown"
                )

                checklist_str = generate_checklist_report(all_results, scenes)
                _ = st.download_button(
                    label="✅ Download Actionable Checklist",
                    data=checklist_str,
                    file_name="CritiqueForge_Checklist.md",
                    mime="text/markdown"
                )

            except Exception as e:
                _ = st.error(f"An error occurred during grading: {str(e)}")

    # --- VERSION HISTORY ---
    history_manuscript_id = _manuscript_id(manuscript_name)
    manuscript_history = load_history(history_manuscript_id)
    if manuscript_history:
        _ = st.write("---")
        _ = st.header("📜 Version History")
        _ = st.caption(f"All past analysis runs logged under manuscript name \"{manuscript_name}\".")

        history_table = [
            {
                "Timestamp": entry["timestamp"],
                "Persona": entry["persona"],
                "Sections": entry["num_sections"],
                **{_format_pillar_label(p): entry["avg_scores"].get(p, 0) for p in PILLAR_KEYS},
            }
            for entry in manuscript_history
        ]
        _ = st.dataframe(history_table, use_container_width=True)

        if len(manuscript_history) > 1:
            history_pillar_choice: str = st.selectbox(
                "Chart which pillar across runs?",
                PILLAR_KEYS,
                format_func=_format_pillar_label,
                key="history_pillar_choice",
            )
            _ = st.line_chart([entry["avg_scores"].get(history_pillar_choice, 0) for entry in manuscript_history])

    # --- REVISE & COMPARE ---
    if "last_chunks" in st.session_state and st.session_state.get("manuscript_id") == history_manuscript_id:
        _ = st.write("---")
        _ = st.header("🔁 Revise & Compare")
        _ = st.caption("Paste a rewritten version of a section to see what changed and whether the scores improved.")

        last_chunks: list[str] = st.session_state["last_chunks"]
        last_results: list[CritiqueResult] = st.session_state["last_results"]

        revise_section_num: int = st.selectbox(
            "Which section do you want to revise?",
            list(range(1, len(last_chunks) + 1)),
            key="revise_section_num",
        )
        revise_idx = revise_section_num - 1
        original_chunk = last_chunks[revise_idx]
        original_result = last_results[revise_idx]

        with st.expander("Show original section text"):
            _ = st.write(original_chunk)

        revised_text: str = st.text_area("Paste your rewritten version of this section:", height=200, key="revised_text")

        if st.button("Re-score & Compare"):
            if not revised_text.strip():
                _ = st.error("Paste a rewritten version of the section first.")
            else:
                revise_persona: str = st.session_state["last_persona"]
                revise_custom_prompt: str = st.session_state.get("last_custom_prompt", "")
                revise_genre: str = st.session_state.get("last_genre", "None / General")
                revise_cache_persona = revise_custom_prompt if revise_persona == "Custom" else revise_persona

                revise_cache = load_cache()
                revise_key = _cache_key(revised_text, revise_cache_persona, revise_genre)
                if revise_key in revise_cache:
                    revised_result: CritiqueResult = revise_cache[revise_key]
                else:
                    revised_result = analyze_chunk(
                        revised_text,
                        persona=revise_persona,
                        custom_system_prompt=revise_custom_prompt if revise_persona == "Custom" else None,
                        genre=revise_genre,
                    )
                    revise_cache[revise_key] = revised_result
                    save_cache(revise_cache)

                _ = st.subheader("What changed")
                _ = st.markdown(render_diff_html(original_chunk, revised_text), unsafe_allow_html=True)

                _ = st.subheader("Score deltas")
                delta_cols = st.columns(4)
                for col, pillar in zip(delta_cols, PILLAR_KEYS):
                    old_score = _pillar_data(original_result, pillar).get("score", 0)
                    new_score = _pillar_data(revised_result, pillar).get("score", 0)
                    with col:
                        _ = st.metric(
                            label=_format_pillar_label(pillar),
                            value=new_score,
                            delta=new_score - old_score,
                        )