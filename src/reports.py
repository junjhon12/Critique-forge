from typing import TypedDict, cast

from src.ai_client import (
    CritiqueResult, CharacterData, PillarData, HookCritiqueResult, QueryLetterResult,
    CliffhangerResult, AddictionScoreResult, RetentionSimResult, TropeRadarResult,
    DialogueQualityResult, CharacterArcSnapshotResult, SecondaryCharUtilResult, AgencyDeepDiveResult,
    ProseDepthResult,
)
from src.structure import (
    SceneInfo, BeatMatch, PacingFlag, ChapterLengthFlag, PlatformPacingFlag,
    ArcHealthFlag, PLATFORM_PACING_RATIONALE,
)
from src.style_audit import PovTenseFlag
from src.consistency import StoryBibleEntry, ConsistencyFlag

PILLAR_KEYS: list[str] = ["agency", "conflict_and_stakes", "compelling_arcs", "tight_scene_structure"]


class SniperHit(TypedDict):
    section: int
    bad_quote: str
    rewritten_example: str


class ChapterReadinessCheck(TypedDict):
    scene_index: int
    heading: str | None
    word_count_ok: bool
    has_strong_cliffhanger: bool
    cliffhanger_score: int | None
    overall_ready: bool


def build_readiness_checklist(
    scenes: list[SceneInfo],
    platform_pacing_flags: list[PlatformPacingFlag] | None,
    cliffhanger_results: dict[int, CliffhangerResult] | None,
) -> list[ChapterReadinessCheck]:
    """Aggregates platform-pacing and cliffhanger results into a per-chapter release-readiness checklist."""
    pacing_by_index = {f["scene_index"]: f for f in (platform_pacing_flags or [])}
    cliffhanger_results = cliffhanger_results or {}

    checklist: list[ChapterReadinessCheck] = []
    for scene in scenes:
        idx = scene["index"]
        pacing_flag = pacing_by_index.get(idx)
        word_count_ok = pacing_flag is None or pacing_flag["flag"] == "ok"

        cliff_result = cliffhanger_results.get(idx)
        cliff_score = cliff_result["cliffhanger_strength"].get("score") if cliff_result else None
        has_strong_cliffhanger = bool(cliff_result and cliff_result.get("would_readers_continue"))

        overall_ready = word_count_ok and (cliff_result is None or has_strong_cliffhanger)

        checklist.append({
            "scene_index": idx,
            "heading": scene.get("heading"),
            "word_count_ok": word_count_ok,
            "has_strong_cliffhanger": has_strong_cliffhanger,
            "cliffhanger_score": cliff_score,
            "overall_ready": overall_ready,
        })
    return checklist


def pillar_data(result: CritiqueResult, pillar: str) -> PillarData:
    """Look up a pillar's data by a runtime key without the result widening to Any."""
    return cast(PillarData, result.get(pillar, {}))


def format_pillar_label(pillar: str) -> str:
    return pillar.replace("_", " ").title()


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
    platform_pacing_flags: list[PlatformPacingFlag] | None = None,
    readiness_checklist: list[ChapterReadinessCheck] | None = None,
    story_bible: dict[str, StoryBibleEntry] | None = None,
    consistency_flags: list[ConsistencyFlag] | None = None,
    platform_name: str = "None",
    addiction_results: dict[int, AddictionScoreResult] | None = None,
    arc_health_flags: list[ArcHealthFlag] | None = None,
    trope_radar_result: TropeRadarResult | None = None,
    dialogue_quality_results: dict[int, DialogueQualityResult] | None = None,
    arc_continuity_results: dict[int, CharacterArcSnapshotResult] | None = None,
    secondary_char_util: SecondaryCharUtilResult | None = None,
    agency_deep_dive_results: dict[int, AgencyDeepDiveResult] | None = None,
    prose_depth_results: dict[int, ProseDepthResult] | None = None,
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

    # --- PLATFORM PACING CONFORMANCE ---
    platform_issues = [p for p in (platform_pacing_flags or []) if p["flag"] != "ok"]
    if platform_issues:
        md += "---\n## 📏 Platform Word-Count Conformance (Revenue/Ranking Impact)\n\n"
        rationale = PLATFORM_PACING_RATIONALE.get(platform_name)
        if rationale:
            md += f"*{rationale}*\n\n"
        for p in platform_issues:
            md += (
                f"- Scene {p['scene_index'] + 1} ({p['word_count']} words): "
                f"{p['flag']} the {p['min_words']}-{p['max_words']} word target range "
                f"({p['severity']} deviation)\n"
            )
        md += "\n"

    # --- RELEASE-READINESS CHECKLIST ---
    if readiness_checklist:
        md += "---\n## ✅ Release-Readiness Checklist\n\n"
        for c in readiness_checklist:
            label = c["heading"] or f"Scene {c['scene_index'] + 1}"
            status = "✅ Ready" if c["overall_ready"] else "⚠️ Not ready"
            md += f"- **{label}:** {status}"
            details: list[str] = []
            if not c["word_count_ok"]:
                details.append("word count out of platform range")
            if c["cliffhanger_score"] is not None and not c["has_strong_cliffhanger"]:
                details.append(f"weak cliffhanger ({c['cliffhanger_score']}/100)")
            if details:
                md += f" ({'; '.join(details)})"
            md += "\n"
        md += "\n"

    # --- READER ADDICTION SCORE ---
    if addiction_results:
        md += "---\n## 🔥 Reader Addiction Score\n\n"
        md += "| Chapter | Opening Hook | Mid Tension | Closing Cliffhanger | Composite | Binge-Read? |\n"
        md += "|---------|-------------|------------|--------------------|-----------|-----------|\n"
        for idx in sorted(addiction_results):
            r = addiction_results[idx]
            md += (
                f"| Ch.{idx + 1} "
                f"| {r['opening_hook'].get('score', 0)}/100 "
                f"| {r['mid_tension'].get('score', 0)}/100 "
                f"| {r['closing_cliffhanger'].get('score', 0)}/100 "
                f"| **{r.get('composite_score', 0)}/100** "
                f"| {'✅' if r.get('would_binge_read') else '❌'} |\n"
            )
        md += "\n"

    # --- ARC HEALTH DASHBOARD ---
    if arc_health_flags:
        md += "---\n## 📊 Arc Health Dashboard\n\n"
        for flag in arc_health_flags:
            icon = "⚠️" if flag["flag_type"] == "sagging_middle" else "📉"
            label = "Sagging Middle" if flag["flag_type"] == "sagging_middle" else "Escalation Plateau"
            md += f"**{icon} {label} (Chapters {flag['start_chapter']}–{flag['end_chapter']}):**\n\n"
            md += f"> {flag['description']}\n\n"

    # --- TROPE RADAR ---
    if trope_radar_result and trope_radar_result.get("detected_tropes"):
        md += "---\n## 🎯 Trope Radar\n\n"
        md += f"**Trope DNA:** {trope_radar_result.get('trope_dna_summary', '')}\n\n"
        md += "| Trope | Verdict | Evidence | Suggestion |\n"
        md += "|-------|---------|----------|------------|\n"
        verdict_icons = {"Fresh Twist": "✅", "Standard Execution": "🟡", "Cliche Risk": "🔴"}
        for trope in trope_radar_result.get("detected_tropes", []):
            icon = verdict_icons.get(trope.get("freshness_verdict", ""), "")
            md += (
                f"| {trope.get('trope_name', '')} "
                f"| {icon} {trope.get('freshness_verdict', '')} "
                f"| {trope.get('evidence', '')} "
                f"| {trope.get('suggestion', '') or '—'} |\n"
            )
        md += "\n"

    # --- STORY BIBLE & CONSISTENCY CHECK ---
    if story_bible:
        md += "---\n## 🗂️ Story Bible\n\n"
        for entry in story_bible.values():
            icon = "👤" if entry["entity_type"] == "character" else "📘"
            md += f"### {icon} {entry['canonical_name']}\n"
            if entry["aliases"]:
                md += f"- **Aliases:** {', '.join(sorted(entry['aliases']))}\n"
            for attr_name, sightings in entry["attributes"].items():
                md += f"- **{attr_name.replace('_', ' ').title()}:** {sightings[-1]['value']}\n"
            md += "\n"

        if consistency_flags:
            md += "## ⚠️ Detected Contradictions\n\n"
            for flag in consistency_flags:
                md += (
                    f"- **{flag['entity_name']}.{flag['attribute']}** changed from "
                    f"\"{flag['previous_value']}\" (Section {flag['previous_chunk_index'] + 1}) to "
                    f"\"{flag['new_value']}\" (Section {flag['chunk_index'] + 1})\n"
                )
            md += "\n"

    # --- DIALOGUE QUALITY ANALYSIS ---
    if dialogue_quality_results:
        md += "---\n## 💬 Dialogue Quality Analysis\n\n"
        md += "| Section | Voice Consistency | Subtext Score | Composite |\n"
        md += "|---------|------------------|--------------|----------|\n"
        for idx in sorted(dialogue_quality_results):
            r = dialogue_quality_results[idx]
            md += (
                f"| Section {idx + 1} "
                f"| {r['voice_consistency'].get('score', 0)}/100 "
                f"| {r['subtext_score'].get('score', 0)}/100 "
                f"| **{r.get('composite_score', 0)}/100** |\n"
            )
        md += "\n"
        # Sub-score breakdown for each section
        for idx in sorted(dialogue_quality_results):
            r = dialogue_quality_results[idx]
            composite = r.get("composite_score", 0)
            if composite < 60:
                md += f"#### Section {idx + 1} — Dialogue Notes (Composite {composite}/100)\n"
                vc = r.get("voice_consistency", {})
                sub = r.get("subtext_score", {})
                md += f"- **Voice Consistency ({vc.get('score', 0)}/100):** {vc.get('analysis', '')}\n"
                md += f"  - *Tip:* {vc.get('actionable_advice', '')}\n"
                md += f"- **Subtext Score ({sub.get('score', 0)}/100):** {sub.get('analysis', '')}\n"
                md += f"  - *Tip:* {sub.get('actionable_advice', '')}\n"
                ratio_note = r.get("dialogue_ratio_note", "")
                if ratio_note:
                    md += f"- **Dialogue Ratio:** {ratio_note}\n"
                flagged = r.get("flagged_lines", [])
                if flagged:
                    md += "- **Flagged Lines:**\n"
                    for line in flagged:
                        md += f'  - 🔴 "{line}"\n'
                md += "\n"

    # --- CHARACTER ARC CONTINUITY ---
    if arc_continuity_results:
        char_arc_timelines: dict[str, list[tuple[int, str, str, str]]] = {}
        for sec_idx, snap in sorted(arc_continuity_results.items()):
            for entry in snap.get("characters", []):
                name = entry.get("character_name", "")
                if not name:
                    continue
                char_arc_timelines.setdefault(name, []).append((
                    sec_idx,
                    entry.get("emotional_state", ""),
                    entry.get("core_goal", ""),
                    entry.get("arc_note", ""),
                ))
        major_chars = {n: t for n, t in char_arc_timelines.items() if len(t) >= 3}
        if major_chars:
            md += "---\n## 🧬 Character Arc Continuity\n\n"
            arc_note_icons = {"progressing": "🟢", "stalled": "🟡", "reversal": "🔴", "resolved": "✅"}
            for char_name, timeline in sorted(major_chars.items()):
                stall_count = sum(1 for _, _, _, note in timeline if note == "stalled")
                reversal_count = sum(1 for _, _, _, note in timeline if note == "reversal")
                flag = " *(Arc Reversal detected)*" if reversal_count else (" *(Stalled Arc)*" if stall_count >= 5 else "")
                md += f"### 👤 {char_name}{flag}\n\n"
                md += "| Section | Emotional State | Core Goal | Arc Note |\n"
                md += "|---------|----------------|-----------|----------|\n"
                for sec_idx, state, goal, note in timeline:
                    icon = arc_note_icons.get(note, "")
                    md += f"| Section {sec_idx + 1} | {state} | {goal} | {icon} {note.title()} |\n"
                md += "\n"

    # --- SECONDARY CHARACTER UNDERUTILIZATION ---
    if secondary_char_util is not None:
        secondary_chars = secondary_char_util.get("characters", [])
        overall_note = secondary_char_util.get("overall_note", "")
        if secondary_chars:
            md += "---\n## 👥 Secondary Character Underutilization\n\n"
            if overall_note:
                md += f"> {overall_note}\n\n"
            verdict_icons = {"well-used": "✅", "underused": "🟡", "prop": "🔴"}
            md += "| Character | Role | Verdict | Intro Ch. | Last Active Ch. | Suggestion |\n"
            md += "|-----------|------|---------|-----------|-----------------|------------|\n"
            for c in secondary_chars:
                icon = verdict_icons.get(c.get("utilization_verdict", ""), "")
                md += (
                    f"| {c.get('character_name', '')} "
                    f"| {c.get('narrative_role', '').replace('_', ' ').title()} "
                    f"| {icon} {c.get('utilization_verdict', '').title()} "
                    f"| {c.get('introduction_chapter', '?')} "
                    f"| {c.get('last_active_chapter', '?')} "
                    f"| {c.get('suggestion', '') or '—'} |\n"
                )
            md += "\n"

    # --- PROTAGONIST AGENCY DEEP-DIVE ---
    if agency_deep_dive_results:
        md += "---\n## 🎯 Protagonist Agency Deep-Dive\n\n"
        md += "| Section | Proactive | Reactive | Goal Clarity | Consequence Wt. | Agency Type |\n"
        md += "|---------|-----------|----------|-------------|----------------|------------|\n"
        agency_icons = {"Fully Proactive": "🟢", "Mostly Proactive": "🔵", "Reactive": "🟡", "Passenger": "🔴"}
        for idx in sorted(agency_deep_dive_results):
            r = agency_deep_dive_results[idx]
            icon = agency_icons.get(r.get("agency_type_label", ""), "")
            md += (
                f"| Section {idx + 1} "
                f"| {r.get('proactive_score', 0)}/100 "
                f"| {r.get('reactive_score', 0)}/100 "
                f"| {r.get('goal_clarity', {}).get('score', 0)}/100 "
                f"| {r.get('consequence_weight', {}).get('score', 0)}/100 "
                f"| {icon} {r.get('agency_type_label', '')} |\n"
            )
        md += "\n"
        passenger_sections = [(idx, r) for idx, r in sorted(agency_deep_dive_results.items()) if r.get("agency_type_label") == "Passenger"]
        if passenger_sections:
            md += "### ⚠️ Passenger Sections\n\n"
            for idx, r in passenger_sections:
                md += f"**Section {idx + 1}:** {r.get('key_observation', '')}\n\n"
                gc = r.get("goal_clarity", {})
                cw = r.get("consequence_weight", {})
                md += f"- **Goal Clarity ({gc.get('score', 0)}/100):** {gc.get('analysis', '')}\n"
                md += f"  - *Tip:* {gc.get('actionable_advice', '')}\n"
                md += f"- **Consequence Weight ({cw.get('score', 0)}/100):** {cw.get('analysis', '')}\n"
                md += f"  - *Tip:* {cw.get('actionable_advice', '')}\n\n"

    # --- PROSE ELEGANCE AUDIT ---
    if prose_depth_results:
        md += "---\n## ✍️ Prose Elegance Audit\n\n"
        md += "| Section | Rhythm Variety | Passive Voice | Adverb Density | Composite |\n"
        md += "|---------|---------------|--------------|----------------|----------|\n"
        weakest_pe_idx = min(prose_depth_results, key=lambda i: prose_depth_results[i].get("prose_elegance", {}).get("composite_score", 100))  # type: ignore[arg-type]
        for idx in sorted(prose_depth_results):
            pe = prose_depth_results[idx].get("prose_elegance", {})
            md += (
                f"| Section {idx + 1} "
                f"| {pe.get('rhythm_variety', {}).get('score', 0)}/100 "
                f"| {pe.get('passive_voice_score', {}).get('score', 0)}/100 "
                f"| {pe.get('adverb_density_score', {}).get('score', 0)}/100 "
                f"| {pe.get('composite_score', 0)}/100 |\n"
            )
        md += "\n"
        weakest_pe = prose_depth_results[weakest_pe_idx].get("prose_elegance", {})
        md += f"### Weakest Section — Section {weakest_pe_idx + 1} (Composite: {weakest_pe.get('composite_score', 0)}/100)\n\n"
        for sub_key, sub_label in [("rhythm_variety", "Rhythm Variety"), ("passive_voice_score", "Passive Voice"), ("adverb_density_score", "Adverb Density")]:
            sub = weakest_pe.get(sub_key, {})
            md += f"**{sub_label} ({sub.get('score', 0)}/100):** {sub.get('analysis', '')}\n"
            md += f"- *Tip:* {sub.get('actionable_advice', '')}\n"
        weak_passages = weakest_pe.get("weak_passages", [])
        if weak_passages:
            md += "\n**Weakest Passages:**\n"
            for p in weak_passages:
                md += f'- "{p}"\n'
        md += "\n"

    # --- SHOW-DON'T-TELL DEEP-DIVE ---
    if prose_depth_results:
        md += "---\n## 🔍 Show-Don't-Tell Deep-Dive\n\n"
        md += "| Section | Compliance | Told % | Emotion Tells | Action Tells | Thought Tells |\n"
        md += "|---------|-----------|--------|--------------|-------------|---------------|\n"
        weakest_sdt_idx = min(prose_depth_results, key=lambda i: prose_depth_results[i].get("show_dont_tell", {}).get("compliance_score", 100))  # type: ignore[arg-type]
        for idx in sorted(prose_depth_results):
            sdt = prose_depth_results[idx].get("show_dont_tell", {})
            md += (
                f"| Section {idx + 1} "
                f"| {sdt.get('compliance_score', 0)}/100 "
                f"| {sdt.get('told_percentage', 0)}% "
                f"| {sdt.get('emotion_tells', 0)} "
                f"| {sdt.get('action_tells', 0)} "
                f"| {sdt.get('thought_tells', 0)} |\n"
            )
        md += "\n"
        weakest_sdt = prose_depth_results[weakest_sdt_idx].get("show_dont_tell", {})
        violations = weakest_sdt.get("worst_violations", [])
        if violations:
            category_labels = {"emotion_telling": "💙 Emotion", "action_telling": "🟠 Action", "thought_telling": "💜 Thought"}
            severity_stars = {1: "★", 2: "★★", 3: "★★★"}
            md += f"### Worst Violations — Section {weakest_sdt_idx + 1} (Compliance: {weakest_sdt.get('compliance_score', 0)}/100)\n\n"
            for v in violations:
                cat_label = category_labels.get(v.get("category", ""), v.get("category", ""))
                stars = severity_stars.get(v.get("severity", 1), "★")
                md += f'- **{cat_label}** {stars}: "{v.get("passage", "")}"\n'
        md += "\n"

    # --- SENSORY DETAIL DENSITY ---
    if prose_depth_results:
        md += "---\n## 🌿 Sensory Detail Density\n\n"
        md += "| Section | Sight | Sound | Smell | Touch | Taste | Immersion |\n"
        md += "|---------|-------|-------|-------|-------|-------|----------|\n"
        for idx in sorted(prose_depth_results):
            sd = prose_depth_results[idx].get("sensory_density", {})
            md += (
                f"| Section {idx + 1} "
                f"| {sd.get('sight_score', 0)}/100 "
                f"| {sd.get('sound_score', 0)}/100 "
                f"| {sd.get('smell_score', 0)}/100 "
                f"| {sd.get('touch_score', 0)}/100 "
                f"| {sd.get('taste_score', 0)}/100 "
                f"| {sd.get('immersion_score', 0)}/100 |\n"
            )
        md += "\n"
        # Chronic blind spots
        sense_keys = ["sight", "sound", "smell", "touch", "taste"]
        n_sections = len(prose_depth_results)
        chronic = [
            sense for sense in sense_keys
            if sum(1 for r in prose_depth_results.values() if r.get("sensory_density", {}).get(f"{sense}_score", 0) < 20) >= (n_sections / 2)
        ]
        if chronic:
            md += f"**⚠️ Chronic Blind Spots:** {', '.join(s.title() for s in chronic)}\n\n"
        # Strongest passages
        md += "**Strongest Sensory Passages:**\n"
        for idx in sorted(prose_depth_results):
            sd = prose_depth_results[idx].get("sensory_density", {})
            sp = sd.get("strongest_passage", "")
            if sp:
                md += f'- Section {idx + 1}: "{sp}"\n'
        md += "\n"

    # --- READABILITY & CLARITY ---
    if prose_depth_results:
        md += "---\n## 📖 Readability & Clarity\n\n"
        md += "| Section | Sentence Complexity | Clarity | Jargon/Opacity | Composite |\n"
        md += "|---------|--------------------|---------|--------------|-----------|\n"
        weakest_rb_idx = min(prose_depth_results, key=lambda i: prose_depth_results[i].get("readability", {}).get("composite_score", 100))  # type: ignore[arg-type]
        for idx in sorted(prose_depth_results):
            rb = prose_depth_results[idx].get("readability", {})
            md += (
                f"| Section {idx + 1} "
                f"| {rb.get('sentence_complexity_score', {}).get('score', 0)}/100 "
                f"| {rb.get('clarity_score', {}).get('score', 0)}/100 "
                f"| {rb.get('jargon_opacity_score', {}).get('score', 0)}/100 "
                f"| {rb.get('composite_score', 0)}/100 |\n"
            )
        md += "\n"
        weakest_rb = prose_depth_results[weakest_rb_idx].get("readability", {})
        md += f"### Lowest Readability — Section {weakest_rb_idx + 1} (Composite: {weakest_rb.get('composite_score', 0)}/100)\n\n"
        for sub_key, sub_label in [("sentence_complexity_score", "Sentence Complexity"), ("clarity_score", "Clarity"), ("jargon_opacity_score", "Jargon/Opacity")]:
            sub = weakest_rb.get(sub_key, {})
            md += f"**{sub_label} ({sub.get('score', 0)}/100):** {sub.get('analysis', '')}\n"
            md += f"- *Tip:* {sub.get('actionable_advice', '')}\n"
        opacity_examples = weakest_rb.get("opacity_examples", [])
        if opacity_examples:
            md += "\n**Opacity Examples:**\n"
            for ex in opacity_examples:
                md += f'- "{ex}"\n'
        md += "\n"

    md += "---\n## Detailed Chunk Breakdown\n\n"

    for i, result in enumerate(all_results):
        md += f"### Section {i+1}\n"
        for pillar in PILLAR_KEYS:
            data = pillar_data(result, pillar)
            md += f"**{format_pillar_label(pillar)} ({data.get('score', 0)}/100):**\n"
            md += f"> *Analysis:* {data.get('analysis', '')}\n>\n"
            md += f"> *Actionable Tip:* {data.get('actionable_advice', '')}\n\n"
        md += "---\n"
    return md


def generate_checklist_report(
    all_results: list[CritiqueResult],
    scenes: list[SceneInfo] | None = None,
    readiness_checklist: list[ChapterReadinessCheck] | None = None,
) -> str:
    """Generates a flat actionable-advice checklist, skipping scores and analysis."""
    readiness_by_index = {c["scene_index"]: c for c in (readiness_checklist or [])}
    md = "# Critique-Forge Action Checklist\n\n"
    for i, result in enumerate(all_results):
        heading = None
        if scenes and i < len(scenes):
            heading = scenes[i].get("heading")
        md += f"## {heading if heading else f'Section {i + 1}'}\n"
        readiness = readiness_by_index.get(i)
        if readiness is not None:
            status = "✅ Ready to post" if readiness["overall_ready"] else "⚠️ Not ready to post"
            md += f"- {status}\n"
        for pillar in PILLAR_KEYS:
            advice = pillar_data(result, pillar).get("actionable_advice", "").strip()
            if advice:
                md += f"- [ ] {format_pillar_label(pillar)}: {advice}\n"
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


def generate_title_blurb_report(result) -> str:
    """Generates a short report for the Title / Blurb / Tag A-B suggestions."""
    md = "# Critique-Forge: Title / Blurb / Tag A-B Suggestions\n\n"
    md += "## Title Options\n\n"
    for i, option in enumerate(result.get("title_options", []), start=1):
        md += f"**Option {chr(64 + i)}:** {option.get('title', '')}\n"
        md += f"> *Why it works:* {option.get('rationale', '')}\n\n"
    md += "## Blurb Options\n\n"
    for i, option in enumerate(result.get("blurb_options", []), start=1):
        md += f"### Option {chr(64 + i)}\n\n{option.get('blurb', '')}\n\n"
        md += f"> *Angle:* {option.get('rationale', '')}\n\n"
    tags = result.get("suggested_tags", [])
    if tags:
        md += "## Suggested Tags\n\n"
        md += ", ".join(tags) + "\n\n"
    md += f"## Why This Matters\n\n> {result.get('discoverability_note', '')}\n"
    return md


def generate_retention_sim_report(result: RetentionSimResult) -> str:
    """Generates a short report for the Chapter One Retention Simulator."""
    md = "# Critique-Forge: Chapter One Retention Simulator\n\n"
    verdict = "✅ **This chapter would earn a 'Next Chapter' click.**" if result.get("would_click_next") else "❌ **This chapter would be abandoned by a platform reader.**"
    md += f"**Verdict:** {verdict}\n\n"
    for pillar, label in [
        ("platform_hook", "Platform Hook (Genre/Trope Signal)"),
        ("protagonist_pull", "Protagonist Pull"),
        ("pacing_first_page", "Pacing — First Chapter"),
    ]:
        data = result.get(pillar, {})
        md += f"## {label} ({data.get('score', 0)}/100)\n"
        md += f"> *Analysis:* {data.get('analysis', '')}\n>\n"
        md += f"> *Actionable Tip:* {data.get('actionable_advice', '')}\n\n"
    notes = result.get("platform_reader_notes", [])
    if notes:
        md += "## Platform Reader Notes\n\n"
        for note in notes:
            md += f"- {note}\n"
        md += "\n"
    return md
