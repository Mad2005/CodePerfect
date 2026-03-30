"""
Justification Agent  (comparison-aware)
────────────────────────────────────────
When human codes are available, Gemini is given BOTH the AI codes AND the human
codes and asked to:
  1. Explain why each AI code is clinically correct (or not).
  2. Directly compare each AI code to the corresponding human code.
  3. Give a verdict: ai_correct | human_correct | both_valid | both_wrong.
"""
from core.llm import call_gemini_json
from core.models import PipelineState, CodeJustification

SYSTEM = (
    "You are a certified professional coder (CPC) and coding educator. "
    "You analyse both AI-generated codes and human coder codes and provide "
    "authoritative justifications and comparison verdicts. "
    "Return ONLY valid JSON — no prose, no markdown fences."
)

# ── Prompt used when human codes ARE available ────────────────────────────────
COMPARISON_PROMPT = """
You are reviewing an AI medical coder's output against a human coder's codes.
For each code, determine which is correct, and justify your reasoning.

CLINICAL NOTE:
{note}

AI-ASSIGNED ICD-10 CODES: {ai_icd10}
HUMAN ICD-10 CODES:        {human_icd10}

AI-ASSIGNED CPT CODES:     {ai_cpt}
HUMAN CPT CODES:           {human_cpt}

AI-ASSIGNED HCPCS CODES:   {ai_hcpcs}
HUMAN HCPCS CODES:         {human_hcpcs}

DISCREPANCIES IDENTIFIED:
{discrepancies}

CODING GUIDELINES AVAILABLE:
{guidelines}

For EVERY unique code (from both AI and human), provide a justification entry.

Return JSON:
{{
  "justifications": [
    {{
      "code": "the code",
      "code_type": "ICD-10|CPT|HCPCS",
      "clinical_evidence": "specific text from the note supporting or refuting this code",
      "guideline_reference": "e.g. ICD-10-CM Guidelines Chapter 4, AMA CPT 2024",
      "explanation": "plain-language explanation of why this code is correct or incorrect",
      "human_code": "the corresponding human code (same code, different code, or null if no human equivalent)",
      "comparison_verdict": "ai_correct|human_correct|both_valid|both_wrong|no_comparison",
      "comparison_reasoning": "1-2 sentence explanation of why AI or human is right in this specific case"
    }}
  ]
}}

Verdict definitions:
  ai_correct    – documentation supports AI code; human code is wrong or missing
  human_correct – documentation supports human code; AI code is wrong or missing
  both_valid    – both codes are clinically acceptable for this encounter
  both_wrong    – neither code correctly reflects the documentation
  no_comparison – only one source coded this (the other did not)
"""

# ── Prompt used when NO human codes are available ─────────────────────────────
STANDARD_PROMPT = """
Provide detailed clinical justifications for the following assigned codes.

CLINICAL DOCUMENTATION:
{note}

CODES TO JUSTIFY:
ICD-10: {icd10_codes}
CPT: {cpt_codes}
HCPCS: {hcpcs_codes}

CODING GUIDELINES:
{guidelines}

Return JSON:
{{
  "justifications": [
    {{
      "code": "code value",
      "code_type": "ICD-10|CPT|HCPCS",
      "clinical_evidence": "specific text/data from the note supporting this code",
      "guideline_reference": "e.g. ICD-10-CM Guidelines Chapter 4, AMA CPT 2024",
      "explanation": "plain-language explanation of why this code is correct",
      "human_code": null,
      "comparison_verdict": "no_comparison",
      "comparison_reasoning": ""
    }}
  ]
}}
"""


def justification_agent(state: PipelineState) -> PipelineState:
    """LangGraph node: generates comparison-aware justifications."""
    try:
        has_human  = (state.comparison_result is not None
                      and state.comparison_result.has_human_input)
        guide_str  = "\n".join(state.retrieved_guidelines[:10])
        note_snip  = state.cleaned_text[:1800]

        if has_human:
            human  = state.human_code_input
            comp   = state.comparison_result

            ai_icd10  = ", ".join(c.get("code","") for c in state.accuracy_codes.get("icd10_codes",[]))
            ai_cpt    = ", ".join(c.get("code","") for c in state.revenue_codes.get("cpt_codes",   []))
            ai_hcpcs  = ", ".join(c.get("code","") for c in state.revenue_codes.get("hcpcs_codes", []))

            h_icd10 = ", ".join(h.code for h in human.icd10_codes) or "None"
            h_cpt   = ", ".join(h.code for h in human.cpt_codes)   or "None"
            h_hcpcs = ", ".join(h.code for h in human.hcpcs_codes) or "None"

            disc_lines = []
            for d in comp.discrepancies[:12]:
                disc_lines.append(
                    f"  [{d.discrepancy_type}] {d.code} ({d.code_type}): "
                    f"AI={d.ai_code or 'not coded'}, Human={d.human_code or 'not coded'} — {d.clinical_impact}"
                )
            disc_str = "\n".join(disc_lines) or "None"

            prompt = COMPARISON_PROMPT.format(
                note=note_snip,
                ai_icd10=ai_icd10 or "None",
                human_icd10=h_icd10,
                ai_cpt=ai_cpt or "None",
                human_cpt=h_cpt,
                ai_hcpcs=ai_hcpcs or "None",
                human_hcpcs=h_hcpcs,
                discrepancies=disc_str,
                guidelines=guide_str or "Standard coding guidelines apply",
            )
        else:
            icd10_str = ", ".join(c.get("code","") for c in state.accuracy_codes.get("icd10_codes",[]))
            cpt_str   = ", ".join(c.get("code","") for c in state.revenue_codes.get("cpt_codes",   []))
            hcpcs_str = ", ".join(c.get("code","") for c in state.revenue_codes.get("hcpcs_codes", []))

            prompt = STANDARD_PROMPT.format(
                note=note_snip,
                icd10_codes=icd10_str or "None",
                cpt_codes=cpt_str     or "None",
                hcpcs_codes=hcpcs_str or "None",
                guidelines=guide_str  or "Standard coding guidelines apply",
            )

        data = call_gemini_json(prompt, SYSTEM)
        justifications_data = data.get("justifications", [])
        
        # Fix any LLM field name mismatches (e.g., "justification" -> "explanation")
        for j in justifications_data:
            if "justification" in j and "explanation" not in j:
                j["explanation"] = j.pop("justification")
        
        # Validate and create CodeJustification objects with better error handling
        processed_justifications = []
        for j in justifications_data:
            try:
                processed_justifications.append(CodeJustification(**j))
            except Exception as e:
                # If creating one fails, log it but continue
                state.errors.append(f"Failed to create CodeJustification: {str(e)}, data: {j}")
                # Try to create a minimal valid justification
                try:
                    safe_j = {
                        "code": j.get("code", "UNKNOWN"),
                        "code_type": j.get("code_type", "ICD-10"),
                        "clinical_evidence": j.get("clinical_evidence", ""),
                        "guideline_reference": j.get("guideline_reference", ""),
                        "explanation": j.get("explanation", j.get("justification", "")),
                        "human_code": j.get("human_code"),
                        "comparison_verdict": j.get("comparison_verdict", "no_comparison"),
                        "comparison_reasoning": j.get("comparison_reasoning", ""),
                    }
                    processed_justifications.append(CodeJustification(**safe_j))
                except Exception as e2:
                    state.errors.append(f"Failed to create safe CodeJustification: {str(e2)}")
        
        state.justifications = processed_justifications

    except Exception as exc:
        state.errors.append(f"JustificationAgent error: {exc}")
        state.justifications = []
    return state
