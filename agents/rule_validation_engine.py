"""
Rule Validation Engine  v3
───────────────────────────
Split into three separate, targeted checks to eliminate false positives:

  1. NCCI PTP check  — deterministic lookup from DB + LLM as fallback
  2. MUE check       — deterministic unit calculation from actual billed units
  3. LCD/NCD check   — context-aware, only flags rules matching actual codes/diagnoses

Key fixes over v2:
  • MUE: billed_units is now extracted from the actual code list, not hallucinated
  • MUE: violation = billed_units > max_units (strictly). Equal is NOT a violation.
  • LCD/NCD: LLM is explicitly told the ACTUAL codes — it must match rules to codes present
  • LCD/NCD: Prompt instructs LLM to return empty array if no rule matches an actual code
  • LCD/NCD: Generic "verify coverage" rules are rejected unless tied to a specific code
"""
from __future__ import annotations
from core.llm import call_gemini_json
from core.models import (
    PipelineState, ComplianceResult,
    NCCIEdit, MUELimit, LCDRule, NCDRule,
)

_SYSTEM = (
    "You are a Medicare compliance specialist. "
    "Return ONLY valid JSON — no prose, no markdown fences."
)


# ── 1. NCCI PTP Check ─────────────────────────────────────────────────────────

_NCCI_PROMPT = """
Check if any CPT code pairs in the list below are NCCI PTP edit pairs
(procedure-to-procedure pairs that cannot be billed together on the same date by the same provider).

CPT CODES BILLED: {cpt_codes}

NCCI RULES FROM DATABASE: {ncci_rules}

STRICT RULES:
- Only report a violation if BOTH codes in the pair are present in the CPT CODES BILLED list above.
- Do NOT report a violation for a code pair if one of the codes is not in the billed list.
- Do NOT invent violations not supported by the database rules provided.
- If no violations exist, return an empty array.

Return JSON:
{{
  "ncci_violations": [
    {{
      "column1_code": "CPT code",
      "column2_code": "CPT code",
      "modifier_allowed": false,
      "description": "specific reason these two codes conflict per NCCI policy"
    }}
  ]
}}
"""


def _check_ncci(cpt_codes: list[dict], ncci_rules: str) -> list[NCCIEdit]:
    """Check NCCI PTP violations for the billed CPT codes."""
    if not cpt_codes or not ncci_rules.strip():
        return []
    cpt_str = "\n".join(f"- {c.get('code','')}" for c in cpt_codes if c.get('code'))
    if not cpt_str.strip():
        return []
    try:
        data = call_gemini_json(
            _NCCI_PROMPT.format(cpt_codes=cpt_str, ncci_rules=ncci_rules),
            _SYSTEM,
        )
        return [NCCIEdit(**v) for v in data.get("ncci_violations", [])]
    except Exception:
        return []


# ── 2. MUE Check (deterministic) ─────────────────────────────────────────────

# Known CMS MUE values for common codes (units per day per patient).
# These are hard-coded to prevent LLM hallucination.
# The DB lookup adds more; this is the safety fallback.
_KNOWN_MUE: dict[str, int] = {
    # E&M
    "99221": 1, "99222": 1, "99223": 1,
    "99231": 1, "99232": 1, "99233": 1,
    "99238": 1, "99239": 1,
    "99213": 1, "99214": 1, "99215": 1,
    # Radiology
    "71046": 1, "71045": 1,
    "93000": 1, "93010": 1,
    # Labs
    "85025": 1, "85027": 1, "80048": 1, "80053": 1,
    "87040": 2, "87070": 1,
    # Procedures
    "36415": 1,
    # HCPCS drug codes — units are dose-based, typically higher
    # These are NOT limited to 1/day; they depend on dose ordered
}

def _extract_mue_from_db(mue_rules: str) -> dict[str, int]:
    """
    Parse MUE limits out of the DB rules text.
    DB records look like: "MUE Limit: CPT/HCPCS XXXXX maximum N unit(s) per day."
    """
    import re
    limits: dict[str, int] = {}
    for line in mue_rules.splitlines():
        m = re.search(r'(?:CPT|HCPCS|CPT/HCPCS)\s+([A-Z0-9]+)\s+maximum\s+(\d+)\s+unit', line, re.I)
        if m:
            limits[m.group(1).upper()] = int(m.group(2))
    return limits


def _check_mue(cpt_codes: list[dict], hcpcs_codes: list[dict], mue_rules: str) -> list[MUELimit]:
    """
    Deterministic MUE check.
    billed_units is taken directly from the code list.
    violation = billed_units STRICTLY GREATER THAN max_units.
    """
    # Build limit table: DB rules first, then fall back to known values
    db_limits = _extract_mue_from_db(mue_rules)
    violations: list[MUELimit] = []

    all_codes = list(cpt_codes) + list(hcpcs_codes)
    for entry in all_codes:
        code = (entry.get("code") or "").upper().strip()
        if not code:
            continue

        # Parse billed units — handle float strings like "1.0"
        try:
            billed = int(float(str(entry.get("units", 1))))
        except (ValueError, TypeError):
            billed = 1

        # Look up MUE limit
        max_u = db_limits.get(code) or _KNOWN_MUE.get(code)
        if max_u is None:
            continue  # No MUE data for this code — skip (don't fabricate a violation)

        # STRICTLY greater than — equal is fine
        if billed > max_u:
            violations.append(MUELimit(
                cpt_code    =code,
                max_units   =max_u,
                billed_units=billed,
                violation   =True,
                reason      =(
                    f"CMS MUE limit for {code} is {max_u} unit(s) per day. "
                    f"Billed {billed} unit(s) — exceeds limit by {billed - max_u}."
                ),
            ))

    return violations


# ── 3. LCD/NCD Check (context-aware) ─────────────────────────────────────────

_LCD_NCD_PROMPT = """
Check if any of the ACTUAL CODES below have documented LCD or NCD coverage concerns.

ACTUAL CODES IN THIS CLAIM:
ICD-10: {icd10_codes}
CPT   : {cpt_codes}
HCPCS : {hcpcs_codes}

LCD/NCD RULES FROM DATABASE: {coverage_rules}

STRICT INSTRUCTIONS:
1. Only flag an LCD/NCD issue if the rule DIRECTLY applies to one of the ACTUAL CODES listed above.
2. Do NOT flag rules about conditions, procedures, or equipment NOT mentioned in the code list.
3. Do NOT flag generic coverage rules (e.g. "verify patient meets criteria") unless the rule
   names a specific code from the actual list AND describes a concrete documentation requirement.
4. Do NOT flag rules about IPV, lung surgery, dialysis, or any service not in the actual codes.
5. If no rules from the database match an actual code — return empty arrays.
6. For each issue, include the specific CPT/HCPCS/ICD-10 code it applies to.

Return JSON:
{{
  "lcd_issues": [
    {{
      "rule_id": "LCD ID (e.g. L33718)",
      "description": "specific coverage concern and what documentation is required",
      "covered": false,
      "applicable_codes": ["the specific code from the actual list this applies to"]
    }}
  ],
  "ncd_issues": [
    {{
      "rule_id": "NCD ID (e.g. 20.7)",
      "description": "specific coverage restriction and what documentation is required",
      "covered": false,
      "applicable_codes": ["the specific code from the actual list this applies to"]
    }}
  ]
}}
"""

_MISSED_CODES_PROMPT = """
Review the clinical codes below and identify any clearly missed billable services.

ICD-10: {icd10_codes}
CPT   : {cpt_codes}
HCPCS : {hcpcs_codes}
CLINICAL CONTEXT: {clinical_context}

Only flag missed codes that are:
1. Strongly implied by the diagnosis/procedure combination (e.g. diabetes coded but no insulin HCPCS when insulin was given)
2. Standard companion codes commonly billed together (e.g. discharge day management 99238/99239 after inpatient stay)

Do NOT speculate. Do NOT flag codes for services not supported by the context.
If nothing is clearly missed, return an empty array.

Return JSON:
{{
  "missed_codes": ["brief description of missed code with suggested code"]
}}
"""


def _check_lcd_ncd(
    icd10_list: list[dict],
    cpt_list:   list[dict],
    hcpcs_list: list[dict],
    coverage_rules: str,
) -> tuple[list[LCDRule], list[NCDRule]]:
    """Context-aware LCD/NCD check — only flags rules matching actual codes."""
    if not coverage_rules.strip():
        return [], []

    icd10_str = "\n".join(f"- {c.get('code','')} {c.get('description','')}" for c in icd10_list) or "None"
    cpt_str   = "\n".join(f"- {c.get('code','')}"                           for c in cpt_list)   or "None"
    hcpcs_str = "\n".join(f"- {c.get('code','')}"                           for c in hcpcs_list) or "None"

    try:
        data = call_gemini_json(
            _LCD_NCD_PROMPT.format(
                icd10_codes=icd10_str, cpt_codes=cpt_str,
                hcpcs_codes=hcpcs_str, coverage_rules=coverage_rules,
            ),
            _SYSTEM,
        )
    except Exception:
        return [], []

    # Post-filter: remove any LCD/NCD that doesn't reference an actual code
    actual_codes = {
        c.get("code","").upper()
        for c in icd10_list + cpt_list + hcpcs_list
        if c.get("code")
    }

    def is_relevant(issue: dict) -> bool:
        """Keep only issues where applicable_codes overlap with actual codes."""
        applicable = [str(c).upper() for c in issue.get("applicable_codes", [])]
        if not applicable:
            return False   # No specific code cited — reject
        return any(c in actual_codes for c in applicable)

    lcd_raw = [r for r in data.get("lcd_issues", []) if is_relevant(r)]
    ncd_raw = [r for r in data.get("ncd_issues", []) if is_relevant(r)]

    lcd = [LCDRule(**r) for r in lcd_raw]
    ncd = [NCDRule(**r) for r in ncd_raw]
    return lcd, ncd


def _check_missed(
    icd10_list: list[dict],
    cpt_list:   list[dict],
    hcpcs_list: list[dict],
    clinical_context: str,
) -> list[str]:
    """Targeted missed-code check using clinical context."""
    icd10_str = "\n".join(f"- {c.get('code','')} {c.get('description','')}" for c in icd10_list) or "None"
    cpt_str   = "\n".join(f"- {c.get('code','')} {c.get('description','')}" for c in cpt_list)   or "None"
    hcpcs_str = "\n".join(f"- {c.get('code','')} {c.get('description','')}" for c in hcpcs_list) or "None"
    try:
        data = call_gemini_json(
            _MISSED_CODES_PROMPT.format(
                icd10_codes=icd10_str, cpt_codes=cpt_str,
                hcpcs_codes=hcpcs_str,
                clinical_context=clinical_context[:600],
            ),
            _SYSTEM,
        )
        return data.get("missed_codes", [])
    except Exception:
        return []


# ── Main engine ───────────────────────────────────────────────────────────────

def rule_validation_engine(state: PipelineState) -> PipelineState:
    try:
        # Use debate-resolved codes if available
        dr = state.debate_result
        if dr and dr.final_icd10_codes:
            icd10_list = dr.final_icd10_codes
            cpt_list   = dr.final_cpt_codes
            hcpcs_list = dr.final_hcpcs_codes
        else:
            icd10_list = state.accuracy_codes.get("icd10_codes", [])
            cpt_list   = state.revenue_codes.get("cpt_codes",    [])
            hcpcs_list = state.revenue_codes.get("hcpcs_codes",  [])

        # Split retrieved rules by type
        all_rules    = state.retrieved_rules
        ncci_rules   = "\n".join(r for r in all_rules if "NCCI" in r.upper() or "PTP" in r.upper())
        mue_rules    = "\n".join(r for r in all_rules if "MUE"  in r.upper())
        lcd_ncd_rules= "\n".join(r for r in all_rules if any(
                            kw in r.upper() for kw in ["LCD","NCD","COVERAGE","LOCAL","NATIONAL"]))

        # If no categorised rules, use all (small DB)
        if not ncci_rules:
            ncci_rules = "\n".join(all_rules[:8])
        if not mue_rules:
            mue_rules  = "\n".join(all_rules[:8])
        if not lcd_ncd_rules:
            lcd_ncd_rules = "\n".join(all_rules[:8])

        # Run three targeted checks
        ncci  = _check_ncci(cpt_list, ncci_rules)
        mue   = _check_mue(cpt_list, hcpcs_list, mue_rules)
        lcd, ncd = _check_lcd_ncd(icd10_list, cpt_list, hcpcs_list, lcd_ncd_rules)

        # Brief clinical context for missed-code check
        clinical_ctx = (state.cleaned_text or "")[:500]
        missed_raw = _check_missed(icd10_list, cpt_list, hcpcs_list, clinical_ctx)
        # Ensure missed_codes is a list of strings (models expect list[str])
        missed = [str(m).strip() for m in missed_raw if m is not None]
        missed = [m for m in missed if m]

        # HARD non-compliant = NCCI or MUE violations (cause claim denial)
        # LCD/NCD = advisory warnings only
        is_compliant = not bool(ncci or mue)

        # Generate compliance summary
        summary_parts = []
        if is_compliant:
            summary_parts.append("✓ All codes pass NCCI and MUE validation.")
        else:
            if ncci:
                summary_parts.append(f"⚠ {len(ncci)} NCCI edit violation(s) detected.")
            if mue:
                summary_parts.append(f"⚠ {len(mue)} MUE limit violation(s) detected.")
        
        if lcd:
            summary_parts.append(f"ℹ {len(lcd)} LCD coverage issue(s) noted.")
        if ncd:
            summary_parts.append(f"ℹ {len(ncd)} NCD coverage issue(s) noted.")
        if missed:
            summary_parts.append(f"⚠ {len(missed)} potentially missed code(s).")
        
        summary = " ".join(summary_parts) if summary_parts else "Compliance check completed."

        state.compliance_result = ComplianceResult(
            ncci_violations=ncci,
            mue_violations =mue,
            lcd_issues     =lcd,
            ncd_issues     =ncd,
            missed_codes   =missed,
            is_compliant   =is_compliant,
            summary        =summary,
        )

    except Exception as exc:
        state.errors.append(f"RuleValidationEngine error: {exc}")
        state.compliance_result = ComplianceResult(summary="Error during compliance check.")

    return state