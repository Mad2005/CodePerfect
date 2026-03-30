"""
Biomedical NER Extractor
─────────────────────────
Uses proven biomedical NER models from Hugging Face.
Model chain (tries in order, uses first that works):

1. d4data/biomedical-ner-all  — BioBERT fine-tuned, broad biomedical NER
                                 Labels: Disease_disorder, Medication, Diagnostic_procedure, etc.
                                 This is the MOST RELIABLE model for clinical text.

2. pruas/BENT-PubMedBERT-NER-Disease — PubMedBERT, disease-focused NER

Note: allenai/scibert_scivocab_uncased is a LANGUAGE MODEL, not a NER model.
      It loads but produces no entities. Removed from chain.
"""
from __future__ import annotations
import re, os
from functools import lru_cache

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# ── Label → entity type ───────────────────────────────────────────────────────

DIAGNOSIS_LABELS = {
    "Disease_disorder", "Sign_symptom", "Pathological_formation",
    "DISEASE", "Disease", "DISEASE_OR_SYNDROME", "SIGN_OR_SYMPTOM",
    "B-DISEASE", "I-DISEASE", "B-Disease_disorder", "I-Disease_disorder",
}
PROCEDURE_LABELS = {
    "Diagnostic_procedure", "Therapeutic_procedure", "Medical_device",
    "Lab_value", "Activity",
    "DIAGNOSTIC_PROCEDURE", "THERAPEUTIC_PROCEDURE", "LABORATORY_PROCEDURE",
    "B-Diagnostic_procedure", "I-Diagnostic_procedure",
    "B-Therapeutic_procedure", "I-Therapeutic_procedure",
}
MEDICATION_LABELS = {
    "Medication", "DRUG", "Drug", "CHEMICAL", "Chemical",
    "Dosage", "Frequency", "Route", "Duration",
    "B-Medication", "I-Medication", "B-DRUG", "I-DRUG",
    "B-CHEMICAL", "I-CHEMICAL",
}

NER_MODEL_CHAIN = [
    ("d4data/biomedical-ner-all",          "BioBERT (d4data/biomedical-ner-all)"),
    ("pruas/BENT-PubMedBERT-NER-Disease",  "PubMedBERT-NER-Disease"),
]


@lru_cache(maxsize=1)
def _load_pipeline():
    from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
    errors = []
    for model_name, label in NER_MODEL_CHAIN:
        try:
            print(f"  [NER] Loading: {model_name} ...", flush=True)
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model     = AutoModelForTokenClassification.from_pretrained(model_name)
            ner = pipeline("ner", model=model, tokenizer=tokenizer,
                           aggregation_strategy="simple", device=-1)
            # Smoke test — must find at least 1 entity in a clear clinical sentence
            result = ner("The patient has pneumonia and hypertension.")
            found  = len(result)
            print(f"  [NER] ✓ {label} loaded — {found} entities on smoke test", flush=True)
            if found == 0:
                raise ValueError("Smoke test returned 0 entities — model not suitable for NER")
            return ner, label
        except Exception as exc:
            errors.append(f"{model_name}: {exc}")
            print(f"  [NER] ✗ {model_name} failed: {exc}", flush=True)
    raise RuntimeError("All NER models failed:\n" + "\n".join(errors))


def _clean(text: str) -> str:
    return re.sub(r"^[\s\-–•#:,()\[\]]+|[\s\-–•#:,()\[\]]+$", "", text).strip()


def _run_chunked(ner_fn, text: str, chunk_words: int = 350, overlap: int = 40) -> list[dict]:
    words = text.split()
    if len(words) <= chunk_words:
        try:    return ner_fn(text)
        except: return []
    results, step = [], chunk_words - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i: i + chunk_words])
        try:    results.extend(ner_fn(chunk))
        except: continue
    return results


def extract_entities_pubmedbert(text: str) -> tuple[dict, str]:
    """Run NER. Returns (entity_dict, model_name_used)."""
    ner, model_name = _load_pipeline()
    raw = _run_chunked(ner, text)

    diagnoses:   list[dict] = []
    procedures:  list[dict] = []
    medications: list[dict] = []
    others:      list[str]  = []
    seen: set[str] = set()

    for ent in raw:
        word  = _clean(ent.get("word", ""))
        label = ent.get("entity_group", ent.get("entity", "MISC"))
        score = round(float(ent.get("score", 0.5)), 2)

        if not word or len(word) < 2:
            continue
        norm = word.lower()
        if norm in seen:
            continue
        seen.add(norm)

        if label in DIAGNOSIS_LABELS:
            diagnoses.append({"text": word, "confidence": score})
        elif label in PROCEDURE_LABELS:
            procedures.append({"text": word, "confidence": score})
        elif label in MEDICATION_LABELS:
            medications.append({"text": word})
        else:
            others.append(word)

    return {
        "diagnoses":      diagnoses,
        "procedures":     procedures,
        "medications":    medications,
        "other_entities": others,
    }, model_name