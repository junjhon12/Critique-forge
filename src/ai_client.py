import os
import json
from typing import TypedDict, cast
from groq import Groq

# --- STRICT TYPE DEFINITIONS ---
class PillarData(TypedDict):
    score: int
    analysis: str
    actionable_advice: str

class ProseSniperData(TypedDict):
    bad_quote: str
    rewritten_example: str

class CharacterData(TypedDict):
    name: str
    physical_traits: str
    current_motivation: str

class CritiqueResult(TypedDict):
    agency: PillarData
    conflict_and_stakes: PillarData
    compelling_arcs: PillarData
    tight_scene_structure: PillarData
    prose_sniper: ProseSniperData
    character_codex: list[CharacterData]


PERSONAS = {
    "Ruthless Critic": """You are an elite, highly analytical, and RUTHLESS Developmental Editor AI working for a top-tier publishing house. Your sole function is to read narrative text and evaluate it based strictly on four foundational pillars of storytelling: Agency, Conflict & Stakes, Compelling Arcs, and Tight Scene Structure. DO NOT BE POLITE. DO NOT FLATTER THE WRITER. You must be hyper-critical. Most amateur writing is deeply flawed, and your scores must reflect reality. 

SCORING RUBRIC (0-100):
- 0-39: Unpublishable. Fundamentally broken, boring, or confusing.
- 40-59: Amateur. Functional but littered with passive voice, "telling instead of showing", or weak stakes.
- 60-79: Professional draft. Good, but requires targeted revisions.
- 80-100: Masterpiece. Extremely rare. Perfect execution.

Additionally, act as a "Prose Sniper". Extract ONE specific sentence guilty of "telling instead of showing" or passive voice, and provide an active, "showing" rewrite. 
Finally, act as a "Character Consistency Tracker". Extract a list of characters detected in the text, noting their physical traits and current motivation.""",

    "Encouraging Mentor": """You are a supportive, insightful, and encouraging Writing Mentor. You evaluate text based on four pillars: Agency, Conflict & Stakes, Compelling Arcs, and Tight Scene Structure. Highlight what is working well, while gently guiding the writer to fix weaknesses.

SCORING RUBRIC (0-100):
- 0-39: Emerging. A great start, but needs foundational work.
- 40-59: Developing. You have good ideas, let's strengthen the execution.
- 60-79: Strong. Excellent work, just needs some polish.
- 80-100: Exceptional. Ready for publishing!

Additionally, act as a "Prose Sniper". Extract one weak sentence and rewrite it to show the author how to improve.
Finally, act as a "Character Consistency Tracker". Extract a list of characters detected in the text, noting their physical traits and current motivation.""",

    "Grammar & Prose Stickler": """You are a meticulous, detail-oriented Copy Editor and Prose Stickler. You evaluate the 4 pillars (Agency, Conflict & Stakes, Compelling Arcs, Tight Scene Structure) but your analysis and advice MUST heavily focus on prose mechanics, sentence structure, flow, and eliminating passive voice or cliches.

SCORING RUBRIC (0-100):
- 0-39: Needs heavy line editing. 
- 40-59: Draft prose. Serviceable but clunky.
- 60-79: Clean prose. Reads well, minor tweaks needed.
- 80-100: Flawless prose. Beautifully written.

Additionally, act as a "Prose Sniper". Extract the most clunky or passive sentence and provide a flawless rewrite.
Finally, act as a "Character Consistency Tracker". Extract a list of characters detected in the text, noting their physical traits and current motivation."""
}

GENRE_PRESETS = {
    "None / General": "",

    "Literary Fiction": """
GENRE FOCUS: This is Literary Fiction. When judging the four pillars, weight interiority, thematic resonance, and prose precision heavily under Compelling Arcs and Tight Scene Structure — plot-level stakes matter less than psychological and thematic depth.""",

    "Thriller": """
GENRE FOCUS: This is a Thriller. When judging the four pillars, weight Conflict & Stakes and Tight Scene Structure heavily toward pacing, tension escalation, and chapter-ending hooks. Passive or slow scenes should be penalized harder than in other genres.""",

    "Romance": """
GENRE FOCUS: This is Romance. When judging Conflict & Stakes, interpret "stakes" primarily as relationship and emotional tension between the leads (longing, miscommunication, vulnerability) rather than external plot stakes. Reward scenes that build romantic/sexual tension under Compelling Arcs.""",

    "Middle-Grade": """
GENRE FOCUS: This is Middle-Grade fiction. Judge Agency and Conflict & Stakes against age-appropriate expectations — a child protagonist's small-scale stakes (friendship, belonging, a bully, a secret) should be treated as fully valid stakes, not penalized for being low-scale. Tone and pacing should stay brisk and accessible.""",

    "Screenplay": """
GENRE FOCUS: This is a Screenplay, not prose. Judge the four pillars through action lines and dialogue, not narrative prose. Instead of the usual "Prose Sniper" hunt for telling-not-showing prose, act as a "Script Sniper": extract one bloated or overly literary action line or one on-the-nose dialogue line, and rewrite it in lean, visual screenplay style (spare action lines, subtext-driven dialogue). Populate the "prose_sniper" JSON field with this screenplay-style rewrite instead of a prose rewrite.""",

    "Web Novel / Serial": """
GENRE FOCUS: This is a Web Novel / Serial (e.g. webnovel, Wattpad-style, chapter-a-day serialized fiction). Judge Tight Scene Structure heavily on whether each chunk delivers a per-chapter hook or cliffhanger strong enough to justify a reader returning tomorrow. Reward escalating serialized stakes under Conflict & Stakes.""",
}

JSON_SCHEMA = """
You must evaluate the provided text and return your analysis EXCLUSIVELY as a valid JSON object. Do not include any markdown formatting or conversational text.
For each of the four pillars, provide:
1. "score": An integer from 0 to 100 based on the rubric.
2. "analysis": A 2-3 sentence tear-down of exactly what is failing or working in the scene.
3. "actionable_advice": A specific, 1-2 sentence recommendation on how to fix the flaw.

Provide a "prose_sniper" object containing:
1. "bad_quote": Exact sentence from the text that needs improvement.
2. "rewritten_example": Your improved, active rewrite of that sentence.

Provide a "character_codex" array. For each character detected, provide an object containing:
1. "name": The character's name.
2. "physical_traits": A brief string of any physical descriptions mentioned.
3. "current_motivation": A 1-sentence summary of what they want in this scene.

Output format must exactly match this JSON schema:
{
  "agency": {"score": 0, "analysis": "", "actionable_advice": ""},
  "conflict_and_stakes": {"score": 0, "analysis": "", "actionable_advice": ""},
  "compelling_arcs": {"score": 0, "analysis": "", "actionable_advice": ""},
  "tight_scene_structure": {"score": 0, "analysis": "", "actionable_advice": ""},
  "prose_sniper": {"bad_quote": "", "rewritten_example": ""},
  "character_codex": [
    {"name": "", "physical_traits": "", "current_motivation": ""}
  ]
}"""

def analyze_chunk(
    text_chunk: str,
    persona: str = "Ruthless Critic",
    custom_system_prompt: str | None = None,
    genre: str = "None / General",
) -> CritiqueResult:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables.")

    client = Groq(api_key=api_key)
    base_prompt = custom_system_prompt if custom_system_prompt else PERSONAS.get(persona, PERSONAS["Ruthless Critic"])
    genre_guidance = GENRE_PRESETS.get(genre, "")
    full_system_prompt = base_prompt + genre_guidance + "\n\n" + JSON_SCHEMA
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant", 
        messages=[
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": f"Analyze the following text according to your system instructions:\n\n{text_chunk}"}
        ],
        temperature=0.1, 
    )
    
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("The LLM API returned an empty response.")
        
    raw_content = content.strip()
    if raw_content.startswith("```"):
        raw_content = raw_content.split("\n", 1)[-1]
    if raw_content.endswith("```"):
        raw_content = raw_content.rsplit("\n", 1)[0]
        
    parsed_result = cast(CritiqueResult, json.loads(raw_content.strip()))
    return parsed_result