"""
Text Processing Agent
─────────────────────
Cleans clinical notes, normalises terminology, expands abbreviations.
"""
from core.llm import call_gemini
from core.models import PipelineState

SYSTEM = (
    "You are a clinical text preprocessing specialist. "
    "Your job is to clean and normalise raw hospital clinical notes for downstream NLP processing. "
    "Do NOT diagnose, code, or interpret — only clean and normalise the text."
)

PROMPT_TEMPLATE = """
Clean and normalise the following clinical note:

1. Expand common medical abbreviations (e.g., HTN→Hypertension, DM→Diabetes Mellitus, MI→Myocardial Infarction, SOB→Shortness of Breath, Hx→History, Dx→Diagnosis, Rx→Prescription, PRN→as needed, BID→twice daily, TID→three times daily).
2. Fix obvious typos while preserving medical terminology.
3. Standardise formatting (consistent spacing, sentence structure).
4. Remove non-clinical noise (page numbers, system artefacts).
5. Preserve ALL clinical content — do not summarise or omit anything.

CLINICAL NOTE:
{text}

Return ONLY the cleaned clinical text, nothing else.
"""


def text_processing_agent(state: PipelineState) -> PipelineState:
    """LangGraph node: cleans and normalises raw clinical text."""
    try:
        prompt = PROMPT_TEMPLATE.format(text=state.raw_clinical_text)
        cleaned = call_gemini(prompt, SYSTEM)
        state.cleaned_text = cleaned
    except Exception as exc:
        state.errors.append(f"TextProcessingAgent error: {exc}")
        state.cleaned_text = state.raw_clinical_text   # fallback to raw
    return state
