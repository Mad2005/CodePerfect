"""
Confidence Scoring Engine  — v2 (smarter formula)
───────────────────────────────────────────────────
Confidence formula rationale
─────────────────────────────
  intrinsic       = LLM self-reported confidence (validated by debate agreement)
  debate_boost    = consensus between clinical and revenue agents (external validation)
  comparison_adj  = human match rate used as a PENALTY signal only, not a primary driver
                    because AI coding MORE codes than human does not mean AI is wrong

  per_type_conf   = 0.70 * intrinsic  +  0.20 * debate_agreement  +  0.10 * human_match
  overall         = weighted average of per-type scores (ICD-10 weighted highest)

Risk score formula
───────────────────
  Each source contributes independently but is CAPPED per category so a
  single bad category cannot saturate the entire score.
  Category caps:
    NCCI/MUE violations  → max 0.25
    LCD/NCD issues       → max 0.15
    Audit findings       → max 0.25
    Comparison mismatches→ max 0.15
    Debate conflicts     → max 0.10
    Non-compliance flag  → 0.10 flat
"""
from core.models import PipelineState, ConfidenceScore
from config.settings import HIGH_RISK_THRESHOLD, MEDIUM_RISK_THRESHOLD


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0

def _risk_label(score: float) -> str:
    if score >= HIGH_RISK_THRESHOLD:   return "high"
    if score >= MEDIUM_RISK_THRESHOLD: return "medium"
    return "low"

def _capped(value: float, cap: float) -> float:
    return min(value, cap)


def confidence_scoring_engine(state: PipelineState) -> PipelineState:
    try:
        dr = state.debate_result

        # ── 1. Intrinsic per-type confidence (from debate final / fallback) ───
        if dr and dr.final_icd10_codes:
            icd10_raw = [c.get("confidence", 0.0) for c in dr.final_icd10_codes]
        else:
            icd10_raw = [c.get("confidence", 0.0) for c in state.accuracy_codes.get("icd10_codes", [])]

        if dr and dr.final_cpt_codes:
            cpt_raw = [c.get("confidence", 0.0) for c in dr.final_cpt_codes]
        else:
            cpt_raw = [c.get("confidence", 0.0) for c in state.revenue_codes.get("cpt_codes", [])]

        if dr and dr.final_hcpcs_codes:
            hcpcs_raw = [c.get("confidence", 0.0) for c in dr.final_hcpcs_codes]
        else:
            hcpcs_raw = [c.get("confidence", 0.0) for c in state.revenue_codes.get("hcpcs_codes", [])]

        # Normalize raw LLM confidences:
        # - If the model reports a max confidence > 1.0 (e.g. '200% sure'),
        #   scale all confidences by dividing by that max so the strongest
        #   becomes 1.0 and others are proportional.
        # - Otherwise cap individual confidences at 0.95 to avoid showing
        #   unrealistic 100% certainty from a single model source.
        def _process_raw(raw: list[float], default_if_empty: float | None = 0.0) -> float:
            vals = []
            for v in raw:
                try:
                    fv = float(v)
                except Exception:
                    continue
                vals.append(fv)
            if not vals:
                return default_if_empty if default_if_empty is not None else 0.0
            maxv = max(vals)
            if maxv > 1.0:
                # scale so max -> 1.0, others proportionally
                norm = [min(1.0, v / maxv) for v in vals]
            else:
                # cap to 0.95 to avoid 100% claims
                norm = [min(v, 0.95) for v in vals]
            return _avg(norm)

        intr_icd10 = _process_raw(icd10_raw, default_if_empty=0.0)
        intr_cpt   = _process_raw(cpt_raw,   default_if_empty=0.0)
        intr_hcpcs = _process_raw(hcpcs_raw, default_if_empty=1.0)

        # ── 2. Debate agreement boost ─────────────────────────────────────────
        # How much did the two agents agree after debate? 
        # High agreement = both agents saw the same evidence = higher confidence.
        if dr and (dr.clinical_wins + dr.revenue_wins + dr.consensus_codes) > 0:
            total = dr.clinical_wins + dr.revenue_wins + dr.consensus_codes
            debate_agreement = dr.consensus_codes / total
        else:
            debate_agreement = 1.0  # no conflicts = perfect agreement

        clinical_vs_revenue_agreement = round(debate_agreement, 3)

        # ── 3. Comparison adjustment (penalty signal only) ────────────────────
        # Human match rate is used as a SMALL penalty when AI and human diverge.
        # AI coding MORE codes than human is not penalised — only MISSING human
        # codes is penalised (captured by human_accuracy_vs_ai, not match rate).
        comp = state.comparison_result
        has_comparison = comp is not None and comp.has_human_input

        if has_comparison:
            s = comp.summary
            # Penalty = how many human codes AI missed (human_only discrepancies)
            human_miss_penalty_icd10  = 1.0 - (s.human_only_codes / max(s.total_human_codes, 1)) * 0.5
            human_miss_penalty_cpt    = 1.0 - (s.human_only_codes / max(s.total_human_codes, 1)) * 0.5
            human_miss_penalty_hcpcs  = 1.0 - (s.human_only_codes / max(s.total_human_codes, 1)) * 0.3
            # Clamp between 0.5 and 1.0 — human completeness at most halves the score
            hmp_icd10  = max(0.5, human_miss_penalty_icd10)
            hmp_cpt    = max(0.5, human_miss_penalty_cpt)
            hmp_hcpcs  = max(0.5, human_miss_penalty_hcpcs)

            comparison_confidence = round(s.overall_match_rate, 3)
            human_agreement_rate  = round(s.ai_accuracy_vs_human, 3)
        else:
            hmp_icd10 = hmp_cpt = hmp_hcpcs = 1.0
            comparison_confidence = 0.0
            human_agreement_rate  = 0.0

        # ── 4. Blended per-type confidence ────────────────────────────────────
        # Formula: 70% intrinsic LLM + 20% debate agreement + 10% human penalty
        icd10_conf = round(0.70 * intr_icd10 + 0.20 * debate_agreement + 0.10 * hmp_icd10,  3)
        cpt_conf   = round(0.70 * intr_cpt   + 0.20 * debate_agreement + 0.10 * hmp_cpt,    3)
        hcpcs_conf = round(0.70 * intr_hcpcs + 0.20 * debate_agreement + 0.10 * hmp_hcpcs,  3)

        # Overall: ICD-10 weighted 45% (most clinically critical),
        #          CPT 35%, HCPCS 20%
        # If a code type is not present (no final codes), exclude it from
        # the overall weighting and renormalise the remaining weights.
        # Determine which types are present in the final output.
        has_icd = bool((dr and dr.final_icd10_codes) or state.accuracy_codes.get("icd10_codes"))
        has_cpt = bool((dr and dr.final_cpt_codes) or state.revenue_codes.get("cpt_codes"))
        has_hcpcs = bool((dr and dr.final_hcpcs_codes) or state.revenue_codes.get("hcpcs_codes"))

        weights = {
            "icd": 0.45,
            "cpt": 0.35,
            "hcpcs": 0.20,
        }
        available = []
        if has_icd:
            available.append((icd10_conf, weights["icd"]))
        if has_cpt:
            available.append((cpt_conf, weights["cpt"]))
        if has_hcpcs:
            available.append((hcpcs_conf, weights["hcpcs"]))

        if not available:
            overall = round(icd10_conf, 3)
        else:
            total_w = sum(w for _, w in available)
            overall = round(sum(v * (w / total_w) for v, w in available), 3)

        # ── 5. Compliance risk score (capped per category) ────────────────────
        compliance = state.compliance_result
        risk_ncci  = 0.0
        risk_lcd   = 0.0
        risk_audit = 0.0
        risk_comp  = 0.0
        risk_debate= 0.0
        risk_flag  = 0.0

        if compliance:
            risk_ncci = (len(compliance.ncci_violations) * 0.10 +
                         len(compliance.mue_violations)  * 0.07)
            risk_lcd  = (len(compliance.lcd_issues)  * 0.05 +
                         len(compliance.ncd_issues)  * 0.05 +
                         len(compliance.missed_codes) * 0.03)
            if not compliance.is_compliant:
                risk_flag = 0.10

        for finding in state.audit_findings:
            if   finding.severity == "high":   risk_audit += 0.12
            elif finding.severity == "medium":  risk_audit += 0.06
            else:                              risk_audit += 0.02

        if has_comparison:
            for d in comp.discrepancies:
                # Only penalise human_only discrepancies (AI missed a code the human got)
                if d.discrepancy_type == "human_only":
                    if   d.severity == "high":   risk_comp += 0.08
                    elif d.severity == "medium":  risk_comp += 0.04
                    else:                        risk_comp += 0.01

        if dr:
            # Only debate points where neither agent won (both wrong / unresolved)
            neither_count = sum(1 for p in dr.debate_points if p.winning_agent == "neither")
            risk_debate = neither_count * 0.04

        # Apply caps per category
        risk = (
            _capped(risk_ncci,   0.25) +
            _capped(risk_lcd,    0.15) +
            _capped(risk_audit,  0.25) +
            _capped(risk_comp,   0.15) +
            _capped(risk_debate, 0.10) +
            risk_flag
        )
        risk = round(min(risk, 1.0), 3)

        # Debate resolution rate = % of debate points resolved cleanly
        if dr and dr.debate_points:
            resolved = sum(1 for p in dr.debate_points if p.winning_agent != "neither")
            debate_resolution_rate = round(resolved / len(dr.debate_points), 3)
        else:
            debate_resolution_rate = 1.0

        state.confidence_scores = ConfidenceScore(
            overall_coding_confidence=overall,
            icd10_confidence=icd10_conf,
            cpt_confidence=cpt_conf,
            hcpcs_confidence=hcpcs_conf,
            compliance_risk_score=risk,
            risk_level=_risk_label(risk),
            comparison_confidence=comparison_confidence,
            human_agreement_rate=human_agreement_rate,
            comparison_available=has_comparison,
            clinical_vs_revenue_agreement=clinical_vs_revenue_agreement,
            debate_resolution_rate=debate_resolution_rate,
        )

    except Exception as exc:
        state.errors.append(f"ConfidenceScoringEngine error: {exc}")
        state.confidence_scores = ConfidenceScore(
            overall_coding_confidence=0.0,
            icd10_confidence=0.0,
            cpt_confidence=0.0,
            hcpcs_confidence=0.0,
            compliance_risk_score=1.0,
            risk_level="high",
        )
    return state
