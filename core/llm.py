"""
Groq LLM wrapper used by all agents.
Uses the Groq SDK with the OpenAI-compatible chat completions API.
Model: meta-llama/llama-4-scout-17b-16e-instruct (or as set in .env)
"""
import json
import re
from groq import Groq
from config.settings import GROQ_API_KEY, GROQ_MODEL


def get_groq_client() -> Groq:
    """Initialise and return a configured Groq client."""
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set. "
            "Add it to your .env file:  GROQ_API_KEY=your_key_here\n"
            "Get a free key at: https://console.groq.com/keys"
        )
    return Groq(api_key=GROQ_API_KEY)


def call_llm(prompt: str, system_instruction: str = "") -> str:
    """
    Send a prompt to the Groq model and return the raw text response.
    system_instruction is passed as the system message if provided.
    """
    client = get_groq_client()

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.1,      # low temperature for consistent medical coding
        max_tokens=4096,
    )
    return response.choices[0].message.content.strip()


def call_llm_json(prompt: str, system_instruction: str = "") -> dict:
    """
    Call the Groq model and parse the response as JSON.
    Strips markdown code fences before parsing.
    """
    # Ask the model explicitly to return only JSON
    json_system = (system_instruction + "\nReturn ONLY valid JSON. No prose, no markdown fences."
                   if system_instruction
                   else "Return ONLY valid JSON. No prose, no markdown fences.")

    raw = call_llm(prompt, json_system)

    # Strip ```json ... ``` or ``` ... ``` fences
    clean = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("```").strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Try to extract first JSON object/array from the response
        match = re.search(r"(\{.*\}|\[.*\])", clean, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"Could not parse Groq response as JSON:\n{raw}")


# ── Backward-compatible aliases so no other file needs changing ───────────────
call_gemini      = call_llm
call_gemini_json = call_llm_json
