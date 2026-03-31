"""
Entity Merger
─────────────
Merges LLM extraction results with BioBERT NER results.

Confidence assignment rules:
  LLM + BioBERT agree  → 0.95  (both sources confirm — highest trust)
  LLM only             → 0.90  (LLM trusted as primary, context-aware)
  BioBERT only         → 0.60  (NER found it but LLM missed — lower trust)

"Agree" = normalised text overlap (exact match OR one is a substring of the other
          within a 3-token tolerance, e.g. "diabetes mellitus" vs "type 2 diabetes mellitus")

The merge is per entity type (diagnoses, procedures, medications) independently.
"""
from __future__ import annotations
import re


# ── Confidence constants ──────────────────────────────────────────────────────

CONF_BOTH     = 0.95   # LLM + BioBERT agree
CONF_LLM_ONLY = 0.90   # LLM found, BioBERT missed
CONF_BIO_ONLY = 0.60   # BioBERT found, LLM missed


# ── Text normalisation ────────────────────────────────────────────────────────

def _norm(text: str) -> str:
    """Lowercase, strip punctuation/extra spaces for comparison."""
    t = text.lower().strip()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _clean_entity_text(text: str) -> str:
    """Remove leading/trailing # and other bullet symbols from entity text."""
    text = text.strip()
    # Remove leading # - • * symbols
    text = re.sub(r"^[\s#\-•*]+", "", text).strip()
    return text


def _tokens(text: str) -> set[str]:
    """Return set of word tokens (≥3 chars) from a normalised string."""
    return {w for w in _norm(text).split() if len(w) >= 3}


def _overlap(a: str, b: str) -> float:
    """
    Token-level Jaccard overlap between two entity strings.
    Returns 0.0–1.0.  ≥ 0.5 is considered a match.
    """
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _find_match(entity_text: str, candidates: list[dict],
                threshold: float = 0.5) -> dict | None:
    """
    Find the best-matching candidate for entity_text.
    Returns the candidate dict or None if no match above threshold.
    """
    best_score, best_cand = 0.0, None
    norm_e = _norm(entity_text)
    for cand in candidates:
        cand_text = cand.get("text", "")
        norm_c    = _norm(cand_text)
        # Fast exact check first
        if norm_e == norm_c:
            return cand
        # Substring check (one contained in the other)
        if norm_e in norm_c or norm_c in norm_e:
            score = len(min(norm_e, norm_c, key=len)) / len(max(norm_e, norm_c, key=len))
            if score > best_score:
                best_score, best_cand = score, cand
            continue
        # Token overlap
        score = _overlap(entity_text, cand_text)
        if score > best_score:
            best_score, best_cand = score, cand

    return best_cand if best_score >= threshold else None


# ── Per-type merge ────────────────────────────────────────────────────────────

def _merge_entity_list(
    llm_entities:  list[dict],   # [{"text": str, "confidence": float}, ...]
    bio_entities:  list[dict],   # same format
    entity_type:   str,          # "diagnosis" | "procedure" | "medication"
) -> list[dict]:
    """
    Merge two entity lists with the confidence rules above.
    Returns a deduplicated merged list sorted by confidence desc.
    """
    merged: list[dict] = []
    used_bio: set[int] = set()   # indices in bio_entities already matched

    # ── Pass 1: LLM entities ──────────────────────────────────────────────────
    for llm_ent in llm_entities:
        llm_text = _clean_entity_text(llm_ent.get("text", "").strip())
        if not llm_text:
            continue

        bio_match = _find_match(llm_text, bio_entities)
        if bio_match is not None:
            # Both agree — use the LLM's text (more context-aware) at 0.95
            idx = bio_entities.index(bio_match)
            used_bio.add(idx)
            merged.append({
                "text"      : llm_text,
                "confidence": CONF_BOTH,
                "source"    : "llm+biobert",
                "bio_text"  : bio_match.get("text", ""),   # store for transparency
            })
        else:
            # LLM only
            merged.append({
                "text"      : llm_text,
                "confidence": CONF_LLM_ONLY,
                "source"    : "llm",
            })

    # ── Pass 2: BioBERT-only entities (not matched to any LLM entity) ─────────
    for i, bio_ent in enumerate(bio_entities):
        if i in used_bio:
            continue
        bio_text = _clean_entity_text(bio_ent.get("text", "").strip())
        if not bio_text or len(bio_text) < 3:
            continue
        # Extra filter: skip very short / noisy tokens that NER sometimes produces
        if len(bio_text.split()) == 1 and len(bio_text) < 5:
            continue
        merged.append({
            "text"      : bio_text,
            "confidence": CONF_BIO_ONLY,
            "source"    : "biobert",
        })

    # Sort: highest confidence first; deduplicate by normalised text
    seen_norm: set[str] = set()
    deduped: list[dict] = []
    for ent in sorted(merged, key=lambda x: x["confidence"], reverse=True):
        n = _norm(ent["text"])
        if n and n not in seen_norm:
            seen_norm.add(n)
            deduped.append(ent)

    return deduped


# ── Public API ────────────────────────────────────────────────────────────────

def merge_extractions(
    llm_data:  dict,   # output of LLM extraction
    bio_data:  dict,   # output of BioBERT extraction (may be empty)
) -> dict:
    """
    Merge LLM and BioBERT extraction dicts.

    Input dicts have keys: diagnoses, procedures, medications, other_entities
    Each value is a list of {"text": str, "confidence": float} dicts.

    Returns merged dict with same structure and calibrated confidence scores.
    Also adds a "source" field per entity for transparency.
    """
    merged_diag  = _merge_entity_list(
        llm_data.get("diagnoses",  []),
        bio_data.get("diagnoses",  []),
        "diagnosis",
    )
    merged_proc  = _merge_entity_list(
        llm_data.get("procedures", []),
        bio_data.get("procedures", []),
        "procedure",
    )

    # Medications: merge text lists, then deduplicate
    # (medications may come as {"text":...} without confidence from BioBERT)
    llm_meds = llm_data.get("medications", [])
    bio_meds = bio_data.get("medications", [])

    # Normalise BioBERT meds to same format as LLM meds
    bio_meds_norm = [{"text": m.get("text", m) if isinstance(m, dict) else str(m),
                      "confidence": float(m.get("confidence", 0.7)) if isinstance(m, dict) else 0.7}
                     for m in bio_meds]
    llm_meds_norm = [{"text": m.get("text", m) if isinstance(m, dict) else str(m),
                      "confidence": float(m.get("confidence", 0.9)) if isinstance(m, dict) else 0.9}
                     for m in llm_meds]

    merged_meds  = _merge_entity_list(llm_meds_norm, bio_meds_norm, "medication")

    # Other entities: simple union (no scoring needed)
    llm_others = llm_data.get("other_entities", [])
    bio_others = bio_data.get("other_entities", [])
    merged_others = list({str(e) for e in llm_others + bio_others})

    return {
        "diagnoses"     : merged_diag,
        "procedures"    : merged_proc,
        "medications"   : merged_meds,
        "other_entities": merged_others,
    }


def summarise_merge(merged: dict) -> str:
    """Return a compact one-line summary of the merge result for logging."""
    parts = []
    for key in ("diagnoses", "procedures", "medications"):
        entities = merged.get(key, [])
        both = sum(1 for e in entities if e.get("source") == "llm+biobert")
        llm  = sum(1 for e in entities if e.get("source") == "llm")
        bio  = sum(1 for e in entities if e.get("source") == "biobert")
        if entities:
            parts.append(f"{key[:4]}:{len(entities)}(✓{both} L{llm} B{bio})")
    return " | ".join(parts) if parts else "no entities"