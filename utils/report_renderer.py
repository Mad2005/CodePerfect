"""
Console Report Renderer  (debate-aware + comparison-aware)
Fix 1: Risk score bar uses inverted color (high risk = red, low risk = green)
Fix 2: Compliance violations explicitly shown in audit findings with explanations
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from core.models import FinalCodingReport, AgentCodeSet, DebateResult, ComplianceResult

console = Console()

VERDICT_STYLE = {
    "ai_correct"   : ("✅ AI Correct",    "green"),
    "human_correct": ("⚠️  Human Correct", "yellow"),
    "both_valid"   : ("🤝 Both Valid",     "cyan"),
    "both_wrong"   : ("❌ Both Wrong",     "red"),
    "no_comparison": ("➖ No Comparison",  "dim"),
}
DISC_TYPE_LABEL = {
    "ai_only"       : ("AI Only",       "blue"),
    "human_only"    : ("Human Only",    "yellow"),
    "units_mismatch": ("Units Differ",  "magenta"),
    "code_mismatch" : ("Code Mismatch", "red"),
}
WINNER_STYLE = {
    "clinical": ("🏥 Clinical", "cyan"),
    "revenue" : ("💰 Revenue",  "green"),
    "both"    : ("🤝 Consensus","blue"),
    "neither" : ("❌ Neither",  "red"),
}


def _risk_color(level: str) -> str:
    return {"low": "green", "medium": "yellow", "high": "red"}.get(level.lower(), "white")


def _bar(score: float, width: int = 20, reverse: bool = False) -> Text:
    """
    Render a progress bar.
    reverse=False (default): high score = green  (for confidence — high is good)
    reverse=True           : high score = red    (for risk      — high is bad)
    """
    filled = int(score * width)
    if reverse:
        # High value = bad → red; low value = good → green
        color = "red" if score >= 0.70 else "yellow" if score >= 0.40 else "green"
    else:
        color = "green" if score >= 0.75 else "yellow" if score >= 0.50 else "red"
    t = Text()
    t.append("█" * filled + "░" * (width - filled), style=color)
    t.append(f" {score * 100:.1f}%", style="bold " + color)
    return t


def _compliance_audit_rows(comp: ComplianceResult) -> list[tuple]:
    """
    Convert every compliance violation into an explicit audit finding row.
    Returns list of (finding_type, code, description, severity_text, severity_color, recommendation)
    """
    rows = []

    for v in comp.ncci_violations:
        rows.append((
            "NCCI Edit",
            f"{v.column1_code} + {v.column2_code}",
            f"These two CPT codes cannot be billed together. {v.description}",
            "HIGH", "red",
            f"Remove or apply appropriate modifier. Modifier allowed: {'Yes' if v.modifier_allowed else 'No'}",
        ))

    for v in comp.mue_violations:
        rows.append((
            "MUE Limit",
            v.cpt_code,
            f"Billed {v.billed_units} unit(s) but CMS limit is {v.max_units} per day. {v.reason}",
            "HIGH", "red",
            f"Reduce units to {v.max_units} or split across separate claim lines with different dates.",
        ))

    for v in comp.lcd_issues:
        rows.append((
            "LCD Issue",
            ", ".join(v.applicable_codes) or "—",
            f"LCD {v.rule_id}: {v.description}",
            "MEDIUM", "yellow",
            "Ensure clinical documentation meets local coverage criteria before submitting claim.",
        ))

    for v in comp.ncd_issues:
        rows.append((
            "NCD Issue",
            ", ".join(v.applicable_codes) or "—",
            f"NCD {v.rule_id}: {v.description}",
            "MEDIUM", "yellow",
            "Verify patient meets national coverage criteria. Obtain ABN if coverage is uncertain.",
        ))

    for code in comp.missed_codes:
        rows.append((
            "Missed Code",
            "—",
            f"Potentially billable service not coded: {code}",
            "LOW", "green",
            "Review documentation and add code if supported.",
        ))

    return rows


def _render_agent_codes(agent: AgentCodeSet, border: str) -> None:
    rows_icd   = [(c.code, c.description, c.sequence_type,
                   f"{c.confidence*100:.0f}%", c.rationale[:60])
                  for c in agent.icd10_codes]
    rows_cpt   = [(c.code, c.description, str(c.units),
                   f"{c.confidence*100:.0f}%", c.rationale[:60])
                  for c in agent.cpt_codes]
    rows_hcpcs = [(c.code, c.description, c.category, str(c.units))
                  for c in agent.hcpcs_codes]

    if rows_icd:
        t = Table(title=f"{agent.agent_name} — ICD-10 Codes",
                  box=box.SIMPLE_HEAD, border_style=border, show_lines=False)
        t.add_column("Code",        style="bold yellow", width=10)
        t.add_column("Description", style="white",       width=42)
        t.add_column("Type",        style="dim",         width=12)
        t.add_column("Conf",        style="green",       width=6)
        t.add_column("Rationale",   style="dim",         width=55)
        for r in rows_icd:
            t.add_row(*r)
        console.print(t)

    if rows_cpt:
        t = Table(title=f"{agent.agent_name} — CPT Codes",
                  box=box.SIMPLE_HEAD, border_style=border, show_lines=False)
        t.add_column("Code",        style="bold yellow", width=10)
        t.add_column("Description", style="white",       width=45)
        t.add_column("Units",       style="cyan",        width=6)
        t.add_column("Conf",        style="green",       width=6)
        t.add_column("Rationale",   style="dim",         width=52)
        for r in rows_cpt:
            t.add_row(*r)
        console.print(t)

    if rows_hcpcs:
        t = Table(title=f"{agent.agent_name} — HCPCS Codes",
                  box=box.SIMPLE_HEAD, border_style=border, show_lines=False)
        t.add_column("Code",        style="bold yellow", width=10)
        t.add_column("Description", style="white",       width=45)
        t.add_column("Category",    style="dim",         width=10)
        t.add_column("Units",       style="cyan",        width=6)
        for r in rows_hcpcs:
            t.add_row(*r)
        console.print(t)

    if agent.agent_notes:
        console.print(Panel(agent.agent_notes,
                            title=f"[dim]{agent.agent_name} Notes[/]",
                            border_style="dim", padding=(0, 2)))


def _render_debate(dr: DebateResult) -> None:
    # debate_points now contains ONLY actual conflicts (consensus already filtered out)
    conflicts = dr.debate_points
    neither   = [p for p in conflicts if p.winning_agent == "neither"]

    sb = Table(box=None, show_header=False, padding=(0, 3))
    sb.add_column("", style="dim",  width=32)
    sb.add_column("", style="bold", width=8)
    sb.add_row("🤝 Codes both agents agreed on",    str(dr.consensus_codes))
    sb.add_row("⚖️  Actual conflicts resolved",      str(len(conflicts)))
    sb.add_row("🏥 Clinical agent won",              str(dr.clinical_wins))
    sb.add_row("💰 Revenue agent won",               str(dr.revenue_wins))
    if neither:
        sb.add_row(Text("❌ Neither correct (review needed)", style="bold red"),
                   Text(str(len(neither)), style="bold red"))
    console.print(Panel(sb, title="[bold]Debate Scoreboard[/]", border_style="magenta"))

    if conflicts:
        t = Table(title=f"⚖️  Conflict Resolution — {len(conflicts)} Conflict(s)",
                  box=box.ROUNDED, border_style="magenta", show_lines=True)
        t.add_column("Code",          style="bold yellow", width=10)
        t.add_column("Type",          style="dim",         width=7)
        t.add_column("Conflict",      style="dim",         width=14)
        t.add_column("Clinical Said", style="cyan",        width=30)
        t.add_column("Revenue Said",  style="green",       width=30)
        t.add_column("Winner",        width=14)
        t.add_column("Resolution",    style="white",       width=35)
        t.add_column("Reasoning",     style="dim",         width=45)
        for p in conflicts:
            label, color = WINNER_STYLE.get(p.winning_agent, ("?", "white"))
            t.add_row(
                p.final_code, p.code_type, p.conflict_type,
                p.clinical_position[:80], p.revenue_position[:80],
                Text(label, style=f"bold {color}"),
                p.resolution[:80], p.reasoning[:120],
            )
        console.print(t)
    else:
        console.print(Panel(
            f"✅ Both agents agreed on all {dr.consensus_codes} codes — no conflicts to resolve.",
            border_style="green"))


def _render_comparison(report: FinalCodingReport) -> None:
    comp = report.comparison_result
    if not comp or not comp.has_human_input:
        return
    hi    = report.human_code_input
    s     = comp.summary
    coder = hi.coder_name if hi else "Human Coder"

    stats = Table(box=None, show_header=False, padding=(0, 2))
    stats.add_column("Metric", style="dim",  width=34)
    stats.add_column("Value",  style="bold", width=10)
    for label, val in [
        ("Total AI codes (post-debate)",  s.total_ai_codes),
        ("Total human codes",             s.total_human_codes),
        ("Exact matches",                 s.exact_matches),
        ("AI-only codes",                 s.ai_only_codes),
        ("Human-only codes",              s.human_only_codes),
        ("Unit mismatches",               s.discrepancies),
        ("", ""),
        ("Overall match rate",            f"{s.overall_match_rate*100:.1f}%"),
        ("ICD-10 match rate",             f"{s.icd10_match_rate*100:.1f}%"),
        ("CPT match rate",                f"{s.cpt_match_rate*100:.1f}%"),
        ("HCPCS match rate",              f"{s.hcpcs_match_rate*100:.1f}%"),
        ("", ""),
        ("AI accuracy vs human",          f"{s.ai_accuracy_vs_human*100:.1f}%"),
        ("Human agreement with AI",       f"{s.human_accuracy_vs_ai*100:.1f}%"),
    ]:
        stats.add_row(str(label), str(val))
    console.print(Panel(stats,
        title=f"[bold]AI (Final) vs Human Comparison  (Human: {coder})[/]",
        border_style="magenta"))

    if comp.matched_codes:
        t = Table(title="✅ Agreed Codes", box=box.ROUNDED, border_style="green")
        t.add_column("Code",        style="bold yellow", width=12)
        t.add_column("Type",        style="dim",         width=8)
        t.add_column("Description", style="white",       width=55)
        t.add_column("AI Conf.",    style="green",       width=10)
        for m in comp.matched_codes:
            t.add_row(m.code, m.code_type, m.description, f"{m.ai_confidence*100:.0f}%")
        console.print(t)

    if comp.discrepancies:
        t = Table(title="⚠️  Discrepancies", box=box.ROUNDED, border_style="yellow")
        t.add_column("Type",           width=14)
        t.add_column("Code",           style="yellow", width=12)
        t.add_column("T",              style="dim",    width=7)
        t.add_column("AI Code",        style="cyan",   width=12)
        t.add_column("Human Code",     style="magenta",width=12)
        t.add_column("Sev",            width=8)
        t.add_column("Clinical Impact",style="dim",    width=45)
        for d in comp.discrepancies:
            label, color = DISC_TYPE_LABEL.get(d.discrepancy_type, (d.discrepancy_type, "white"))
            sev_color = _risk_color(d.severity)
            t.add_row(
                Text(label, style=f"bold {color}"),
                d.code, d.code_type,
                d.ai_code    or "—",
                d.human_code or "—",
                Text(d.severity.upper(), style=f"bold {sev_color}"),
                d.clinical_impact,
            )
        console.print(t)


def _scores_panel(sc, include_cpt: bool = True, include_hcpcs: bool = True) -> Panel:
    t = Table(box=None, show_header=False, padding=(0, 1))
    t.add_column("Label", style="dim", width=36)
    t.add_column("Bar",   width=30)

    # ── Confidence scores (high = good = green) ───────────────────────────────
    t.add_row(Text("── Coding Confidence ──────────────", style="bold dim"), Text(""))
    rows = [
        ("Overall Coding Confidence", sc.overall_coding_confidence),
        ("ICD-10 Confidence",         sc.icd10_confidence),
    ]
    if include_cpt:
        rows.append(("CPT Confidence", sc.cpt_confidence))
    if include_hcpcs:
        rows.append(("HCPCS Confidence", sc.hcpcs_confidence))
    for label, val in rows:
        t.add_row(label, _bar(val, reverse=False))

    # ── Risk score (high = bad = red) ─────────────────────────────────────────
    t.add_row(Text("── Compliance Risk ─────────────────", style="bold dim"), Text(""))
    t.add_row("Compliance Risk Score", _bar(sc.compliance_risk_score, reverse=True))
    risk_color = _risk_color(sc.risk_level)
    t.add_row("Risk Level", Text(sc.risk_level.upper(), style=f"bold {risk_color}"))

    # ── Comparison (high match = good = green) ────────────────────────────────
    if sc.comparison_available:
        t.add_row(Text("── AI vs Human Comparison ─────────", style="bold dim"), Text(""))
        t.add_row("AI vs Human Match Rate",   _bar(sc.comparison_confidence, reverse=False))
        t.add_row("AI Accuracy vs Human",     _bar(sc.human_agreement_rate,  reverse=False))

    # ── Debate agreement (high = good = green) ────────────────────────────────
    if sc.clinical_vs_revenue_agreement > 0:
        t.add_row(Text("── Debate Agreement ────────────────", style="bold dim"), Text(""))
        t.add_row("Clinical vs Revenue Agreement",
                  _bar(sc.clinical_vs_revenue_agreement, reverse=False))

    return Panel(t, title="[bold]Confidence & Risk Scores[/]", border_style="green")


def render_report(report: FinalCodingReport) -> None:
    console.print()
    console.rule("[bold cyan]🏥  MEDICAL CODING AI — FINAL COMPLIANCE REPORT[/]")

    console.print(Panel(report.patient_note_excerpt,
                        title="[bold]Clinical Note Excerpt[/]", border_style="blue"))

    # ── Per-agent code sets ───────────────────────────────────────────────────
    console.rule("[bold cyan]🏥 Clinical Accuracy Agent — Independent Coding[/]")
    if report.clinical_agent_codes:
        _render_agent_codes(report.clinical_agent_codes, "cyan")
    else:
        console.print("[yellow]  ⚠  No clinical agent output[/]")

    console.rule("[bold green]💰 Revenue Optimization Agent — Independent Coding[/]")
    if report.revenue_agent_codes:
        _render_agent_codes(report.revenue_agent_codes, "green")
    else:
        console.print("[yellow]  ⚠  No revenue agent output[/]")

    # ── Debate resolution ─────────────────────────────────────────────────────
    console.rule("[bold magenta]⚖️  Debate Agent — Conflict Resolution[/]")
    if report.debate_result:
        _render_debate(report.debate_result)
    else:
        console.print("[yellow]  ⚠  No debate result[/]")

    # ── Final resolved codes ──────────────────────────────────────────────────
    console.rule("[bold white]📋 Final Resolved Codes (Post-Debate)[/]")
    if report.icd10_codes:
        t = Table(title="Final ICD-10-CM Codes", box=box.ROUNDED, border_style="cyan")
        t.add_column("Code",        style="bold yellow", width=12)
        t.add_column("Description", style="white",       width=52)
        t.add_column("Type",        style="dim",         width=12)
        t.add_column("Confidence",  style="green",       width=10)
        for c in report.icd10_codes:
            t.add_row(c.get("code",""), c.get("description",""),
                      c.get("type",""), c.get("confidence",""))
        console.print(t)

    if report.cpt_codes:
        t = Table(title="Final CPT Codes", box=box.ROUNDED, border_style="magenta")
        t.add_column("Code",        style="bold yellow", width=10)
        t.add_column("Description", style="white",       width=55)
        t.add_column("Units",       style="cyan",        width=8)
        t.add_column("Confidence",  style="green",       width=10)
        for c in report.cpt_codes:
            t.add_row(c.get("code",""), c.get("description",""),
                      c.get("units","1"), c.get("confidence",""))
        console.print(t)

    if report.hcpcs_codes:
        t = Table(title="Final HCPCS Codes", box=box.ROUNDED, border_style="blue")
        t.add_column("Code",        style="bold yellow", width=10)
        t.add_column("Description", style="white",       width=50)
        t.add_column("Category",    style="dim",         width=12)
        t.add_column("Units",       style="cyan",        width=8)
        for c in report.hcpcs_codes:
            t.add_row(c.get("code",""), c.get("description",""),
                      c.get("category",""), c.get("units","1"))
        console.print(t)

    # ── Human codes ───────────────────────────────────────────────────────────
    hi = report.human_code_input
    if hi:
        all_human = ([(h.code, h.description, "ICD-10") for h in hi.icd10_codes] +
                     [(h.code, h.description, "CPT")    for h in hi.cpt_codes]   +
                     [(h.code, h.description, "HCPCS")  for h in hi.hcpcs_codes])
        if all_human:
            t = Table(title=f"Human Coder Codes ({hi.coder_name})",
                      box=box.ROUNDED, border_style="magenta")
            t.add_column("Code",        style="bold magenta", width=12)
            t.add_column("Description", style="white",        width=55)
            t.add_column("Type",        style="dim",          width=8)
            for code, desc, ctype in all_human:
                t.add_row(code, desc, ctype)
            console.print(t)

    _render_comparison(report)

    # ── Compliance summary ────────────────────────────────────────────────────
    comp_r = report.compliance_result
    if comp_r:
        color  = "green" if comp_r.is_compliant else "red"
        status = "✅ COMPLIANT" if comp_r.is_compliant else "❌ NON-COMPLIANT"
        issues = []
        if comp_r.ncci_violations: issues.append(f"NCCI violations: {len(comp_r.ncci_violations)}")
        if comp_r.mue_violations:  issues.append(f"MUE violations: {len(comp_r.mue_violations)}")
        if comp_r.lcd_issues:      issues.append(f"LCD issues: {len(comp_r.lcd_issues)}")
        if comp_r.ncd_issues:      issues.append(f"NCD issues: {len(comp_r.ncd_issues)}")
        if comp_r.missed_codes:    issues.append(f"Missed billable codes: {len(comp_r.missed_codes)}")
        body = status + "\n" + ("\n".join(f"  • {i}" for i in issues) if issues else "  No issues detected.")
        console.print(Panel(body, title="[bold]Compliance Validation Summary[/]", border_style=color))

    # ── Audit findings — AI findings + compliance violations combined ─────────
    # Build compliance violation rows first, then append AI audit findings
    compliance_rows = _compliance_audit_rows(comp_r) if comp_r and not comp_r.is_compliant else []
    ai_finding_rows = []
    for f in report.audit_findings:
        sev_color = _risk_color(f.severity)
        ai_finding_rows.append((
            f.finding_type, f.code, f.description,
            f.severity.upper(), sev_color, f.recommendation,
        ))

    if compliance_rows or ai_finding_rows:
        t = Table(title="Audit Findings  (Compliance Violations + AI Audit)",
                  box=box.ROUNDED, border_style="yellow", show_lines=True)
        t.add_column("Type",           style="bold",   width=14)
        t.add_column("Code",           style="yellow", width=14)
        t.add_column("Description",    style="white",  width=42)
        t.add_column("Severity",       width=10)
        t.add_column("Action Required",style="dim",    width=40)

        # Compliance violations first (most actionable)
        if compliance_rows:
            t.add_row(
                Text("── COMPLIANCE VIOLATIONS ──", style="bold red"),
                "", "", "", "",
            )
            for ftype, code, desc, sev, sev_color, rec in compliance_rows:
                t.add_row(
                    Text(ftype, style="bold red"),
                    code, desc,
                    Text(sev, style=f"bold {sev_color}"),
                    rec,
                )

        # AI audit findings second
        if ai_finding_rows:
            t.add_row(
                Text("── AI AUDIT FINDINGS ───────", style="bold yellow"),
                "", "", "", "",
            )
            for ftype, code, desc, sev, sev_color, rec in ai_finding_rows:
                t.add_row(
                    ftype, code, desc,
                    Text(sev, style=f"bold {sev_color}"),
                    rec,
                )

        console.print(t)
    else:
        console.print(Panel("✅ No audit findings or compliance violations.",
                            title="[bold]Audit Findings[/]", border_style="green"))

    # ── Justifications ────────────────────────────────────────────────────────
    if report.justifications:
        lines = []
        for j in report.justifications:
            verdict_label, _ = VERDICT_STYLE.get(j.comparison_verdict, ("➖ No Comparison", "dim"))
            lines.append(f"{'─'*70}")
            lines.append(f"{j.code}  ({j.code_type})   [{verdict_label}]")
            lines.append(f"  Evidence   : {j.clinical_evidence}")
            lines.append(f"  Guideline  : {j.guideline_reference}")
            lines.append(f"  Explanation: {j.explanation}")
            if j.human_code:
                lines.append(f"  Human Code : {j.human_code}")
            if j.comparison_reasoning:
                lines.append(f"  Comparison : {j.comparison_reasoning}")
            lines.append("")
        console.print(Panel("\n".join(lines).strip(),
                            title="[bold]Code Justifications (with AI vs Human Verdict)[/]",
                            border_style="blue"))

    # ── Confidence & risk scores ──────────────────────────────────────────────
    if report.confidence_scores:
        # Determine whether final CPT/HCPCS codes exist — if not, omit those rows.
        include_cpt = bool(report.cpt_codes)
        include_hcpcs = bool(report.hcpcs_codes)
        console.print(_scores_panel(report.confidence_scores, include_cpt=include_cpt, include_hcpcs=include_hcpcs))

    # ── Recommendations ───────────────────────────────────────────────────────
    if report.recommendations:
        recs = "\n".join(f"  → {r}" for r in report.recommendations)
        console.print(Panel(recs, title="[bold]Recommendations[/]", border_style="yellow"))

    # ── Audit summary ─────────────────────────────────────────────────────────
    console.print(Panel(report.audit_summary or "No audit summary available.",
                        title="[bold]Audit Summary[/]", border_style="cyan"))

    console.rule("[bold cyan]END OF REPORT[/]")
    console.print()
