# Pillar 3 — Prose & Craft Depth Plan

## Top-Level Overview

Add four new prose-focused analysis features to Critique-Forge. Like Pillar 2, all four features are available for **all writing formats** (Web Novel and Traditional Publishing). They are additive and do not alter existing analysis paths.

1. **Prose Elegance Audit** — Per-section scoring of sentence rhythm variety, passive-voice density, adverb density, and a composite elegance score with the weakest passages surfaced.
2. **Show-Don't-Tell Deep-Dive** — Per-section compliance score (% told vs. shown), category breakdown (emotion-telling / action-telling / thought-telling), and worst offending passages. Extends the existing Prose Sniper without replacing it.
3. **Sensory Detail Density** — Per-section coverage across the five senses (sight, sound, smell, touch, taste), an immersion score, and flags for sections with sensory blind spots.
4. **Readability & Clarity** — Per-section sentence complexity, clarity score, jargon/opacity flags, and an overall readability composite.

### Efficiency Design — Single Combined Call Per Section

Pillars 1 and 2 already add ~5 per-section LLM loops after the main critique loop. On a 20-chapter manuscript that is already ~100 sequential API calls. Naively adding 4 more Pillar 3 loops would push this to ~180 calls, hitting Groq rate limits and degrading performance significantly.

**All four Pillar 3 features read the same section text to ask questions about the same dimension — how the prose reads.** They can be answered in one LLM pass per section with a single combined prompt and schema, returning a unified `ProseDepthResult` object. This reduces 4 × N calls to **1 × N calls** at no loss in output quality.

The four analyses are still rendered as four separate expanders in the UI — the combined result is simply unpacked — so the writer experience is unchanged.

**Files touched:**
- `src/ai_client.py` — Combined `ProseDepthResult` TypedDict (containing four sub-TypedDicts) + `PROSE_DEPTH_JSON_SCHEMA` + `PROSE_DEPTH_SYSTEM_PROMPT` + `analyze_prose_depth()` function.
- `src/views.py` — One new per-section loop + four new `st.expander` sections in the Full Manuscript dashboard (all-format, placed **after the Protagonist Agency Deep-Dive section**, before the download buttons).
- `src/reports.py` — Four new sections in `generate_markdown_report()`.

---

## Sub-Task 1 — Combined TypedDicts, Schema & Prompt (`src/ai_client.py`) ✅

**Status:** [x] done

### Intent
Define all data structures and the single LLM function that powers all four Pillar 3 expanders. Doing this in one sub-task ensures the schema, prompt, and TypedDicts are designed together as a coherent whole before any UI work begins.

### Expected Outcomes
- Five new TypedDicts in `src/ai_client.py`: `SDTViolation`, `ProseEleganceData`, `ShowDontTellData`, `SensoryDensityData`, `ReadabilityData`, and the top-level `ProseDepthResult`.
- `PROSE_DEPTH_SYSTEM_PROMPT` string — a single combined persona prompt covering all four lenses.
- `PROSE_DEPTH_JSON_SCHEMA` string — a single JSON schema returning all four sub-objects.
- `analyze_prose_depth(section_text, genre) -> ProseDepthResult` function following the existing `analyze_*` pattern.

### Todo List
1. **`src/ai_client.py`** — Add `SDTViolation` TypedDict: `category` (str — `"emotion_telling"` | `"action_telling"` | `"thought_telling"`), `passage` (str), `severity` (int 1–3).
2. **`src/ai_client.py`** — Add `ProseEleganceData` TypedDict: `rhythm_variety` (PillarData), `passive_voice_score` (PillarData), `adverb_density_score` (PillarData), `composite_score` (int), `weak_passages` (list[str]).
3. **`src/ai_client.py`** — Add `ShowDontTellData` TypedDict: `compliance_score` (int 0–100), `told_percentage` (int 0–100), `emotion_tells` (int), `action_tells` (int), `thought_tells` (int), `worst_violations` (list[SDTViolation]).
4. **`src/ai_client.py`** — Add `SensoryDensityData` TypedDict: `sight_score` (int 0–100), `sound_score` (int 0–100), `smell_score` (int 0–100), `touch_score` (int 0–100), `taste_score` (int 0–100), `immersion_score` (int 0–100), `blind_spot_senses` (list[str]), `strongest_passage` (str).
5. **`src/ai_client.py`** — Add `ReadabilityData` TypedDict: `sentence_complexity_score` (PillarData), `clarity_score` (PillarData), `jargon_opacity_score` (PillarData), `composite_score` (int), `opacity_examples` (list[str]).
6. **`src/ai_client.py`** — Add `ProseDepthResult` TypedDict: `prose_elegance` (ProseEleganceData), `show_dont_tell` (ShowDontTellData), `sensory_density` (SensoryDensityData), `readability` (ReadabilityData).
7. **`src/ai_client.py`** — Add `PROSE_DEPTH_SYSTEM_PROMPT`. Persona: a senior line editor and prose coach who has spent 20 years working across literary and commercial fiction. The prompt should cover four lenses simultaneously and make clear that the model should evaluate all four in a single reading pass. Lens definitions:
   - *Elegance*: rhythm variety (sentence-length variation and cadence), passive-voice density (does it drain scene energy?), adverb density (are adverbs doing work stronger verbs should?). Higher scores = more elegant prose.
   - *Show-Don't-Tell*: compliance_score is how fully the section shows rather than tells (100 = fully shown); told_percentage is the estimated proportion of prose that tells; violations break down into emotion-telling (stating feelings), action-telling (narrating actions that could be dramatised), and thought-telling (reporting thoughts rather than enacting them). Flag the three worst offending passages with a severity 1–3.
   - *Sensory Density*: score each of the five senses (0–100) based on how many distinct, specific sensory details are present (not generic or decorative); flag any sense below 20 as a blind spot; identify the strongest single passage.
   - *Readability*: sentence_complexity (structural density — nested clauses, run-ons, inverted syntax), clarity (precision of meaning without ambiguity), jargon_opacity (density of domain-specific or unnecessarily obscure word choices). Higher scores = more readable. Extract the worst opacity examples as short quoted phrases.
8. **`src/ai_client.py`** — Add `PROSE_DEPTH_JSON_SCHEMA` covering the full combined output structure (all four sub-objects with all fields per the TypedDicts above).
9. **`src/ai_client.py`** — Add `analyze_prose_depth(section_text: str, genre: str = "None / General") -> ProseDepthResult` following the existing `analyze_*` pattern: build system prompt from `PROSE_DEPTH_SYSTEM_PROMPT` + genre context, call `_call_groq(system_prompt, section_text, PROSE_DEPTH_JSON_SCHEMA)`, return result.

### Relevant Context
- `PillarData` TypedDict (`src/ai_client.py` line 7) — building block for PillarData sub-scores inside `ProseEleganceData` and `ReadabilityData`.
- `_call_groq()` function (`src/ai_client.py`) — the single underlying API call wrapper used by all `analyze_*` functions; same pattern applies here.
- `analyze_dialogue_quality()` — closest structural model: single function, system prompt + JSON schema, returns a composite TypedDict with three `PillarData` sub-scores + composite int + list[str].
- `ADDICTION_SCORE_JSON_SCHEMA` (lines 368–397) — model for a multi-section JSON schema with nested objects; `PROSE_DEPTH_JSON_SCHEMA` will be larger but follows the same structure.
- Genre context injection pattern: existing `analyze_*` functions prepend genre guidance to the system prompt — mirror this for `analyze_prose_depth`.

---

## Sub-Task 2 — Per-Section Loop & Caching (`src/views.py`) ✅

**Status:** [x] done

### Intent
Wire the `analyze_prose_depth()` call into the analysis pipeline as a single per-section loop (not four separate loops), cache each section's result with a `"ProseDepth"` cache key, and persist the full dict to session state so the four rendering sub-tasks can read from it independently.

### Expected Outcomes
- A single new loop after the Protagonist Agency Deep-Dive loop (around line 503) that iterates over `scenes`, calls `analyze_prose_depth()` once per section, and stores results in `st.session_state["prose_depth_results"]` (a `dict[int, ProseDepthResult]` keyed by scene index).
- The loop uses the existing `_cache_key(section_text, "ProseDepth", selected_genre)` pattern for caching — a cache hit skips the API call entirely on subsequent runs.
- Progress bar text shows `"Analysing prose depth for section {i+1} of {N}..."` during the loop.

### Todo List
1. **`src/views.py`** — Add the necessary import for `ProseDepthResult` and `analyze_prose_depth` at the top of the file alongside the existing Pillar 2 imports.
2. **`src/views.py`** — After the Protagonist Agency Deep-Dive loop (after line ~503, before the Arc Health block), add a new per-section loop following the identical pattern of the Dialogue Quality loop (lines 413–432):
   - Initialise `prose_depth_results: dict[int, ProseDepthResult] = {}`.
   - Iterate over `scenes`, extract section text using `words_for_prose_depth` word list.
   - Build `prose_depth_key = _cache_key(section_text, "ProseDepth", selected_genre)`.
   - Cache-check → call `analyze_prose_depth()` → save cache → store in dict.
3. **`src/views.py`** — Add `st.session_state["prose_depth_results"] = prose_depth_results` alongside the other `st.session_state` assignments (around line 568).

### Relevant Context
- Dialogue Quality Analysis loop (`src/views.py` lines 413–432) — direct template; copy the exact structure, change the function call, cache key prefix, and variable names.
- Session state assignments block (`src/views.py` ~lines 568–578) — add the new key here so results persist for the rendering code.
- `_cache_key()` is already imported/available in this scope.

---

## Sub-Task 3 — Prose Elegance & Show-Don't-Tell Expanders (`src/views.py`) ✅

**Status:** [x] done

### Intent
Render the first two Pillar 3 expanders using the `prose_depth_results` cached in Sub-Task 2. These two share the same structural pattern (composite score table + trend chart + lowest-section drill-down with a list of flagged strings).

### Expected Outcomes
- `st.expander("✍️ Prose Elegance Audit")` — per-section sub-score table (Rhythm Variety, Passive Voice, Adverb Density, Composite) + `st.line_chart` of composite scores + lowest-scoring section drill-down showing `weak_passages` as a bulleted list.
- `st.expander("🔍 Show-Don't-Tell Deep-Dive")` — per-section compliance score + emotion/action/thought tell counts table + `st.line_chart` of compliance scores + "Worst Violations" drill-down with passages color-coded by category (emotion = blue badge, action = orange badge, thought = purple badge) and severity stars.
- Both expanders placed immediately after the Protagonist Agency Deep-Dive expander.

### Todo List
1. **`src/views.py`** — After the Protagonist Agency Deep-Dive expander (around line 1380), add `st.expander("✍️ Prose Elegance Audit")`:
   - Load `prose_depth_results` from `st.session_state`.
   - Build a table: one row per section, columns = Section, Rhythm Variety score, Passive Voice score, Adverb Density score, Composite. Identify the lowest composite row.
   - Render `st.line_chart` of composite scores across sections.
   - Render an expandable "Weakest Section" sub-section with the `weak_passages` list from the lowest composite section as a bulleted markdown list.
2. **`src/views.py`** — Immediately after the Prose Elegance expander, add `st.expander("🔍 Show-Don't-Tell Deep-Dive")`:
   - Build a table: one row per section, columns = Section, Compliance Score, Told %, Emotion Tells, Action Tells, Thought Tells.
   - Render `st.line_chart` of compliance scores.
   - Render an expandable "Worst Violations" sub-section: for each `SDTViolation` in the lowest-scoring section's `worst_violations`, render a styled row with a category badge (use emoji prefix: 💙 emotion, 🟠 action, 💜 thought) and severity indicator (★ / ★★ / ★★★).

### Relevant Context
- Dialogue Quality Analysis expander (`src/views.py` ~lines 1181–1249) — direct UI model for the composite score table + trend chart + lowest-section drill-down pattern.
- Protagonist Agency Deep-Dive expander (`src/views.py` ~lines 1331–1380) — determines the exact insertion point for both new expanders.
- Trope Radar expander (`src/views.py` ~lines 972–1005) — model for rendering a list of objects with badge-style verdict columns.

---

## Sub-Task 4 — Sensory Detail Density & Readability Expanders (`src/views.py`) ✅

**Status:** [x] done

### Intent
Render the final two Pillar 3 expanders. Sensory Detail Density introduces a five-column score heatmap and a chronic blind-spot callout computed client-side over the cached results. Readability mirrors the Prose Elegance structure.

### Expected Outcomes
- `st.expander("🌿 Sensory Detail Density")` — per-section sense-coverage heatmap table (Sight / Sound / Smell / Touch / Taste / Immersion Score) with cells color-coded by score range + trend chart of immersion scores + a "Chronic Blind Spots" callout listing senses that scored below 20 in 50%+ of sections.
- `st.expander("📖 Readability & Clarity")` — per-section sub-score table (Sentence Complexity, Clarity, Jargon/Opacity, Composite) + trend chart + lowest-scoring section drill-down with `opacity_examples`.
- Both placed immediately after the Show-Don't-Tell expander (Sub-Task 3).

### Todo List
1. **`src/views.py`** — After the Show-Don't-Tell expander, add `st.expander("🌿 Sensory Detail Density")`:
   - Build per-section table: columns = Section, Sight, Sound, Smell, Touch, Taste, Immersion. Color-code cells by score range using `st.markdown` with emoji indicators (🟢 ≥ 60, 🟡 30–59, 🔴 < 30).
   - Render `st.line_chart` of immersion scores.
   - Compute chronic blind spots inline: for each sense, count how many sections have that sense's score < 20. If count ≥ 50% of sections, add sense to `chronic_blind_spots` list. Render as `st.warning()` callout if any chronic blind spots exist.
2. **`src/views.py`** — After the Sensory Detail Density expander, add `st.expander("📖 Readability & Clarity")`:
   - Build per-section table: columns = Section, Sentence Complexity, Clarity, Jargon/Opacity, Composite.
   - Render `st.line_chart` of composite scores.
   - Render expandable lowest-scoring section drill-down with `opacity_examples` as a bulleted list.

### Relevant Context
- Protagonist Agency Deep-Dive per-section table (`src/views.py` ~lines 1331–1380) — model for a multi-column int score table across sections.
- `detect_arc_health_issues()` in `src/structure.py` — reference for the "aggregate across sections to find a threshold condition" pattern, but the chronic blind-spot logic is simple enough to compute inline in views.py (no need for a structure.py helper).
- Prose Elegance expander (Sub-Task 3) — direct UI model for the Readability expander; structurally identical.
- `st.warning()` callout pattern — already used elsewhere in views.py for flagging structural issues; use the same approach for chronic blind spots.

---

## Sub-Task 5 — Report Sections (`src/reports.py`) ✅

**Status:** [x] done

### Intent
Add four new sections to `generate_markdown_report()` so all Pillar 3 features are included in the downloadable Markdown report. All four sections read from the same `prose_depth_results` dict.

### Expected Outcomes
- Four new sections in `generate_markdown_report()`, placed after the Protagonist Agency Deep-Dive section and before the download footer:
  - `## ✍️ Prose Elegance Audit` — composite score table + sub-scores per section + weak passages from the lowest-scoring section.
  - `## 🔍 Show-Don't-Tell Deep-Dive` — compliance score table with category counts per section + worst violations with category and severity.
  - `## 🌿 Sensory Detail Density` — per-sense score table + chronic blind spots callout + strongest passage per section.
  - `## 📖 Readability & Clarity` — composite score table + sub-scores per section + opacity examples from the lowest-scoring section.

### Todo List
1. **`src/reports.py`** — Identify the `generate_markdown_report()` function signature and the exact location of the Protagonist Agency Deep-Dive section (the current final feature section). Add the four new sections immediately after it.
2. **`src/reports.py`** — Add Prose Elegance Audit section: composite scores table (Section | Rhythm | Passive Voice | Adverb Density | Composite) + weak passages block from lowest-scoring section.
3. **`src/reports.py`** — Add Show-Don't-Tell Deep-Dive section: compliance score table (Section | Compliance Score | Told % | Emotion Tells | Action Tells | Thought Tells) + worst violations list (category, severity, passage).
4. **`src/reports.py`** — Add Sensory Detail Density section: sense table (Section | Sight | Sound | Smell | Touch | Taste | Immersion) + chronic blind spots callout (if any) + strongest passage per section.
5. **`src/reports.py`** — Add Readability & Clarity section: composite scores table (Section | Sentence Complexity | Clarity | Jargon/Opacity | Composite) + opacity examples from lowest-scoring section.

### Relevant Context
- Protagonist Agency Deep-Dive section in `generate_markdown_report()` (`src/reports.py`) — determines the exact insertion point.
- Dialogue Quality report section (`src/reports.py`) — direct model for a sub-score table + flagged-items block.
- `generate_markdown_report()` already receives `prose_depth_results` dict as a parameter (to be added alongside the other `analyze_*` result parameters).

---

## Implementation Order

Sub-tasks should be implemented in this order:

1. **Sub-Task 1** — TypedDicts, schema, prompt, and `analyze_prose_depth()`. All subsequent sub-tasks depend on this.
2. **Sub-Task 2** — The per-section loop and caching in `views.py`. Sub-Tasks 3–4 depend on the cached results.
3. **Sub-Task 3** — Prose Elegance + Show-Don't-Tell expanders. Establishes the UI insertion point for Sub-Task 4.
4. **Sub-Task 4** — Sensory Density + Readability expanders. Completes the UI.
5. **Sub-Task 5** — Report sections. Can be done last as it has no UI dependencies; only requires the TypedDicts from Sub-Task 1.
