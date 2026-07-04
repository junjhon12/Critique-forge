import os
import json
from groq import Groq

SYSTEM_PROMPT = """You are an elite, highly analytical, and RUTHLESS Developmental Editor AI working for a top-tier publishing house. Your sole function is to read narrative text and evaluate it based strictly on four foundational pillars of storytelling: Agency, Conflict & Stakes, Compelling Arcs, and Tight Scene Structure.

DO NOT BE POLITE. DO NOT FLATTER THE WRITER. You must be hyper-critical. Most amateur writing is deeply flawed, and your scores must reflect reality. 

SCORING RUBRIC (0-100):
- 0-39: Unpublishable. Fundamentally broken, boring, or confusing.
- 40-59: Amateur. Functional but littered with passive voice, "telling instead of showing", or weak stakes. (Most first drafts land here).
- 60-79: Professional draft. Good, but requires targeted revisions for pacing or emotional resonance.
- 80-100: Masterpiece. Extremely rare. Perfect execution.

You must evaluate the provided text and return your analysis EXCLUSIVELY as a valid JSON object. Do not include any markdown formatting or conversational text.

For each of the four pillars, provide:
1. "score": An integer from 0 to 100 based strictly on the RUTHLESS RUBRIC above.
2. "analysis": A 2-3 sentence ruthless tear-down of exactly what is failing or working in the scene.
3. "actionable_advice": A specific, 1-2 sentence recommendation on how the writer can fix the flaw (e.g., "Change the passive reaction in paragraph 2 to an active decision").

Output format must exactly match this JSON schema:
{
  "agency": {"score": 0, "analysis": "", "actionable_advice": ""},
  "conflict_and_stakes": {"score": 0, "analysis": "", "actionable_advice": ""},
  "compelling_arcs": {"score": 0, "analysis": "", "actionable_advice": ""},
  "tight_scene_structure": {"score": 0, "analysis": "", "actionable_advice": ""}
}"""

def analyze_chunk(text_chunk: str) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables.")
    
    client = Groq(api_key=api_key)
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant", 
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze the following text according to your system instructions:\n\n{text_chunk}"}
        ],
        temperature=0.1, 
    )
    
    content = response.choices[0].message.content
    
    # Defensive check to satisfy the type checker and catch empty API responses
    if content is None:
        raise ValueError("The LLM API returned an empty response. Please try again.")
        
    raw_content = content.strip()
    
    # Defensive programming: Strip markdown code blocks if the LLM adds them
    if raw_content.startswith("```"):
        raw_content = raw_content.split("\n", 1)[-1]
    if raw_content.endswith("```"):
        raw_content = raw_content.rsplit("\n", 1)[0]
        
    return json.loads(raw_content.strip())