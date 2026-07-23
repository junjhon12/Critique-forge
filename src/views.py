from datetime import datetime

import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from src.ai_client import (
    analyze_chunk, analyze_hook, analyze_query_letter, analyze_cliffhanger, extract_bible_entities,
    analyze_recap,
    CritiqueResult, CharacterData, HookCritiqueResult, QueryLetterResult, CliffhangerResult,
    RecapResult,
)
from src.consistency import merge_entity, StoryBibleEntry, ConsistencyFlag
from src.cache import _cache_key, load_cache, save_cache
from src.history import manuscript_id as _manuscript_id, load_history, append_history
from src.diff import render_diff_html
from src.style_audit import audit_filter_words, detect_pov_tense, PovTenseFlag
from src.structure import (
    detect_scenes, map_beats_to_scenes, analyze_pacing_weight,
    analyze_chapter_length_consistency, check_platform_pacing_conformance,
    SceneInfo, BeatMatch, PacingFlag, ChapterLengthFlag, PlatformPacingFlag,
)
from src.chunker import user_text
from src.file_io import extract_text_from_file, extract_text_from_files
from src.reports import (
    PILLAR_KEYS, SniperHit, pillar_data, format_pillar_label,
    generate_markdown_report, generate_checklist_report,
    generate_hook_report, generate_query_letter_report,
    ChapterReadinessCheck, build_readiness_checklist,
)


def render_query_letter_mode() -> None:
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


def render_agent_read_mode(manuscript_name: str, selected_genre: str) -> None:
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


def render_full_manuscript_mode(
    manuscript_name: str,
    selected_persona: str,
    custom_prompt: str,
    selected_genre: str,
    selected_structure_template: str,
    platform_min_words: int = 0,
    platform_max_words: int = 0,
    manuscript_format: str = "Web Novel",
) -> None:
    _ = st.markdown("Upload your manuscript to analyze its structural integrity.")

    upload_mode: str = st.radio(
        "Input mode:",
        ["Paste / single file", "Multiple chapter files"],
        horizontal=True,
    )

    uploaded_file: UploadedFile | None = None
    uploaded_chapter_files: list[UploadedFile] = []
    text_input: str = ""

    if upload_mode == "Multiple chapter files":
        uploaded_chapter_files = st.file_uploader(
            "Import chapter files here (one file per chapter, in reading order)",
            type=["txt", "md", "pdf", "docx"],
            accept_multiple_files=True,
        ) or []
    else:
        uploaded_file = st.file_uploader(
            "Import document here", type=["txt", "md", "pdf", "docx"]
        )
        text_input = st.text_area("Or paste the content here:", height=200)

    if st.button("Analyze Manuscript"):
        raw_text: str = ""
        chapter_files: list[tuple[str, str]] = []

        if uploaded_chapter_files:
            try:
                chapter_files = extract_text_from_files(uploaded_chapter_files)
                raw_text = "\n\n".join(text for _name, text in chapter_files)
            except Exception as e:
                _ = st.error(f"Error reading chapter files: {e}")
        elif uploaded_file is not None:
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
            if chapter_files:
                # Each uploaded file is its own chapter; skip heading-regex detection.
                scenes = []
                cursor = 0
                for i, (name, text) in enumerate(chapter_files):
                    word_count = len(text.split())
                    scenes.append({
                        "index": i,
                        "heading": name,
                        "start_word": cursor,
                        "word_count": word_count,
                        "pct_start": 0.0,
                        "pct_end": 0.0,
                    })
                    cursor += word_count
                total_words = cursor or 1
                for s in scenes:
                    s["pct_start"] = s["start_word"] / total_words * 100
                    s["pct_end"] = (s["start_word"] + s["word_count"]) / total_words * 100
            else:
                scenes: list[SceneInfo] = detect_scenes(raw_text, chunks)
            beat_matches: list[BeatMatch] = map_beats_to_scenes(scenes, selected_structure_template)
            pacing_flags: list[PacingFlag] = analyze_pacing_weight(
                scenes,
                selected_structure_template if selected_structure_template != "None / General" else None,
            )
            chapter_length_flags: list[ChapterLengthFlag] = analyze_chapter_length_consistency(scenes)
            is_web_novel = manuscript_format == "Web Novel"
            platform_pacing_flags: list[PlatformPacingFlag] = (
                check_platform_pacing_conformance(scenes, platform_min_words, platform_max_words)
                if is_web_novel else []
            )

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
            story_bible: dict[str, StoryBibleEntry] = {}  # Running character/terminology bible across chunks
            consistency_flags: list[ConsistencyFlag] = []  # Detected contradictions across chunks

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
                        pacing_data[pillar].append(pillar_data(result, pillar).get("score", 0))

                    # --- TRACK WEAKEST SECTION ---
                    section_avg = sum(pillar_data(result, p).get("score", 0) for p in PILLAR_KEYS) / 4
                    section_scores.append(section_avg)

                    # Accumulate scores
                    for pillar in avg_scores.keys():
                        avg_scores[pillar] += pillar_data(result, pillar).get("score", 0)

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

                    # --- UPDATE STORY BIBLE / CONSISTENCY CHECK ---
                    bible_key = _cache_key(chunk, "Story Bible", "")
                    if bible_key in cache:
                        bible_result = cache[bible_key]
                    else:
                        bible_result = extract_bible_entities(chunk)
                        cache[bible_key] = bible_result
                        save_cache(cache)
                    for bible_entity in bible_result.get("entities", []):
                        consistency_flags.extend(merge_entity(story_bible, bible_entity, i))

                # --- CLIFFHANGER / CHAPTER-ENDING HOOK SCORING (per scene, LLM; Web Novel only) ---
                cliffhanger_results: dict[int, CliffhangerResult] = {}
                if is_web_novel and len(scenes) >= 2:
                    words = raw_text.split()
                    for scene in scenes:
                        _ = progress_bar.progress(
                            0.9, text=f"Scoring chapter ending {scene['index'] + 1} of {len(scenes)}..."
                        )
                        end_word = scene["start_word"] + scene["word_count"]
                        ending_text = " ".join(words[max(scene["start_word"], end_word - 250):end_word])
                        if not ending_text.strip():
                            continue
                        cliff_key = _cache_key(ending_text, "Cliffhanger", selected_genre)
                        if cliff_key in cache:
                            cliff_result: CliffhangerResult = cache[cliff_key]
                        else:
                            cliff_result = analyze_cliffhanger(ending_text, genre=selected_genre)
                            cache[cliff_key] = cliff_result
                            save_cache(cache)
                        cliffhanger_results[scene["index"]] = cliff_result

                readiness_checklist: list[ChapterReadinessCheck] = (
                    build_readiness_checklist(scenes, platform_pacing_flags, cliffhanger_results)
                    if is_web_novel else []
                )

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
                st.session_state["last_platform_pacing_flags"] = platform_pacing_flags
                st.session_state["last_cliffhanger_results"] = cliffhanger_results
                st.session_state["last_readiness_checklist"] = readiness_checklist

                # --- TENSION LINE GRAPH ---
                if len(pacing_data["agency"]) > 1:
                    _ = st.subheader("📈 Manuscript Pacing")
                    pillar_choice: str = st.selectbox(
                        "Chart which pillar?",
                        PILLAR_KEYS,
                        format_func=format_pillar_label,
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
                            f"⚠️ **Pacing lull detected** in {format_pillar_label(pillar_choice)}: "
                            + f"Section(s) {section_list} scored below {lull_threshold}/100."
                        )

                _ = st.header("Average Content Grades")
                col1, col2 = st.columns(2)

                final_chunk: CritiqueResult = all_results[-1]

                with col1:
                    _ = st.subheader("Agency & Conflict")
                    _ = st.write("**Character Agency (Avg)**")
                    _ = st.progress(avg_scores["agency"])
                    _ = st.success(f"**Tip from Final Scene:** {pillar_data(final_chunk, 'agency').get('actionable_advice', '')}")

                    _ = st.write("---")
                    _ = st.write("**Conflict & Stakes (Avg)**")
                    _ = st.progress(avg_scores["conflict_and_stakes"])
                    _ = st.warning(f"**Tip from Final Scene:** {pillar_data(final_chunk, 'conflict_and_stakes').get('actionable_advice', '')}")

                with col2:
                    _ = st.subheader("Structure & Arcs")
                    _ = st.write("**Compelling Arcs (Avg)**")
                    _ = st.progress(avg_scores["compelling_arcs"])
                    _ = st.info(f"**Tip from Final Scene:** {pillar_data(final_chunk, 'compelling_arcs').get('actionable_advice', '')}")

                    _ = st.write("---")
                    _ = st.write("**Tight Scene Structure (Avg)**")
                    _ = st.progress(avg_scores["tight_scene_structure"])
                    _ = st.success(f"**Tip from Final Scene:** {pillar_data(final_chunk, 'tight_scene_structure').get('actionable_advice', '')}")

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

                    if platform_pacing_flags:
                        _ = st.write("**Platform Word-Count Conformance**")
                        platform_issues = [p for p in platform_pacing_flags if p["flag"] != "ok"]
                        _ = st.dataframe(
                            [
                                {
                                    "Scene": p["scene_index"] + 1,
                                    "Words": p["word_count"],
                                    "Target Range": f"{p['min_words']}-{p['max_words']}",
                                    "Flag": p["flag"],
                                }
                                for p in platform_pacing_flags
                            ],
                            use_container_width=True,
                        )
                        for p in platform_issues:
                            _ = st.warning(
                                f"Scene {p['scene_index'] + 1} is **{p['flag']}** the platform's "
                                f"{p['min_words']}-{p['max_words']} word target ({p['word_count']} words)."
                            )

                    if cliffhanger_results:
                        _ = st.write("**Chapter-Ending Cliffhanger Strength**")
                        _ = st.dataframe(
                            [
                                {
                                    "Scene": idx + 1,
                                    "Cliffhanger Score": r["cliffhanger_strength"].get("score", 0),
                                    "Would Readers Continue?": "Yes" if r.get("would_readers_continue") else "No",
                                }
                                for idx, r in sorted(cliffhanger_results.items())
                            ],
                            use_container_width=True,
                        )
                        for idx, r in sorted(cliffhanger_results.items()):
                            if not r.get("would_readers_continue"):
                                _ = st.warning(
                                    f"Scene {idx + 1} ending scored {r['cliffhanger_strength'].get('score', 0)}/100: "
                                    f"{r['cliffhanger_strength'].get('actionable_advice', '')}"
                                )

                    if readiness_checklist:
                        _ = st.write("**Release-Readiness Checklist**")
                        _ = st.dataframe(
                            [
                                {
                                    "Chapter": c["heading"] or f"Scene {c['scene_index'] + 1}",
                                    "Word Count OK": "✅" if c["word_count_ok"] else "❌",
                                    "Strong Cliffhanger": "✅" if c["has_strong_cliffhanger"] else "❌",
                                    "Ready to Post": "✅" if c["overall_ready"] else "❌",
                                }
                                for c in readiness_checklist
                            ],
                            use_container_width=True,
                        )

                # --- RECAP / "PREVIOUSLY ON..." GENERATOR (LLM; Web Novel only) ---
                if is_web_novel and len(scenes) >= 1:
                    _ = st.write("---")
                    _ = st.subheader("📼 Previously On... Recap Generator")
                    _ = st.caption(
                        "Generate a 'Previously on...' recap of the last chapter (or a recent arc) "
                        "to paste at the top of your next chapter for returning readers."
                    )

                    scene_labels = [
                        scene["heading"] or f"Scene {scene['index'] + 1}" for scene in scenes
                    ]
                    recap_col1, recap_col2 = st.columns(2)
                    with recap_col1:
                        recap_start_idx: int = st.selectbox(
                            "Recap from chapter:",
                            list(range(len(scenes))),
                            index=len(scenes) - 1,
                            format_func=lambda i: scene_labels[i],
                            key="recap_start_idx",
                        )
                    with recap_col2:
                        recap_end_idx: int = st.selectbox(
                            "Recap through chapter:",
                            list(range(len(scenes))),
                            index=len(scenes) - 1,
                            format_func=lambda i: scene_labels[i],
                            key="recap_end_idx",
                        )

                    if recap_end_idx < recap_start_idx:
                        _ = st.warning("The end chapter must be at or after the start chapter.")
                    else:
                        words = raw_text.split()
                        recap_start_word = scenes[recap_start_idx]["start_word"]
                        recap_end_word = scenes[recap_end_idx]["start_word"] + scenes[recap_end_idx]["word_count"]
                        recap_source_text = " ".join(words[recap_start_word:recap_end_word])

                        if not recap_source_text.strip():
                            _ = st.info("No chapter text found for the selected range.")
                        else:
                            recap_key = _cache_key(recap_source_text, "Recap", selected_genre)
                            if recap_key in cache:
                                recap_result: RecapResult = cache[recap_key]
                            else:
                                recap_result = analyze_recap(recap_source_text, genre=selected_genre)
                                cache[recap_key] = recap_result
                                save_cache(cache)

                            _ = st.text_area(
                                "Recap (copy/paste this at the top of your next chapter):",
                                value=recap_result.get("recap", ""),
                                height=200,
                                key="recap_output_text_area",
                            )
                            _ = st.caption(f"**Where it leaves off:** {recap_result.get('cliffhanger_reminder', '')}")

                            recap_download_str = (
                                f"# Previously On...\n\n{recap_result.get('recap', '')}\n\n"
                                f"**Where it leaves off:** {recap_result.get('cliffhanger_reminder', '')}\n"
                            )
                            _ = st.download_button(
                                label="📥 Download Recap",
                                data=recap_download_str,
                                file_name="CritiqueForge_Recap.md",
                                mime="text/markdown",
                                key="recap_download_button",
                            )

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
                    pd = pillar_data(weakest_result, pillar)
                    with st.expander(f"{format_pillar_label(pillar)} ({pd.get('score', 0)}/100)"):
                        _ = st.write(f"**Analysis:** {pd.get('analysis', '')}")
                        _ = st.write(f"**Actionable Tip:** {pd.get('actionable_advice', '')}")

                # --- STORY BIBLE & CONSISTENCY CHECK ---
                _ = st.write("---")
                _ = st.subheader("🗂️ Story Bible & Consistency Check")

                if story_bible:
                    _ = st.caption(f"{len(story_bible)} entit(y/ies) tracked across {len(chunks)} section(s).")
                    for entry in story_bible.values():
                        icon = "👤" if entry["entity_type"] == "character" else "📘"
                        with st.expander(f"{icon} {entry['canonical_name']}"):
                            if entry["aliases"]:
                                _ = st.write(f"**Aliases:** {', '.join(sorted(entry['aliases']))}")
                            for attr_name, sightings in entry["attributes"].items():
                                _ = st.write(f"**{attr_name.replace('_', ' ').title()}:** {sightings[-1]['value']}")
                else:
                    _ = st.info("No characters or terminology detected.")

                if consistency_flags:
                    _ = st.write("**⚠️ Detected Contradictions**")
                    for flag in consistency_flags:
                        _ = st.error(
                            f"**{flag['entity_name']}.{flag['attribute']}** changed from "
                            f"\"{flag['previous_value']}\" (Section {flag['previous_chunk_index'] + 1}) to "
                            f"\"{flag['new_value']}\" (Section {flag['chunk_index'] + 1})."
                        )
                else:
                    _ = st.success(f"No contradictions detected across {len(chunks)} section(s).")

                # --- DOWNLOAD REPORT ---
                report_str = generate_markdown_report(
                    avg_scores, all_results, all_characters, prose_snipers, section_scores,
                    filter_word_counts, pov_tense_flags,
                    scenes, beat_matches, pacing_flags, chapter_length_flags,
                    platform_pacing_flags, readiness_checklist,
                    story_bible, consistency_flags,
                )
                _ = st.download_button(
                    label="📥 Download Full Offline Report",
                    data=report_str,
                    file_name="CritiqueForge_Report.md",
                    mime="text/markdown"
                )

                checklist_str = generate_checklist_report(all_results, scenes, readiness_checklist)
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
                **{format_pillar_label(p): entry["avg_scores"].get(p, 0) for p in PILLAR_KEYS},
            }
            for entry in manuscript_history
        ]
        _ = st.dataframe(history_table, use_container_width=True)

        if len(manuscript_history) > 1:
            history_pillar_choice: str = st.selectbox(
                "Chart which pillar across runs?",
                PILLAR_KEYS,
                format_func=format_pillar_label,
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
                    old_score = pillar_data(original_result, pillar).get("score", 0)
                    new_score = pillar_data(revised_result, pillar).get("score", 0)
                    with col:
                        _ = st.metric(
                            label=format_pillar_label(pillar),
                            value=new_score,
                            delta=new_score - old_score,
                        )
