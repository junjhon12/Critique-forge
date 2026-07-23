# Critique-Forge

Critique-Forge is a Streamlit app that acts as an AI developmental editor for fiction manuscripts. It uses Groq-hosted LLMs to critique full manuscripts, query letters/synopses, and first pages, and adds structural/style checks (pacing, beat-sheet mapping, POV/tense consistency, filter words) on top of the AI feedback.

## Features

- **Full Manuscript mode** — chunk-by-chunk critique with selectable editor personas (Ruthless Critic, Encouraging Mentor, Grammar & Prose Stickler, or a custom prompt), genre presets, structure/beat-sheet overlays, chapter-length and platform pacing checks, and diff view for revisions.
- **Query Letter / Synopsis mode** — critiques hook strength, genre clarity, and stakes.
- **Read Like an Agent (First Page) mode** — simulates an agent's first-page read, scoring the opening hook by genre.
- **Webnovel tools** — platform pacing norms, chapter batch upload, and cliffhanger scoring for serialized fiction.
- Style audits (filter-word detection, POV/tense consistency), version history, caching of AI responses, and exportable Markdown reports and checklists.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and add your [Groq API key](https://console.groq.com/keys):
   ```
   GROQ_API_KEY=your_groq_api_key_here
   ```

## Usage

```
streamlit run app.py
```

Then open the local URL Streamlit prints, choose an analysis mode from the sidebar, and paste or upload your manuscript, query letter, or first page.

## Project structure

- `app.py` — Streamlit entry point and sidebar configuration.
- `src/views.py` — renders each analysis mode's UI.
- `src/ai_client.py` — Groq API calls, prompt construction, genre presets.
- `src/structure.py` — beat-sheet templates, scene detection, pacing/word-count checks.
- `src/style_audit.py` — filter-word and POV/tense checks.
- `src/reports.py` — Markdown report and checklist generation.
- `src/cache.py`, `src/history.py` — response caching and manuscript version history.
- `src/diff.py`, `src/file_io.py`, `src/chunker.py` — diff rendering, file extraction, text chunking utilities.
