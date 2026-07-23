from typing import TypedDict, cast

from src.ai_client import CritiqueResult, CharacterData, PillarData, HookCritiqueResult, QueryLetterResult, CliffhangerResult
from src.structure import (
    SceneInfo, BeatMatch, PacingFlag, ChapterLengthFlag, PlatformPacingFlag,
    PLATFORM_PACING_RATIONALE,
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
