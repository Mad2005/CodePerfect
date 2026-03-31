"""
Auditor Agent
──────────────
Detects upcoding, downcoding, missing codes, and high-risk discrepancies.
Compares human-typical coding patterns against AI-assigned codes.
"""
from core.llm import call_gemini_json
from core.models import PipelineState, AuditFinding

SYSTEM = (
    "You are a senior medical coding auditor specialising in Medicare compliance and OIG guidelines. "
    "Return ONLY valid JSON — no prose, no markdown fences."
)

AUDIT_PROMPT = """
Conduct a thorough coding audit for potential upcoding, downcoding, and compliance risks.

CLINICAL DOCUMENTATION SUMMARY:
{note}

ASSIGNED ICD-10 CODES:
{icd10_codes}

ASSIGNED CPT CODES:
{cpt_codes}

COMPLIANCE ISSUES DETECTED:
{compliance_summary}

AUDIT TASK:
1. UPCODING CHECK – Are any codes higher-complexity or higher-paying than documentation supports?
2. DOWNCODING CHECK – Are any codes lower-complexity than what is clearly documented?
3. MISSING CODE CHECK – Are there diagnoses or procedures clearly documented but not coded?
4. INCORRECT CODE CHECK – Are any codes factually wrong for the documented condition?
5. HIGH-RISK FLAGS – Flag any combinations that have high OIG or RAC audit risk.

For each finding, assign severity: "high", "medium", or "low".

Return JSON:
{{
  "audit_findings": [
    {{
      "finding_type": "upcoding|downcoding|missing|incorrect|high_risk",
      "code": "the code in question",
      "description": "what the finding is",
      "severity": "high|medium|low",
      "recommendation": "what should be done"
    }}
  ],
  "overall_audit_risk": "low|medium|high",
  "audit_summary": "2-3 sentence executive summary of audit findings"
}}
"""


def auditor_agent(state: PipelineState) -> PipelineState:
    """LangGraph node: audits for upcoding, downcoding, and coding errors."""
    try:
        icd10_list = state.accuracy_codes.get("icd10_codes", [])
        cpt_list   = state.revenue_codes.get("cpt_codes", [])
        compliance = state.compliance_result

        icd10_str  = "\n".join(f"- {c.get('code')} {c.get('description','')}" for c in icd10_list)
        cpt_str    = "\n".join(f"- {c.get('code')} {c.get('description','')}" for c in cpt_list)

        compliance_summary = "No compliance issues detected."
        if compliance:
            parts = []
            if compliance.ncci_violations:
                parts.append(f"NCCI violations: {len(compliance.ncci_violations)}")
            if compliance.mue_violations:
                parts.append(f"MUE violations: {len(compliance.mue_violations)}")
            if compliance.lcd_issues:
                parts.append(f"LCD issues: {len(compliance.lcd_issues)}")
            if compliance.ncd_issues:
                parts.append(f"NCD issues: {len(compliance.ncd_issues)}")
            if compliance.missed_codes:
                parts.append(f"Missed codes: {len(compliance.missed_codes)}")
            if parts:
                compliance_summary = "; ".join(parts)

        prompt = AUDIT_PROMPT.format(
            note=state.cleaned_text[:1500],
            icd10_codes=icd10_str  or "None assigned",
            cpt_codes=cpt_str      or "None assigned",
            compliance_summary=compliance_summary,
        )
        data = call_gemini_json(prompt, SYSTEM)

        state.audit_findings = [AuditFinding(**f) for f in data.get("audit_findings", [])]
        # Store audit summary in a temporary attribute for report generation
        state.__dict__["_audit_summary"] = data.get("audit_summary", "")
        state.__dict__["_audit_risk"]    = data.get("overall_audit_risk", "low")
    except Exception as exc:
        state.errors.append(f"AuditorAgent error: {exc}")
        state.audit_findings = []
    return state
