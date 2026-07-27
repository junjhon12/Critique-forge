# Pillar 1 — Engagement & Reader Retention Features Plan

## Top-Level Overview

Add four new engagement-focused features to Critique-Forge's Web Novel track:

1. **Arc Health Dashboard** — An arc-level emotional tension curve across all chapters, with sagging-middle and escalation-plateau detection.
2. **Reader Addiction Score** — A composite per-chapter score combining cliffhanger strength, chapter-opening hook pull, and mid-chapter tension.
3. **Chapter One Retention Simulator** — A web-reader-first-click simulation (mirrors "Read Like an Agent" but tuned for platform readers, not literary agents).
4. **Trope Radar** — Detects web fiction tropes present in the manuscript and evaluates whether each is used freshly or as a cliché.

All four features are additive — they do not alter existing analysis paths. They are only shown when `writing_for == "Web Novel / Serial"`.

**Files touched:**
- `src/ai_client.py` — New TypedDicts + new `analyze_*` functions for each feature
- `src/structure.py` — Arc tension aggregation helper (Arc Health Dashboard)
- `src/views.py` — New UI sections in the Full Manuscript dashboard + a new sidebar mode for Chapter One Retention Simulator
- `src/reports.py` — New sections added to `generate_markdown_report()` and new standalone report generators

---

## Sub-Task 1 — Reader Addiction Score

**Status:** [x] done

### Intent
The existing cliffhanger score only evaluates the last ~250 words of a chapter. Reader addiction is driven by three moments: the opening hook that pulls you *into* a chapter, mid-chapter tension that keeps you reading, and the closing cliffhanger that pulls you to the next. This sub-task builds a composite "Reader Addiction Score" per chapter from all three signals.

### Expected Outcomes
- Each chapter in the Full Manuscript dashboard shows a **Reader Addiction Score** (0–100) alongside its cliffhanger score.
- The score is broken into three sub-scores: Opening Hook (first ~200 words), Mid-Chapter Tension (middle ~50% of chapter), Closing Cliffhanger (existing `cliffhanger_strength`).
- A trend chart shows Reader Addiction Score across all chapters.
- The score is included in the downloadable Markdown report.

### Todo List
1. **`src/ai_client.py`** — Add `AddictionScoreResult` TypedDict with fields: `opening_hook` (PillarData), `mid_tension` (PillarData), `closing_cliffhanger` (PillarData), `composite_score` (int), `would_binge_read` (bool).
2. **`src/ai_client.py`** — Add `ADDICTION_SCORE_JSON_SCHEMA` string and `ADDICTION_SYSTEM_PROMPT` string (persona: a binge-reading platform user, not a literary agent).
3. **`src/ai_client.py`** — Add `analyze_addiction_score(chapter_text, genre) -> AddictionScoreResult` following the existing `analyze_*` pattern (system prompt + genre guidance + JSON schema → `_call_groq()`).
4. **`src/views.py`** — After the cliffhanger scoring loop (around line 379), add a second loop that calls `analyze_addiction_score()` per chapter using the full scene text (not just the ending). Cache results in `st.session_state["addiction_results"]`.
5. **`src/views.py`** — In the Structural Overlay section (after the cliffhanger strength table, around line 640), add a new `st.expander("🔥 Reader Addiction Score")` section that renders: per-chapter sub-scores table + composite score + a `st.line_chart` of composite scores across chapters.
6. **`src/reports.py`** — Add addiction score section to `generate_markdown_report()`: composite scores table + sub-score breakdown per chapter.

### Relevant Context
- Existing cliffhanger loop: `src/views.py` lines 360–379 — mirrors this pattern.
- Existing cliffhanger render: `src/views.py` lines 617–670 — addiction score section goes directly after this.
- `_call_groq()` pattern: `src/ai_client.py` lines 317–342.
- `CliffhangerResult` TypedDict: reference for structuring `AddictionScoreResult`.

---

## Sub-Task 2 — Arc Health Dashboard

**Status:** [x] done

### Intent
All existing tension/pacing analysis operates at the scene/chapter level. The Arc Health Dashboard aggregates chapter-level scores across the *entire manuscript* to plot an emotional tension curve. It detects "sagging middles" (a stretch of low-tension chapters in chapters 30–70% of the manuscript) and "escalation plateaus" (three or more consecutive chapters with flat/declining tension after the midpoint).

### Expected Outcomes
- A new "📊 Arc Health Dashboard" section in the Full Manuscript dashboard (Web Novel only).
- A line chart of emotional tension across chapters (derived from composite addiction scores or, if addiction score not run, from the average `conflict_and_stakes` pillar scores already collected).
- Flags for detected sagging middles and escalation plateaus shown as annotated regions on the chart or as a warning list.
- Included in the downloadable Markdown report.

### Todo List
1. **`src/structure.py`** — Add `build_arc_tension_curve(chapter_scores: list[float]) -> list[float]` — applies a 3-point rolling average to smooth the raw per-chapter scores into a tension curve.
2. **`src/structure.py`** — Add `ArcHealthFlag` TypedDict: `flag_type` ("sagging_middle" | "escalation_plateau"), `start_chapter`, `end_chapter`, `description`.
3. **`src/structure.py`** — Add `detect_arc_health_issues(tension_curve: list[float]) -> list[ArcHealthFlag]`:
   - Sagging middle: chapters in the 30–70% range whose rolling-average tension is below the manuscript mean by more than 1 standard deviation.
   - Escalation plateau: 3+ consecutive chapters post-midpoint with tension change ≤ 0 (flat or declining).
4. **`src/views.py`** — After Reader Addiction Score section (Sub-Task 1), add a new `st.expander("📊 Arc Health Dashboard")`. Build the tension curve from addiction composite scores if available, else fall back to per-chapter `conflict_and_stakes` scores. Render `st.line_chart` + a table of `ArcHealthFlag` items with chapter ranges and descriptions.
5. **`src/reports.py`** — Add Arc Health section to `generate_markdown_report()`: tension curve table + arc flags with descriptions.

### Relevant Context
- Per-chapter `conflict_and_stakes` scores are already accumulated in `section_scores` during the main LLM loop (`src/views.py` lines 294–359).
- `analyze_chapter_length_consistency()` in `src/structure.py` (lines 370–400) uses a similar z-score/mean approach — mirror this pattern for sagging-middle detection.
- The pacing line chart in `src/views.py` (lines 425–450) is the reference for rendering the tension curve chart.

---

## Sub-Task 3 — Chapter One Retention Simulator

**Status:** [x] done

### Intent
"Read Like an Agent" is hidden in the Web Novel track because it asks the wrong questions (literary agent conventions). Web platform readers decide to click "Next Chapter" within the first few paragraphs based on completely different signals: familiar tropes, fast pacing, an immediately interesting protagonist voice, and a clear genre hook. This sub-task adds a parallel mode tuned for platform readers.

### Expected Outcomes
- A new **"Chapter One Retention Simulator"** option in the Web Novel sidebar analysis mode selector (alongside "Full Manuscript").
- The user pastes or uploads their first chapter.
- The AI scores it on three pillars: `platform_hook` (genre recognition + trope signal), `protagonist_pull` (is the MC immediately interesting?), `pacing_first_page` (does anything happen fast enough for a serial reader?).
- Output shows: scores with progress bars + a `would_click_next` boolean verdict + a `platform_reader_notes` list of specific line-level observations + a download button for the report.

### Todo List
1. **`src/ai_client.py`** — Add `RetentionSimResult` TypedDict: `platform_hook` (PillarData), `protagonist_pull` (PillarData), `pacing_first_page` (PillarData), `would_click_next` (bool), `platform_reader_notes` (list[str]).
2. **`src/ai_client.py`** — Add `RETENTION_SIM_JSON_SCHEMA` and `RETENTION_SIM_SYSTEM_PROMPT` (persona: an impatient web novel reader who has 50 other novels in their reading list, making a snap decision in 2 minutes).
3. **`src/ai_client.py`** — Add `analyze_retention_sim(chapter_text, genre) -> RetentionSimResult` following the existing `analyze_*` pattern.
4. **`src/reports.py`** — Add `generate_retention_sim_report(result: RetentionSimResult) -> str` — mirrors the structure of `generate_hook_report()`.
5. **`src/views.py`** — Add `render_retention_sim_mode()` function modeled after `render_agent_read_mode()` (lines 82–163):
   - File upload or text area for first chapter.
   - Calls `analyze_retention_sim()`.
   - Renders verdict badge (`would_click_next`), three pillars with progress bars, and `platform_reader_notes` as a bulleted list.
   - Download button calling `generate_retention_sim_report()`.
6. **`src/views.py`** / **`app.py`** — Add "Chapter One Retention Simulator" to the Web Novel analysis mode selector in the sidebar. Wire to `render_retention_sim_mode()`.

### Relevant Context
- `render_agent_read_mode()`: `src/views.py` lines 82–163 — direct structural model for this new mode.
- `analyze_hook()` + `HookCritiqueResult`: `src/ai_client.py` — reference TypedDict and function pattern.
- `generate_hook_report()`: `src/reports.py` lines 254–273 — direct model for `generate_retention_sim_report()`.
- Sidebar mode selector lives in `app.py`; the Web Novel track currently shows only "Full Manuscript" — the new mode is added here.

---

## Sub-Task 4 — Trope Radar

**Status:** [x] done

### Intent
Web fiction lives and dies by tropes. Readers choose novels by trope signals; a story that hits familiar tropes but with a fresh twist outperforms one that ignores or unknowingly clunks them. The Trope Radar detects which web fiction tropes are present in the manuscript and evaluates whether each is executed freshly or as an overused cliché, giving the writer a clear picture of their story's trope DNA.

### Expected Outcomes
- A new "🎯 Trope Radar" section in the Full Manuscript dashboard (Web Novel only), rendered after the Arc Health Dashboard section.
- Lists detected tropes (e.g., isekai truck-kun, system awakening, reincarnation, dungeon diving, villain protagonist, etc.) each with: `trope_name`, `freshness_verdict` ("Fresh Twist" | "Standard Execution" | "Cliché Risk"), `evidence` (a short quote or scene reference), and `suggestion` (if cliché risk).
- A summary badge showing trope DNA (e.g., "Isekai + System Awakening + Villain Protagonist").
- Included in the downloadable Markdown report.

### Todo List
1. **`src/ai_client.py`** — Add `TropeEntry` TypedDict: `trope_name` (str), `freshness_verdict` (str), `evidence` (str), `suggestion` (str).
2. **`src/ai_client.py`** — Add `TropeRadarResult` TypedDict: `detected_tropes` (list[TropeEntry]), `trope_dna_summary` (str).
3. **`src/ai_client.py`** — Add `TROPE_RADAR_JSON_SCHEMA`, `TROPE_RADAR_SYSTEM_PROMPT` (persona: an experienced web fiction editor who has read 10,000+ web novels and knows every trope cold). The prompt should list common web fiction trope categories to scan for and instruct the model to only report tropes that are actually evidenced in the text.
4. **`src/ai_client.py`** — Add `analyze_trope_radar(manuscript_excerpt, genre) -> TropeRadarResult`. Use the first ~1,500 words of the manuscript (enough to detect setup tropes) or the full first chapter if chapters are separated. Follow the existing `analyze_*` pattern.
5. **`src/views.py`** — Add a new `st.expander("🎯 Trope Radar")` section after the Arc Health Dashboard. Render: `trope_dna_summary` as a styled badge/callout, then a table of detected tropes with columns `Trope`, `Verdict`, `Evidence`, `Suggestion`. Color-code rows by freshness_verdict (fresh = green, standard = yellow, cliché = red using st.markdown with emoji badges).
6. **`src/reports.py`** — Add Trope Radar section to `generate_markdown_report()`: DNA summary + trope table with freshness verdicts and suggestions.

### Relevant Context
- `analyze_title_blurb_tags()` in `src/ai_client.py` (lines 368–371) + its JSON schema (around lines 270–314) — closest structural model for a list-of-objects result.
- The Title/Blurb/Tag section in `src/views.py` (lines 809–868) shows how to render A-B card-style results — simpler table approach used here instead.
- `TitleBlurbTagResult` and `BibleExtractionResult` show the pattern for `list[TypedDict]` return types.
- Trope Radar runs once on the full manuscript (not per-chunk), so it fits after the main LLM loop without adding to the per-chunk cost.

---

## Implementation Order

Sub-tasks should be implemented in this order:

1. **Sub-Task 1** (Reader Addiction Score) — establishes the per-chapter composite score that Sub-Task 2 depends on.
2. **Sub-Task 2** (Arc Health Dashboard) — consumes the addiction scores built in Sub-Task 1.
3. **Sub-Task 3** (Chapter One Retention Simulator) — fully independent; can be done in any order but benefits from seeing the AI pattern used in Sub-Tasks 1–2.
4. **Sub-Task 4** (Trope Radar) — fully independent; runs once on full manuscript text already available in session state.
