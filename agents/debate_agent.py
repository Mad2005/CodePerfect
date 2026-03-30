"""
Debate Agent (v4 — rule-compliant arbitration)
─────────────────────────────────────────────
Resolves conflicts between Clinical and Revenue agents using
general ICD-10-CM / CPT / HCPCS coding principles + NCCI/MUE/LCD/NCD.
Conservative by default: clinical agent wins ties, revenue must prove upgrades.
"""

from core.llm import call_gemini_json
from core.models import PipelineState, DebateResult, DebatePoint


SYSTEM = (
    "You are a Chief Medical Coding Officer (CMCO) arbitrating between two expert coders. "
    "Your standard is conservative: when documentation is ambiguous, choose the lower-level "
    "or more specific code. Your rulings must be audit-defensible and compliant "
    "with NCCI PTP edits, MUE limits, LCD/NCD policies. "
    "Clinical agent wins ties. Revenue agent must prove upgrades with direct quotes. "
    "Return ONLY valid JSON — no prose, no fences."
)


DEBATE_PROMPT = """
Two coding agents independently coded the same clinical encounter.
Compare their outputs, identify conflicts, and produce one final unified code set.

CLINICAL NOTE:
{note}

CLINICAL ACCURACY AGENT:
ICD-10 : {clinical_icd10}
CPT    : {clinical_cpt}
HCPCS  : {clinical_hcpcs}
Notes  : {clinical_notes}

REVENUE OPTIMIZATION AGENT:
ICD-10 : {revenue_icd10}
CPT    : {revenue_cpt}
HCPCS  : {revenue_hcpcs}
Notes  : {revenue_notes}

REFERENCE DATA FROM CHROMADB:
NCCI PTP edits:
{ncci_ptp}
MUE tables:
{mue}
LCD/NCD coverage:
{lcd_ncd}
Coding guidelines:
{guidelines}

━━━━━━━━━━━━━━━━━━━━━━━━━━
ARBITRATION PRINCIPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━

1. CONSENSUS FIRST
   If both agents coded the same code → mark as consensus and include it.

2. PRE‑FILTER NON‑COMPLIANT CODES
   Before arbitrating, exclude any code from either agent that:
   a) Has confidence < 0.8
   b) Violates an NCCI PTP edit (reference data shows the conflict)
   c) Exceeds MUE units for that code
   d) Fails LCD/NCD coverage for the documented diagnosis
   e) Is a symptom code (R-code) integral to the principal diagnosis
   f) Is a Z-code not explicitly stated in the note
   g) Is critical care (99291/99292) without explicit "critically ill" + time documentation

3. RESOLVE EACH CONFLICT
   For each remaining code where agents disagree, evaluate:
   • Which agent's code is better supported by the note?
   • Does the revenue agent's challenge include a direct quote? If not → clinical wins.
   • Is the revenue agent proposing a higher E&M level? Require clear MDM documentation (diagnoses, data, risk).
   • winning_agent values:
       "clinical"  — clinical agent is correct or revenue cannot prove upgrade
       "revenue"   — revenue agent is correct AND note + rules support it
       "both"      — consensus (same code from both)
       "neither"   — both agents are wrong; use a corrected code from reference data or exclude

4. E&M LEVEL ARBITRATION (STRICT)
   • Revenue may only win E&M upgrades if the note explicitly documents MDM elements
     that support the higher level AND it passes NCCI/MUE/LCD/NCD checks.
   • Clinical wins all tiebreakers and borderline cases.
   • Never assign critical care based on abnormal vitals alone.

5. FINAL OUTPUT MUST BE COMPLIANT
   • No duplicate codes.
   • All final codes must have confidence >= 0.8.
   • Correct ICD-10 sequencing: principal first, then secondary, then additional.
   • No code pairs that violate NCCI PTP edits.

━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━
Return JSON:
{{
  "debate_points": [
    {{
      "code": "disputed or corrected code",
      "code_type": "ICD-10|CPT|HCPCS",
      "clinical_position": "what clinical agent coded and why (max 80 chars)",
      "revenue_position": "what revenue agent coded and why (max 80 chars)",
      "conflict_type": "different_code|different_level|one_sided|units_differ|compliance_violation",
      "resolution": "one sentence: decision and reason (mention NCCI/MUE/LCD/NCD if relevant)",
      "winning_agent": "clinical|revenue|both|neither",
      "final_code": "the code to include in the final output",
      "final_description": "official description",
      "final_units": 1,
      "final_confidence": 0.0-1.0,
      "reasoning": "cite specific guideline, rule, or direct note text (max 120 chars)"
    }}
  ],
  "final_icd10_codes": [
    {{
      "code": "code", "description": "description", "code_type": "ICD-10",
      "sequence_type": "principal|secondary|additional",
      "units": 1, "confidence": 0.0-1.0, "rationale": "brief rationale"
    }}
  ],
  "final_cpt_codes": [
    {{
      "code": "code", "description": "description", "code_type": "CPT",
      "units": 1, "confidence": 0.0-1.0, "rationale": "brief rationale"
    }}
  ],
  "final_hcpcs_codes": [
    {{
      "code": "code", "description": "description", "code_type": "HCPCS",
      "category": "drug|DME|supply|vaccine",
      "units": 1, "confidence": 0.0-1.0, "rationale": "brief rationale"
    }}
  ],
  "clinical_wins": 0,
  "revenue_wins": 0,
  "consensus_codes": 0,
  "debate_summary": "2-3 sentences describing the key conflicts and how they were resolved"
}}
"""


def debate_agent(state: PipelineState) -> PipelineState:
    try:
        ca = state.clinical_agent_output
        ra = state.revenue_agent_output

        def fmt(codes):
            if not codes:
                return "  None"
            return "\n".join(
                f"  {c.code} – {c.description} x{c.units} "
                f"[conf:{c.confidence:.2f}] | {c.rationale[:120]}"
                for c in codes
            )

        # Include vectorDB reference data for compliance checks
        ncci_ptp = getattr(state, "vector_ncci_ptp", []) or getattr(state, "retrieved_rules", [])
        mue = getattr(state, "vector_mue", [])
        lcd_ncd = getattr(state, "vector_lcd_ncd", [])
        guide_text = "\n".join(getattr(state, "retrieved_guidelines", [])[:12]) or "Standard guidelines apply"

        data = call_gemini_json(
            DEBATE_PROMPT.format(
                note=state.cleaned_text[:2500],
                clinical_icd10=fmt(ca.icd10_codes if ca else []),
                clinical_cpt=fmt(ca.cpt_codes if ca else []),
                clinical_hcpcs=fmt(ca.hcpcs_codes if ca else []),
                clinical_notes=ca.agent_notes if ca else "N/A",
                revenue_icd10=fmt(ra.icd10_codes if ra else []),
                revenue_cpt=fmt(ra.cpt_codes if ra else []),
                revenue_hcpcs=fmt(ra.hcpcs_codes if ra else []),
                revenue_notes=ra.agent_notes if ra else "N/A",
                ncci_ptp="\n".join(ncci_ptp[:10]) if ncci_ptp else "No NCCI data available",
                mue="\n".join(mue[:10]) if mue else "No MUE data available",
                lcd_ncd="\n".join(lcd_ncd[:10]) if lcd_ncd else "No LCD/NCD data available",
                guidelines=guide_text,
            ),
            SYSTEM,
        )

        all_points = [DebatePoint(**p) for p in data.get("debate_points", [])]

        # Derive counts deterministically (don't trust LLM numbers).
        # Compute consensus as the intersection of codes both agents originally proposed.
        def _codes_by_type(agent, attr):
          return {c.code for c in getattr(agent, attr, [])} if agent else set()

        ca_icd = _codes_by_type(ca, "icd10_codes")
        ra_icd = _codes_by_type(ra, "icd10_codes")
        ca_cpt = _codes_by_type(ca, "cpt_codes")
        ra_cpt = _codes_by_type(ra, "cpt_codes")
        ca_hcpcs = _codes_by_type(ca, "hcpcs_codes")
        ra_hcpcs = _codes_by_type(ra, "hcpcs_codes")

        icd_consensus = len(ca_icd & ra_icd)
        cpt_consensus = len(ca_cpt & ra_cpt)
        hcpcs_consensus = len(ca_hcpcs & ra_hcpcs)
        consensus_count = icd_consensus + cpt_consensus + hcpcs_consensus

        # Conflicts are debate points where the LLM indicated a non-consensus resolution.
        conflict_list = [
          p for p in all_points
          if p.winning_agent != "both" and p.conflict_type not in ("no conflict", "no_conflict")
        ]

        clinical_wins = sum(1 for p in conflict_list if p.winning_agent == "clinical")
        revenue_wins = sum(1 for p in conflict_list if p.winning_agent == "revenue")
        neither_wins = sum(1 for p in conflict_list if p.winning_agent == "neither")

        state.debate_result = DebateResult(
            debate_points=conflict_list,  # only actual conflicts
            final_icd10_codes=data.get("final_icd10_codes", []),
            final_cpt_codes=data.get("final_cpt_codes", []),
            final_hcpcs_codes=data.get("final_hcpcs_codes", []),
            clinical_wins=clinical_wins,
            revenue_wins=revenue_wins,
            consensus_codes=consensus_count,
            debate_summary=data.get("debate_summary", ""),
        )

        # Update state codes for downstream use
        state.accuracy_codes = {
            "icd10_codes": data.get("final_icd10_codes", []),
            "coding_notes": data.get("debate_summary", ""),
        }
        state.revenue_codes = {
            "cpt_codes": data.get("final_cpt_codes", []),
            "hcpcs_codes": data.get("final_hcpcs_codes", []),
            "missed_billable_services": (
                (getattr(ca, "missed_services", []) if ca else []) +
                (getattr(ra, "missed_services", []) if ra else [])
            ),
        }

    except Exception as exc:
        state.errors.append(f"DebateAgent error: {exc}")
        state.debate_result = DebateResult(
            debate_summary=f"Debate failed: {exc}. Using clinical agent fallback."
        )
        if ca := getattr(state, "clinical_agent_output", None):
            state.accuracy_codes = {
                "icd10_codes": [c.model_dump() for c in ca.icd10_codes],
                "coding_notes": ca.agent_notes,
            }
        if ra := getattr(state, "revenue_agent_output", None):
            state.revenue_codes = {
                "cpt_codes": [c.model_dump() for c in ra.cpt_codes],
                "hcpcs_codes": [c.model_dump() for c in ra.hcpcs_codes],
                "missed_billable_services": ra.missed_services,
            }
    return state
