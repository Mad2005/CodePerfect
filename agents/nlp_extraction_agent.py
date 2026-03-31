"""
NLP Extraction Agent  — LLM primary + BioBERT secondary + merge
────────────────────────────────────────────────────────────────
Extraction flow:

  Step 1 — LLM extraction (primary)
    • Sends cleaned note to the Groq LLM
    • Context-aware: understands negation, implicit diagnoses, complex phrasing
    • Returns entities with confidence scores

  Step 2 — BioBERT NER (secondary, runs in parallel via thread)
    • Runs biomedical NER model on the same text
    • Pure pattern-based: catches explicit medical terms LLM may miss
    • Returns entities with NER confidence scores

  Step 3 — Merge (entity_merger.py)
    • LLM + BioBERT agree  → confidence 0.95 (both sources confirm)
    • LLM only             → confidence 0.90 (trusted primary)
    • BioBERT only         → confidence 0.60 (kept but lower trust)

  Step 4 — RxNorm enrichment (optional, for medications)
    • Normalises drug names, adds RxCUI + drug class

Final entities are passed to the SNOMED mapping and coding agents.
"""
from __future__ import annotations
import threading
from core.models     import PipelineState, ClinicalEntities, Diagnosis, Procedure, Medication
from core.llm        import call_gemini_json
from core.entity_merger import merge_extractions, summarise_merge
from rich.console    import Console

console = Console()

# ── LLM extraction prompt ─────────────────────────────────────────────────────

_LLM_SYSTEM = (
    "You are a senior clinical NLP specialist with expertise in medical entity extraction. "
    "Extract ONLY entities explicitly stated in the note — do not infer or hallucinate. "
    "Return ONLY valid JSON — no prose, no markdown fences."
)

_LLM_PROMPT = """
Extract all clinical entities from the note below.

Rules:
- Extract every DIAGNOSIS, CONDITION, DISEASE, SYNDROME, and FINDING explicitly mentioned.
- Extract every PROCEDURE, SURGERY, TEST, IMAGING, and INTERVENTION explicitly documented.
- Extract every MEDICATION, DRUG, and TREATMENT explicitly listed.
- Assign confidence: 1.0 = directly stated, 0.85 = clearly documented but slightly implied,
  0.7 = mentioned in passing, 0.0 = do not include.
- Do NOT add entities not present in the text.
- Do NOT duplicate entities.

Return JSON:
{{
  "diagnoses": [
    {{"text": "exact diagnosis text", "confidence": 0.0-1.0}}
  ],
  "procedures": [
    {{"text": "exact procedure text", "confidence": 0.0-1.0}}
  ],
  "medications": [
    {{"text": "medication name and dose as written", "confidence": 0.9}}
  ],
  "other_entities": [
    "lab values, vital signs, relevant findings as plain strings"
  ]
}}

CLINICAL NOTE:
{text}
"""


def _run_llm_extraction(text: str) -> dict:
    """Run LLM extraction. Returns entity dict."""
    return call_gemini_json(
        _LLM_PROMPT.format(text=text[:3500]),
        _LLM_SYSTEM,
    )


def _run_biobert_extraction(text: str) -> dict:
    """Run BioBERT NER extraction with diagnostics."""
    try:
        from core.biobert_extractor import extract_entities_pubmedbert
        data, model_name = extract_entities_pubmedbert(text)
        print(f"[DEBUG] BioBERT {model_name} raw output: {data}")  # ADD THIS
        return data
    except Exception as exc:
        print(f"[DEBUG] BioBERT error: {exc}")  # ADD THIS
        import traceback
        traceback.print_exc()  # ADD THIS
        return {}


# ── Main agent ────────────────────────────────────────────────────────────────

def nlp_extraction_agent(state: PipelineState) -> PipelineState:
    """
    LangGraph node:
      1. LLM extraction  (primary)
      2. BioBERT NER     (secondary, concurrent)
      3. Merge with confidence calibration
      4. RxNorm enrichment (optional)
    """
    text = state.cleaned_text or state.raw_clinical_text

    # ── Step 1 + 2: Run LLM and BioBERT concurrently ─────────────────────────
    console.print("[dim]  → Starting LLM extraction (primary)...[/]")
    console.print("[dim]  → Starting BioBERT NER (secondary, concurrent)...[/]")

    llm_result:    dict = {}
    bio_result:    dict = {}
    llm_error:     str  = ""
    bio_model_name: str = "BioBERT"

    def run_llm():
        nonlocal llm_result, llm_error
        try:
            llm_result = _run_llm_extraction(text)
        except Exception as exc:
            llm_error = str(exc)

    def run_bio():
        nonlocal bio_result, bio_model_name
        try:
            from core.biobert_extractor import extract_entities_pubmedbert
            bio_result, bio_model_name = extract_entities_pubmedbert(text)
            print(f"[DEBUG] BioBERT thread {bio_model_name} raw output: {bio_result}")
        except Exception as exc:
            print(f"[DEBUG] BioBERT error in thread: {exc}")
            import traceback
            traceback.print_exc()
            bio_result = {}

    t_llm = threading.Thread(target=run_llm)
    t_bio = threading.Thread(target=run_bio)
    t_llm.start()
    t_bio.start()
    t_llm.join()
    t_bio.join()

    # ── Handle LLM failure ────────────────────────────────────────────────────
    if llm_error or not llm_result:
        state.errors.append(f"LLM extraction failed: {llm_error}")
        console.print(f"[red]  → LLM extraction failed: {llm_error}[/]")
        # If LLM failed but BioBERT has something, use it as primary
        if bio_result and any(bio_result.get(k) for k in ("diagnoses","procedures","medications")):
            console.print("[yellow]  → Using BioBERT as sole source (LLM failed)[/]")
            # Promote BioBERT to LLM-level confidence since it's the only source
            for key in ("diagnoses", "procedures", "medications"):
                for ent in bio_result.get(key, []):
                    ent["confidence"] = 0.90
            llm_result = bio_result
            bio_result = {}
        else:
            state.clinical_entities = ClinicalEntities()
            return state

    # ── Log results ───────────────────────────────────────────────────────────
    llm_d = len(llm_result.get("diagnoses",  []))
    llm_p = len(llm_result.get("procedures", []))
    llm_m = len(llm_result.get("medications",[]))
    console.print(
        f"[green]  → LLM: {llm_d} diagnoses, {llm_p} procedures, {llm_m} medications[/]"
    )

    bio_d = len(bio_result.get("diagnoses",  []))
    bio_p = len(bio_result.get("procedures", []))
    bio_m = len(bio_result.get("medications",[]))
    if bio_d + bio_p + bio_m > 0:
        console.print(
            f"[cyan]  → {bio_model_name}: "
            f"{bio_d} diagnoses, {bio_p} procedures, {bio_m} medications[/]"
        )
    else:
        console.print("[dim]  → BioBERT: 0 entities (LLM result used alone)[/]")

    # ── Step 3: Merge ─────────────────────────────────────────────────────────
    merged = merge_extractions(llm_result, bio_result)
    console.print(f"[bold green]  → Merged: {summarise_merge(merged)}[/]")

    # ── Step 4: Build entity model objects (WITHOUT RxNorm — will enrich later) ────────────────────────────────────
    diagnoses  = [
        Diagnosis(text=e["text"], confidence=e["confidence"])
        for e in merged.get("diagnoses", []) if e.get("text")
    ]
    procedures = [
        Procedure(text=e["text"], confidence=e["confidence"])
        for e in merged.get("procedures", []) if e.get("text")
    ]

    raw_meds   = merged.get("medications", [])
    medications = []
    for m in raw_meds:
        t    = m.get("text", str(m))
        conf = float(m.get("confidence", 0.9))
        # Create medication WITHOUT RxNorm enrichment (will be added later)
        medications.append(Medication(
            text           = t,
            normalized_name= None,
            rxnorm_rxcui   = None,
            rxnorm_name    = None,
            rxnorm_class   = None,
        ))

    others = merged.get("other_entities", [])

    state.clinical_entities = ClinicalEntities(
        diagnoses     =diagnoses,
        procedures    =procedures,
        medications   =medications,
        other_entities=others,
    )

    # Store merge source stats for transparency
    both_count = sum(1 for e in merged.get("diagnoses",[]) + merged.get("procedures",[])
                     if e.get("source") == "llm+biobert")
    bio_only   = sum(1 for e in merged.get("diagnoses",[]) + merged.get("procedures",[])
                     if e.get("source") == "biobert")
    if bio_only:
        state.errors.append(
            f"NLPExtraction: {both_count} entities confirmed by both sources, "
            f"{bio_only} BioBERT-only entities included at confidence 0.60"
        )

    return state