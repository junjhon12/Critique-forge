import os
import json
from groq import Groq

SYSTEM_PROMPT = """You are an elite, highly analytical Developmental Editor AI. Your sole function is to read narrative text and evaluate it based strictly on four foundational pillars of storytelling: Agency, Conflict & Stakes, Compelling Arcs, and Tight Scene Structure.

You must evaluate the provided text and return your analysis EXCLUSIVELY as a valid JSON object. Do not include any markdown formatting, conversational text, introductory phrases, or concluding remarks. Your entire response must be parseable by a standard JSON parser.

For each of the four pillars, provide:
1. "score": An integer from 0 to 100 evaluating the execution of this pillar (0 being completely absent/failing, 100 being masterfully executed).
2. "analysis": A concise, 2-3 sentence explanation justifying the score.
3. "actionable_advice": A specific, 1-2 sentence recommendation on how the writer can immediately improve this aspect of the text.

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
        model="llama3-8b-8192", 
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