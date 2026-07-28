# Pillar 2 — Character & Voice Depth Plan

## Top-Level Overview

Add four new character-focused analysis features to Critique-Forge. Unlike Pillar 1 (Web Novel-only), all four features are available for **all writing formats** (Web Novel and Traditional Publishing). They are additive and do not alter existing analysis paths.

1. **Dialogue Quality Analysis** — Per-section scoring of dialogue craft: character voice consistency, subtext vs. on-the-nose writing, and dialogue-to-prose ratio flags.
2. **Character Arc Continuity** — Tracks each named character's emotional state and motivation across chapters; surfaces stalled arcs and contradiction flags.
3. **Secondary Character Underutilization** — Detects named secondary characters who appear early but vanish or are reduced to props, with recommendations to deepen their function.
4. **Protagonist Agency Deep-Dive** — Per-section breakdown of *type* of agency (proactive choice vs. reactive response), decision-consequence clarity, and goal-driving-the-scene signal. Goes deeper than the existing broad `agency_and_conflict` pillar.

**Files touched:**
- `src/ai_client.py` — New TypedDicts + new `analyze_*` functions for each feature.
- `src/views.py` — New UI expander sections in the Full Manuscript dashboard (all-format, placed **after the Story Bible & Consistency Check section**, before the download buttons — works identically for both Web Novel and Traditional Publishing tracks).
- `src/reports.py` — New sections in `generate_markdown_report()`.

---

## Sub-Task 1 — Dialogue Quality Analysis

**Status:** [x] done

### Intent
The existing critique only evaluates show-don't-tell and prose sniper violations at the sentence level. Dialogue is one of the fastest signals readers use to evaluate a novel (voice, authenticity, subtext) but is currently unscored. This sub-task adds a per-section dialogue quality score covering three dimensions: character voice consistency, subtext vs. on-the-nose delivery, and dialogue-to-prose balance.

### Expected Outcomes
- Each analysed section in the Full Manuscript dashboard shows a **Dialogue Quality** score (0–100) with three sub-scores.
- A new `st.expander("💬 Dialogue Quality Analysis")` section renders: per-section sub-score table + a trend line chart + sections with lowest subtext score highlighted.
- Included in the downloadable Markdown report.

### Todo List
1. **`src/ai_client.py`** — Add `DialogueQualityResult` TypedDict with fields: `voice_consistency` (PillarData), `subtext_score` (PillarData), `dialogue_ratio_note` (str), `composite_score` (int), `flagged_lines` (list[str]).
2. **`src/ai_client.py`** — Add `DIALOGUE_QUALITY_JSON_SCHEMA` string and `DIALOGUE_QUALITY_SYSTEM_PROMPT` (persona: a dialogue coach and screenwriter who reads for authentic character voice and subtext; NOT a literary agent). The prompt should instruct the model to score voice consistency based on whether each character sounds distinct, subtext based on whether emotional content is implied vs. stated outright, and dialogue ratio based on the balance of dialogue to narration in the section.
3. **`src/ai_client.py`** — Add `analyze_dialogue_quality(section_text, genre) -> DialogueQualityResult` following the existing `analyze_*` pattern.
4. **`src/views.py`** — After the main per-section LLM critique loop (around line 294–359), add a second per-section loop that calls `analyze_dialogue_quality()` and caches results in `st.session_state["dialogue_quality_results"]`.
5. **`src/views.py`** — After the Structural Overlay section (or after Trope Radar if Web Novel), add a new `st.expander("💬 Dialogue Quality Analysis")` that renders: per-section sub-score table (Voice Consistency, Subtext Score, Dialogue Ratio Note, Composite), a `st.line_chart` of composite scores, and an expandable drill-down for the lowest-scoring section showing `flagged_lines`.
6. **`src/reports.py`** — Add a Dialogue Quality section to `generate_markdown_report()`: composite scores table + sub-score breakdown per section + flagged lines.

### Relevant Context
- Existing per-section analysis loop: `src/views.py` lines 294–359 — mirrors this pattern for the new loop.
- `AddictionScoreResult` (Pillar 1): direct structural model for a composite-score TypedDict with sub-score PillarData fields.
- `analyze_addiction_score()` loop in `src/views.py` (around line 379) — mirrors this caching pattern.
- Reader Addiction Score expander in `src/views.py` (lines 796–843) — direct UI model for the new expander.

---

## Sub-Task 2 — Character Arc Continuity ✅

**Status:** [ ] pending

### Intent
The existing Story Bible tracks character *attributes* (physical traits, current motivation) from each section independently, then detects contradictions in factual attributes (name/alias, eye colour, etc.). It does not track whether a character's *emotional state* or *motivation* is progressing coherently across chapters. This sub-task adds a cross-section arc continuity pass that identifies stalled arcs (character feels the same in chapter 10 as chapter 1) and arc reversals (unexplained or contradictory motivation jumps).

### Expected Outcomes
- A new `st.expander("🧬 Character Arc Continuity")` section in the Full Manuscript dashboard (all formats).
- For each major character (protagonist + any character appearing in 3+ sections), shows an arc timeline: a table of `section → emotional_state → core_goal → arc_note`.
- Flags stalled arcs (no meaningful change across 5+ consecutive sections) and arc reversals (motivation jumps without sufficient setup).
- Included in the downloadable Markdown report.

### Todo List
1. **`src/ai_client.py`** — Add `CharacterArcEntry` TypedDict: `character_name` (str), `emotional_state` (str), `core_goal` (str), `arc_note` (str — "progressing" | "stalled" | "reversal" | "resolved").
2. **`src/ai_client.py`** — Add `CharacterArcSnapshotResult` TypedDict: `characters` (list[CharacterArcEntry]), `section_index` (int).
3. **`src/ai_client.py`** — Add `CHARACTER_ARC_JSON_SCHEMA`, `CHARACTER_ARC_SYSTEM_PROMPT` (persona: a developmental editor who maps character psychology and transformation through a manuscript). Prompt instructs the model to extract, for each named character present in the section, their current emotional state and core goal as short phrases, plus an arc note that classifies whether their state has changed relative to the prior section context (provided in the user message).
4. **`src/ai_client.py`** — Add `analyze_character_arc_snapshot(section_text, genre, prior_states: dict[str, str]) -> CharacterArcSnapshotResult`. Pass a JSON-encoded `prior_states` dict (character → last known emotional state) in the user message so the model can judge change vs. stall.
5. **`src/views.py`** — After the main LLM loop, add a per-section loop that calls `analyze_character_arc_snapshot()`, passing the accumulated `prior_states` dict (updated after each section). Cache results in `st.session_state["arc_continuity_results"]`.
6. **`src/views.py`** — Add `st.expander("🧬 Character Arc Continuity")`: one sub-expander per major character (appearing in 3+ sections), showing a table of their arc progression across sections. Highlight rows with `arc_note == "stalled"` or `"reversal"` in amber/red.
7. **`src/reports.py`** — Add Character Arc Continuity section to `generate_markdown_report()`: per-character arc timeline table with stall/reversal flags.

### Relevant Context
- Existing Story Bible per-section extraction: `extract_bible_entities()` in `src/ai_client.py` (lines 511–513) — analogous per-section LLM pass.
- Story Bible consistency check section in `src/views.py` (lines 1036–1109) — UI pattern for character-grouped display.
- `BibleExtractionResult` TypedDict: `characters` as a list of `CharacterData` objects — structural reference for `CharacterArcSnapshotResult`.
- The `prior_states` accumulation pattern is analogous to how `consistency_check.py` merges entities across sections.

---

## Sub-Task 3 — Secondary Character Underutilization

**Status:** [ ] pending

### Intent
Writers routinely introduce secondary characters who never fulfil their narrative promise — they appear in early chapters with specific traits and roles but then become background furniture. This sub-task runs a single post-loop analysis pass (like Trope Radar) to identify named secondary characters whose presence fades after their introduction, and provides specific recommendations for deepening their function.

### Expected Outcomes
- A new `st.expander("👥 Secondary Character Underutilization")` section in the Full Manuscript dashboard.
- A list of flagged secondary characters with: `character_name`, `introduction_chapter`, `last_active_chapter`, `narrative_role` ("mentor" | "rival" | "love_interest" | "comic_relief" | "plot_device" | "other"), `utilization_verdict` ("well-used" | "underused" | "prop"), `suggestion`.
- A summary of characters whose role is "prop" or whose `last_active_chapter` is less than half the total chapter count.
- Included in the downloadable Markdown report.

### Todo List
1. **`src/ai_client.py`** — Add `SecondaryCharacterEntry` TypedDict: `character_name` (str), `introduction_chapter` (int), `last_active_chapter` (int), `narrative_role` (str), `utilization_verdict` (str), `suggestion` (str).
2. **`src/ai_client.py`** — Add `SecondaryCharUtilResult` TypedDict: `characters` (list[SecondaryCharacterEntry]), `overall_note` (str).
3. **`src/ai_client.py`** — Add `SECONDARY_CHAR_JSON_SCHEMA`, `SECONDARY_CHAR_SYSTEM_PROMPT` (persona: a structural editor who specialises in ensemble casts and identifies characters who are introduced with promise but never deliver on it). Instruct the model to ignore the protagonist(s) and focus on supporting cast.
4. **`src/ai_client.py`** — Add `analyze_secondary_char_util(manuscript_excerpt, genre, chapter_count: int) -> SecondaryCharUtilResult`. Use the first ~2,000 words + the last ~2,000 words of the manuscript (to capture introductions and final appearances). Pass `chapter_count` in the user message.
5. **`src/views.py`** — After the Character Arc Continuity section, add a single-call (not per-section) invocation of `analyze_secondary_char_util()` after the main loop. Cache in `st.session_state["secondary_char_util"]`.
6. **`src/views.py`** — Add `st.expander("👥 Secondary Character Underutilization")`: table of secondary characters with verdict color-coded (well-used = green, underused = amber, prop = red). Show `overall_note` as a callout.
7. **`src/reports.py`** — Add Secondary Character Underutilization section to `generate_markdown_report()`: character table + overall note.

### Relevant Context
- `analyze_trope_radar()` in `src/ai_client.py` (lines 528–531) — direct model for a single post-loop analysis call on a manuscript excerpt.
- Trope Radar UI section in `src/views.py` (lines 872–903) — direct model for the new expander pattern.
- `TropeEntry` / `TropeRadarResult` TypedDicts — structural model for `SecondaryCharacterEntry` / `SecondaryCharUtilResult`.
- Story Bible character accumulation in `src/views.py` (lines 1036–1109) already collects named characters; the accumulated `story_bible_entries` list can supply the chapter-range signal for `introduction_chapter` / `last_active_chapter`.

---

## Sub-Task 4 — Protagonist Agency Deep-Dive

**Status:** [ ] pending

### Intent
The existing `agency_and_conflict` pillar in `CritiqueResult` scores protagonist agency broadly per section. This new feature zooms in on the *type* of agency: whether the protagonist is making proactive choices that drive the plot, or passively reacting to events driven by others. It also evaluates whether each scene has a clear protagonist goal and whether decisions carry visible consequences. The goal is to help writers identify "passenger protagonist" scenes — sections where the protagonist is acted upon but never acts.

### Expected Outcomes
- A new `st.expander("🎯 Protagonist Agency Deep-Dive")` section in the Full Manuscript dashboard.
- Per-section breakdown: `proactive_score`, `reactive_score`, `goal_clarity_score`, `consequence_weight_score`, `agency_type_label` ("Fully Proactive" | "Mostly Proactive" | "Reactive" | "Passenger"), `key_observation` (one sentence).
- A trend chart showing the `agency_type_label` or a composite agency score across sections, with "Passenger" sections highlighted.
- Included in the downloadable Markdown report.

### Todo List
1. **`src/ai_client.py`** — Add `AgencyDeepDiveResult` TypedDict: `proactive_score` (int 0–100), `reactive_score` (int 0–100), `goal_clarity` (PillarData), `consequence_weight` (PillarData), `agency_type_label` (str), `key_observation` (str).
2. **`src/ai_client.py`** — Add `AGENCY_DEEP_DIVE_JSON_SCHEMA`, `AGENCY_DEEP_DIVE_SYSTEM_PROMPT` (persona: a story coach focused on protagonist agency and active storytelling, who reads each scene asking "is the protagonist the cause of events or the effect of them?"). The prompt should define the four agency type labels clearly.
3. **`src/ai_client.py`** — Add `analyze_agency_deep_dive(section_text, genre) -> AgencyDeepDiveResult` following the existing `analyze_*` pattern.
4. **`src/views.py`** — After the main per-section loop, add a second per-section loop that calls `analyze_agency_deep_dive()` and caches in `st.session_state["agency_deep_dive_results"]`.
5. **`src/views.py`** — Add `st.expander("🎯 Protagonist Agency Deep-Dive")`: per-section table (Scene, Proactive Score, Reactive Score, Goal Clarity, Consequence Weight, Agency Type) with "Passenger" rows highlighted in red. Add `st.line_chart` of composite proactive scores across sections.
6. **`src/reports.py`** — Add Protagonist Agency Deep-Dive section to `generate_markdown_report()`: per-section table + passenger section list + key observations.

### Relevant Context
- Existing `agency_and_conflict` PillarData in `CritiqueResult`: reference for what the current scoring covers (so the new feature clearly *extends* rather than duplicates).
- `AddictionScoreResult` — structural model for a multi-score TypedDict with a composite label.
- Reader Addiction Score loop and expander (Pillar 1, `src/views.py` ~lines 379–843) — mirrors the pattern for the new per-section loop and expander.

---

## Implementation Order

Sub-tasks should be implemented in this order:

1. **Sub-Task 1** (Dialogue Quality Analysis) — independent; establishes the per-section loop pattern used by Sub-Task 4.
2. **Sub-Task 2** (Character Arc Continuity) — depends on having a working per-section loop; introduces the novel `prior_states` accumulation pattern.
3. **Sub-Task 3** (Secondary Character Underutilization) — single post-loop call; independent but benefits from the Story Bible context already cached by the main loop.
4. **Sub-Task 4** (Protagonist Agency Deep-Dive) — per-section loop; independent but placed last so the Protagonist Agency expander appears after the Character Arc and Secondary Character sections in the UI.
