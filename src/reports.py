from typing import TypedDict, cast

from src.ai_client import CritiqueResult, CharacterData, PillarData, HookCritiqueResult, QueryLetterResult
from src.structure import SceneInfo, BeatMatch, PacingFlag, ChapterLengthFlag
from src.style_audit import PovTenseFlag

PILLAR_KEYS: list[str] = ["agency", "conflict_and_stakes", "compelling_arcs", "tight_scene_structure"]


class SniperHit(TypedDict):
    section: int
    bad_quote: str
    rewritten_example: str


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
            data = pillar_data(result, pillar)
            md += f"**{format_pillar_label(pillar)} ({data.get('score', 0)}/100):**\n"
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
