"""
AI vs Human Code Comparison Engine  (fixed counting)

Root causes of duplicate counts:
  - total_union used set() but AI codes from debate had duplicates across
    accuracy_codes and revenue_codes
  - human codes from CSV upload weren't being passed to pipeline state correctly

Fixes:
  - Use final debate codes (not raw agent outputs) for AI side
  - Deduplicate AI codes before comparison
  - Count matched = exact same code present on both sides (no double counting)
"""
from __future__ import annotations
from core.models import (
    PipelineState, ComparisonResult, ComparisonSummary,
    CodeMatch, CodeDiscrepancy, HumanCode,
)


def _norm(code: str) -> str:
    return code.strip().upper().replace(" ", "")


def _mr(matched: int, total: int) -> float:
    return round(matched / total, 3) if total > 0 else 1.0


def _get_final_ai_codes(state: PipelineState) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Always use debate-resolved final codes for comparison.
    Falls back to individual agent outputs if debate didn't run.
    Deduplicates by code value.
    """
    dr = state.debate_result

    def dedup(codes: list[dict]) -> list[dict]:
        seen, out = set(), []
        for c in codes:
            k = _norm(c.get("code", ""))
            if k and k not in seen:
                seen.add(k)
                out.append(c)
        return out

    if dr and dr.final_icd10_codes:
        icd10 = dedup(dr.final_icd10_codes)
    else:
        icd10 = dedup(state.accuracy_codes.get("icd10_codes", []))

    if dr and dr.final_cpt_codes:
        cpt = dedup(dr.final_cpt_codes)
    else:
        cpt = dedup(state.revenue_codes.get("cpt_codes", []))

    if dr and dr.final_hcpcs_codes:
        hcpcs = dedup(dr.final_hcpcs_codes)
    else:
        hcpcs = dedup(state.revenue_codes.get("hcpcs_codes", []))

    return icd10, cpt, hcpcs


def _compare_lists(
    ai_codes: list[dict],
    human_codes: list[HumanCode],
    code_type: str,
) -> tuple[list[CodeMatch], list[CodeDiscrepancy]]:
    matches: list[CodeMatch]       = []
    discs:   list[CodeDiscrepancy] = []

    ai_map    = {_norm(c.get("code", "")): c for c in ai_codes    if c.get("code")}
    human_map = {_norm(h.code): h            for h in human_codes if h.code}
    all_codes = sorted(set(ai_map) | set(human_map))

    for code in all_codes:
        ai    = ai_map.get(code)
        human = human_map.get(code)

        if ai and human:
            ai_u = int(str(ai.get("units", 1)).split(".")[0])
            hu_u = int(str(human.units or 1).split(".")[0])
            if ai_u == hu_u:
                matches.append(CodeMatch(
                    code=code, code_type=code_type,
                    description=ai.get("description", human.description or ""),
                    ai_confidence=float(ai.get("confidence", 0.0)),
                ))
            else:
                discs.append(CodeDiscrepancy(
                    code=code, code_type=code_type,
                    discrepancy_type="units_mismatch",
                    ai_code=code, ai_description=ai.get("description",""),
                    human_code=code, human_description=human.description or "",
                    ai_units=ai_u, human_units=hu_u, severity="medium",
                    clinical_impact=f"Units differ: AI billed {ai_u}, human billed {hu_u}.",
                ))
        elif ai and not human:
            discs.append(CodeDiscrepancy(
                code=code, code_type=code_type,
                discrepancy_type="ai_only",
                ai_code=code, ai_description=ai.get("description",""),
                human_code=None, human_description="Not coded by human",
                ai_units=int(str(ai.get("units",1)).split(".")[0]), human_units=0,
                severity="medium",
                clinical_impact=f"AI coded {code} — human did not. Verify documentation.",
            ))
        else:
            discs.append(CodeDiscrepancy(
                code=code, code_type=code_type,
                discrepancy_type="human_only",
                ai_code=None, ai_description="Not coded by AI",
                human_code=code, human_description=human.description or "",
                ai_units=0, human_units=int(str(human.units or 1).split(".")[0]),
                severity="high",
                clinical_impact=f"Human coded {code} — AI missed it. Review documentation.",
            ))

    return matches, discs


def _unique_human_count(human_codes: list[HumanCode]) -> int:
    """Count unique human codes after normalization to align with comparison maps."""
    return len({_norm(h.code) for h in human_codes if h.code})


def comparison_engine(state: PipelineState) -> PipelineState:
    human_input = state.human_code_input
    if not human_input:
        state.comparison_result = ComparisonResult(has_human_input=False)
        return state

    try:
        ai_icd10, ai_cpt, ai_hcpcs = _get_final_ai_codes(state)

        m_icd, d_icd   = _compare_lists(ai_icd10, human_input.icd10_codes, "ICD-10")
        m_cpt, d_cpt   = _compare_lists(ai_cpt,   human_input.cpt_codes,   "CPT")
        m_hcpcs,d_hcpcs= _compare_lists(ai_hcpcs, human_input.hcpcs_codes, "HCPCS")

        all_matches = m_icd + m_cpt + m_hcpcs
        all_discs   = d_icd + d_cpt + d_hcpcs

        # Counts — no duplication:
        # total_ai    = unique AI codes (after dedup)
        # total_human = unique human codes
        # exact_matches = codes present on BOTH sides (same code, same units)
        total_ai    = len(ai_icd10) + len(ai_cpt) + len(ai_hcpcs)
        total_human = (
            _unique_human_count(human_input.icd10_codes) +
            _unique_human_count(human_input.cpt_codes) +
            _unique_human_count(human_input.hcpcs_codes)
        )
        exact_match = len(all_matches)
        ai_only     = sum(1 for d in all_discs if d.discrepancy_type == "ai_only")
        human_only  = sum(1 for d in all_discs if d.discrepancy_type == "human_only")
        unit_diff   = sum(1 for d in all_discs if d.discrepancy_type == "units_mismatch")

        # Match rates — based on union (avoid dividing by wrong denominator)
        icd_union   = len(set([_norm(c.get("code","")) for c in ai_icd10] +
                              [_norm(h.code) for h in human_input.icd10_codes]))
        cpt_union   = len(set([_norm(c.get("code","")) for c in ai_cpt] +
                              [_norm(h.code) for h in human_input.cpt_codes]))
        hcpcs_union = len(set([_norm(c.get("code","")) for c in ai_hcpcs] +
                              [_norm(h.code) for h in human_input.hcpcs_codes]))

        summary = ComparisonSummary(
            total_ai_codes    =total_ai,
            total_human_codes =total_human,
            exact_matches     =exact_match,
            ai_only_codes     =ai_only,
            human_only_codes  =human_only,
            discrepancies     =unit_diff,
            # Match rate = matched / union (codes that either side coded)
            icd10_match_rate  =_mr(len(m_icd),   icd_union),
            cpt_match_rate    =_mr(len(m_cpt),   cpt_union),
            hcpcs_match_rate  =_mr(len(m_hcpcs), hcpcs_union),
            overall_match_rate=_mr(exact_match,  icd_union+cpt_union+hcpcs_union),
            # AI accuracy = what % of human codes did AI also code correctly
            ai_accuracy_vs_human=_mr(exact_match, total_human),
            # Human agreement = what % of AI codes did human also code
            human_accuracy_vs_ai=_mr(exact_match, total_ai),
        )

        state.comparison_result = ComparisonResult(
            matched_codes=all_matches,
            discrepancies=all_discs,
            summary=summary,
            has_human_input=True,
        )

    except Exception as exc:
        state.errors.append(f"ComparisonEngine error: {exc}")
        state.comparison_result = ComparisonResult(has_human_input=False)

    return state