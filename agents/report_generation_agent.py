"""
Report Generation Agent  (debate-aware)
────────────────────────────────────────
Assembles FinalCodingReport including per-agent outputs and debate resolution.
"""
from core.models import PipelineState, FinalCodingReport


def report_generation_agent(state: PipelineState) -> PipelineState:
    try:
        dr = state.debate_result

        def _num_conf(value, default: float = 0.0) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        # Use debate-resolved final codes if available, else fall back
        if dr and dr.final_icd10_codes:
            icd10_codes = [
                {"code": c.get("code",""), "description": c.get("description",""),
                 "type": c.get("sequence_type",""), "confidence": _num_conf(c.get("confidence", 0.0))}
                for c in dr.final_icd10_codes
            ]
        else:
            icd10_codes = [
                {"code": c.get("code",""), "description": c.get("description",""),
                 "type": c.get("sequence_type", c.get("code_type","")),
                 "confidence": _num_conf(c.get("confidence", 0.0))}
                for c in state.accuracy_codes.get("icd10_codes", [])
            ]

        if dr and dr.final_cpt_codes:
            cpt_codes = [
                {"code": c.get("code",""), "description": c.get("description",""),
                 "units": str(c.get("units",1)), "confidence": _num_conf(c.get("confidence", 0.0))}
                for c in dr.final_cpt_codes
            ]
        else:
            cpt_codes = [
                {"code": c.get("code",""), "description": c.get("description",""),
                 "units": str(c.get("units",1)), "confidence": _num_conf(c.get("confidence", 0.0))}
                for c in state.revenue_codes.get("cpt_codes", [])
            ]

        if dr and dr.final_hcpcs_codes:
            hcpcs_codes = [
                {"code": c.get("code",""), "description": c.get("description",""),
                 "category": c.get("category",""), "units": str(c.get("units",1)),
                 "confidence": _num_conf(c.get("confidence", 0.0))}
                for c in dr.final_hcpcs_codes
            ]
        else:
            hcpcs_codes = [
                {"code": c.get("code",""), "description": c.get("description",""),
                 "category": c.get("category",""), "units": str(c.get("units",1)),
                 "confidence": _num_conf(c.get("confidence", 0.0))}
                for c in state.revenue_codes.get("hcpcs_codes", [])
            ]

        # ── Recommendations ───────────────────────────────────────────────────
        recommendations: list[str] = []
        if state.compliance_result:
            if state.compliance_result.missed_codes:
                recommendations.append(
                    f"Consider missed codes: {', '.join(state.compliance_result.missed_codes[:5])}")
            if not state.compliance_result.is_compliant:
                recommendations.append("Resolve compliance violations before claim submission.")
        for svc in state.revenue_codes.get("missed_billable_services", [])[:3]:
            recommendations.append(f"Revenue opportunity: {svc}")
        for finding in state.audit_findings:
            if finding.severity == "high":
                recommendations.append(f"HIGH RISK – {finding.recommendation}")
        comp = state.comparison_result
        if comp and comp.has_human_input:
            for d in comp.discrepancies:
                if d.discrepancy_type == "human_only":
                    recommendations.append(
                        f"Human coded {d.code} ({d.code_type}) — AI missed, verify documentation.")
                elif d.discrepancy_type == "ai_only":
                    recommendations.append(
                        f"AI coded {d.code} ({d.code_type}) — human missed, review for overcoding.")
                elif d.discrepancy_type == "units_mismatch":
                    recommendations.append(
                        f"Units mismatch {d.code}: AI={d.ai_units} Human={d.human_units}.")

        audit_summary = getattr(state, "_audit_summary", "") or (
            "Automated audit completed. Review all high-severity findings before submission."
        )
        if dr and dr.debate_summary:
            audit_summary = dr.debate_summary + "\n\n" + audit_summary

        state.final_report = FinalCodingReport(
            patient_note_excerpt=state.cleaned_text[:1500] + (
    "\n\n[Note truncated — full text processed by pipeline]"
       if len(state.cleaned_text) > 1500 else ""),
            clinical_agent_codes=state.clinical_agent_output,
            revenue_agent_codes =state.revenue_agent_output,
            debate_result=dr,
            icd10_codes=icd10_codes,
            cpt_codes=cpt_codes,
            hcpcs_codes=hcpcs_codes,
            human_code_input=state.human_code_input,
            comparison_result=comp,
            compliance_result=state.compliance_result,
            audit_findings=state.audit_findings,
            justifications=state.justifications,
            confidence_scores=state.confidence_scores,
            audit_summary=audit_summary,
            recommendations=recommendations,
        )
    except Exception as exc:
        state.errors.append(f"ReportGenerationAgent error: {exc}")
    return state
