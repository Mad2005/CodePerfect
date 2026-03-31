"""
LangGraph Pipeline  (with live per-agent output display)
──────────────────────────────────────────────────────────
Each node prints its output to the console immediately after running,
so the user sees progress in real time rather than waiting for the full report.
"""
from __future__ import annotations
from typing import Any
import sqlite3
import uuid
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from core.models import PipelineState
from core.vector_db import VectorKnowledgeBase

from agents.text_processing_agent      import text_processing_agent
from agents.nlp_extraction_agent       import nlp_extraction_agent
from agents.terminology_mapping_agent  import terminology_mapping_agent
from agents.knowledge_retrieval_agent  import knowledge_retrieval_agent
from agents.coding_agents              import clinical_accuracy_agent, revenue_optimization_agent
from agents.debate_agent               import debate_agent
from agents.comparison_engine          import comparison_engine
from agents.rule_validation_engine     import rule_validation_engine
from agents.auditor_agent              import auditor_agent
from agents.justification_agent        import justification_agent
from agents.confidence_scoring_engine  import confidence_scoring_engine
from agents.report_generation_agent    import report_generation_agent
from agents.rxnorm_enrichment_agent    import rxnorm_enrichment_agent

console = Console()

# ── Checkpoint Database Setup ────────────────────────────────────────────────
CHECKPOINT_DB_PATH = Path(__file__).parent.parent / "data" / "checkpoints.db"

def _get_checkpointer():
    """Initialize SQLite checkpointer for thread-based state persistence."""
    try:
        # check_same_thread=False allows SQLite connection to be used across LangGraph's thread pool
        # This is safe because SQLite serializes access internally
        conn = sqlite3.connect(str(CHECKPOINT_DB_PATH), check_same_thread=False)
        return SqliteSaver(conn=conn)
    except Exception as e:
        console.print(f"[yellow]⚠️  Checkpoint DB fail: {e} — running without checkpoints[/]")
        return None


# ── Per-agent live display functions ─────────────────────────────────────────

def _show_text_processing(s: PipelineState) -> None:
    console.print(Panel(
        f"[green]✓ Cleaned {len(s.cleaned_text)} chars[/]\n"
        f"[dim]{s.cleaned_text[:300]}{'...' if len(s.cleaned_text) > 300 else ''}[/]",
        title="[bold cyan]📝 Text Processing Agent[/]", border_style="cyan"))


def _show_nlp_extraction(s: PipelineState) -> None:
    e = s.clinical_entities
    if not e:
        console.print("[yellow]NLP Extraction: no entities found[/]")
        return
    t = Table(box=box.SIMPLE_HEAD, border_style="cyan", show_lines=False)
    t.add_column("Type",       style="bold yellow", width=12)
    t.add_column("Entity",     style="white",       width=42)
    t.add_column("Conf",       style="green",       width=7)
    t.add_column("Source",     style="dim",         width=12)

    conf_color = lambda c: "green" if c >= 0.9 else "yellow" if c >= 0.7 else "red"
    for d in e.diagnoses:
        c = d.confidence
        t.add_row("Diagnosis",  d.text[:40],
                  f"[{conf_color(c)}]{c*100:.0f}%[/]", "—")
    for p in e.procedures:
        c = p.confidence
        t.add_row("Procedure",  p.text[:40],
                  f"[{conf_color(c)}]{c*100:.0f}%[/]", "—")
    for m in e.medications:
        t.add_row("Medication", m.text[:40], "[green]90%[/]", "—")
    for o in e.other_entities[:3]:
        t.add_row("Other",      str(o)[:40], "—", "—")
    console.print(Panel(t, title="[bold cyan]🔬 NLP Extraction — LLM + BioBERT Merged[/]",
                        border_style="cyan"))


def _show_terminology_mapping(s: PipelineState) -> None:
    e = s.mapped_entities or s.clinical_entities
    if not e:
        return
    mapped = [(d.text, d.snomed_code) for d in e.diagnoses if d.snomed_code]
    if mapped:
        t = Table(box=box.SIMPLE_HEAD, border_style="blue")
        t.add_column("Entity",     style="white",       width=40)
        t.add_column("SNOMED CT",  style="bold yellow", width=15)
        for text, code in mapped:
            t.add_row(text, code)
        console.print(Panel(t, title="[bold blue]🗺️  SNOMED CT Mapping[/]", border_style="blue"))
    else:
        console.print("[dim]🗺️  SNOMED mapping: no matches in knowledge base[/]")

    # Show RxNorm medication matches (if any)
    meds = getattr(e, "medications", [])
    mapped_meds = [(m.text, m.rxnorm_rxcui or "", m.rxnorm_name or "", m.rxnorm_class or "")
                   for m in meds if (m.rxnorm_rxcui or m.normalized_name)]
    if mapped_meds:
        t2 = Table(box=box.SIMPLE_HEAD, border_style="green")
        t2.add_column("Medication", style="white", width=40)
        t2.add_column("RxCUI",      style="bold yellow", width=12)
        t2.add_column("Name",       style="dim",         width=30)
        t2.add_column("Class",      style="dim",         width=18)
        for text, rxcui, name, cls in mapped_meds:
            t2.add_row(text, rxcui, name, cls)
        console.print(Panel(t2, title="[bold green]💊 RxNorm Mapping[/]", border_style="green"))
    else:
        console.print("[dim]💊 RxNorm mapping: no matches or RxNorm unavailable[/]")


def _show_knowledge_retrieval(s: PipelineState) -> None:
    console.print(Panel(
        f"[green]Clinical guidelines retrieved : {len(s.clinical_guidelines)}[/]\n"
        f"[green]Revenue guidelines retrieved  : {len(s.revenue_guidelines)}[/]\n"
        f"[green]Compliance rules retrieved    : {len(s.retrieved_rules)}[/]",
        title="[bold blue]📚 Knowledge Retrieval (RAG)[/]", border_style="blue"))


def _show_agent_codes(agent_output, title: str, border: str) -> None:
    if not agent_output:
        return
    lines = []
    if agent_output.icd10_codes:
        lines.append(f"[bold]ICD-10:[/] " +
                     ", ".join(f"{c.code}({c.confidence*100:.0f}%)" for c in agent_output.icd10_codes))
    if agent_output.cpt_codes:
        lines.append(f"[bold]CPT   :[/] " +
                     ", ".join(f"{c.code}({c.confidence*100:.0f}%)" for c in agent_output.cpt_codes))
    if agent_output.hcpcs_codes:
        lines.append(f"[bold]HCPCS :[/] " +
                     ", ".join(f"{c.code}" for c in agent_output.hcpcs_codes))
    if agent_output.missed_services:
        lines.append(f"[yellow]Missed: {'; '.join(agent_output.missed_services[:2])}[/]")
    if agent_output.agent_notes:
        lines.append(f"[dim]Notes : {agent_output.agent_notes[:120]}[/]")
    console.print(Panel("\n".join(lines) or "[dim]No codes[/]",
                        title=f"[bold]{title}[/]", border_style=border))


def _show_debate(s: PipelineState) -> None:
    dr = s.debate_result
    if not dr:
        return
    conflicts = dr.debate_points
    body = (
        f"🤝 Agreed: [bold]{dr.consensus_codes}[/]  "
        f"⚖️  Conflicts: [bold]{len(conflicts)}[/]  "
        f"🏥 Clinical won: [bold]{dr.clinical_wins}[/]  "
        f"💰 Revenue won: [bold]{dr.revenue_wins}[/]"
    )
    if conflicts:
        body += "\n\n[bold]Resolved conflicts:[/]"
        for p in conflicts[:5]:
            body += f"\n  [{p.winning_agent}] {p.final_code} — {p.resolution[:80]}"
        if len(conflicts) > 5:
            body += f"\n  ... and {len(conflicts)-5} more"
    console.print(Panel(body, title="[bold magenta]⚖️  Debate Agent[/]", border_style="magenta"))


def _show_compliance(s: PipelineState) -> None:
    cr = s.compliance_result
    if not cr:
        return
    color  = "green" if cr.is_compliant else "red"
    status = "✅ COMPLIANT" if cr.is_compliant else "❌ NON-COMPLIANT"
    issues = []
    if cr.ncci_violations: issues.append(f"NCCI: {len(cr.ncci_violations)}")
    if cr.mue_violations:  issues.append(f"MUE: {len(cr.mue_violations)}")
    if cr.lcd_issues:      issues.append(f"LCD: {len(cr.lcd_issues)}")
    if cr.ncd_issues:      issues.append(f"NCD: {len(cr.ncd_issues)}")
    if cr.missed_codes:    issues.append(f"Missed: {len(cr.missed_codes)}")
    body = f"[{color}]{status}[/]"
    if issues:
        body += "  |  " + "  ".join(issues)
    console.print(Panel(body, title="[bold yellow]⚖️  Rule Validation[/]", border_style=color))


def _show_audit(s: PipelineState) -> None:
    if not s.audit_findings:
        console.print("[dim]🔍 Auditor: No findings[/]")
        return
    t = Table(box=box.SIMPLE_HEAD, border_style="yellow")
    t.add_column("Type",     style="bold",   width=14)
    t.add_column("Code",     style="yellow", width=10)
    t.add_column("Severity", width=8)
    t.add_column("Summary",  style="dim",    width=60)
    sev_color = {"high": "red", "medium": "yellow", "low": "green"}
    for f in s.audit_findings:
        c = sev_color.get(f.severity.lower(), "white")
        t.add_row(f.finding_type, f.code,
                  f"[{c}]{f.severity.upper()}[/{c}]",
                  f.description[:80])
    console.print(Panel(t, title="[bold yellow]🔍 Auditor Agent[/]", border_style="yellow"))


def _show_scores(s: PipelineState) -> None:
    sc = s.confidence_scores
    if not sc:
        return
    risk_c = {"low": "green", "medium": "yellow", "high": "red"}.get(sc.risk_level, "white")
    body = (
        f"Overall Confidence : [bold]{sc.overall_coding_confidence*100:.1f}%[/]  "
        f"ICD-10: {sc.icd10_confidence*100:.1f}%  "
        f"CPT: {sc.cpt_confidence*100:.1f}%  "
        f"HCPCS: {sc.hcpcs_confidence*100:.1f}%\n"
        f"Compliance Risk    : [{risk_c}]{sc.compliance_risk_score*100:.1f}%  "
        f"Risk Level: {sc.risk_level.upper()}[/{risk_c}]"
    )
    if sc.comparison_available:
        body += (f"\nAI vs Human Match  : {sc.comparison_confidence*100:.1f}%  "
                 f"AI Accuracy: {sc.human_agreement_rate*100:.1f}%")
    console.print(Panel(body, title="[bold green]📊 Confidence & Risk Scores[/]", border_style="green"))


# ── Wrapped node factory ──────────────────────────────────────────────────────

def _wrap(agent_fn, display_fn=None, vdb=None):
    """Wrap an agent function with pre/post display and timing."""
    import time
    def node(s: dict) -> dict:
        state = PipelineState(**s)
        t0    = time.time()
        state = agent_fn(state, vdb) if vdb else agent_fn(state)
        elapsed = time.time() - t0
        console.print(f"  [dim]({elapsed:.1f}s)[/]")
        if display_fn:
            display_fn(state)
        return state.model_dump()
    return node


def build_pipeline(vdb: VectorKnowledgeBase):
    graph = StateGraph(dict)
    checkpointer = _get_checkpointer()

    graph.add_node("text_processing",
        _wrap(text_processing_agent, _show_text_processing))
    graph.add_node("nlp_extraction",
        _wrap(nlp_extraction_agent, _show_nlp_extraction))
    graph.add_node("terminology_mapping",
        _wrap(lambda s, v: terminology_mapping_agent(s, v), _show_terminology_mapping, vdb))
    graph.add_node("knowledge_retrieval",
        _wrap(lambda s, v: knowledge_retrieval_agent(s, v), _show_knowledge_retrieval, vdb))

    graph.add_node("clinical_accuracy",
        _wrap(clinical_accuracy_agent,
              lambda s: _show_agent_codes(s.clinical_agent_output,
                                          "🏥 Clinical Accuracy Agent", "cyan")))
    graph.add_node("revenue_optimization",
        _wrap(revenue_optimization_agent,
              lambda s: _show_agent_codes(s.revenue_agent_output,
                                          "💰 Revenue Optimization Agent", "green")))
    graph.add_node("debate_agent",
        _wrap(debate_agent, _show_debate))
    graph.add_node("comparison_engine",
        _wrap(comparison_engine, lambda s: (
            console.print(f"[dim]🔀 Comparison: "
                          f"{s.comparison_result.summary.exact_matches if s.comparison_result else 0} matches, "
                          f"{len(s.comparison_result.discrepancies) if s.comparison_result else 0} discrepancies[/]")
            if s.comparison_result else None
        )))
    graph.add_node("rule_validation",
        _wrap(rule_validation_engine, _show_compliance))
    graph.add_node("auditor",
        _wrap(auditor_agent, _show_audit))
    graph.add_node("justification",
        _wrap(justification_agent, lambda s: console.print(
            f"[dim]📜 Justification: {len(s.justifications)} code justifications generated[/]")))
    graph.add_node("confidence_scoring",
        _wrap(confidence_scoring_engine, _show_scores))
    graph.add_node("report_generation",
        _wrap(report_generation_agent, lambda s: console.print(
            "[dim]📋 Report generation complete[/]")))
    graph.add_node("rxnorm_enrichment",
        _wrap(rxnorm_enrichment_agent, lambda s: console.print(
            "[dim]🚀 Background RxNorm enrichment started[/]")))

    graph.set_entry_point("text_processing")
    graph.add_edge("text_processing",      "nlp_extraction")
    graph.add_edge("nlp_extraction",       "terminology_mapping")
    graph.add_edge("terminology_mapping",  "knowledge_retrieval")
    graph.add_edge("knowledge_retrieval",  "clinical_accuracy")
    graph.add_edge("clinical_accuracy",    "revenue_optimization")
    graph.add_edge("revenue_optimization", "debate_agent")
    graph.add_edge("debate_agent",         "comparison_engine")
    graph.add_edge("comparison_engine",    "rule_validation")
    graph.add_edge("rule_validation",      "auditor")
    graph.add_edge("auditor",              "justification")
    graph.add_edge("justification",        "confidence_scoring")
    graph.add_edge("confidence_scoring",   "report_generation")
    graph.add_edge("report_generation",    "rxnorm_enrichment")
    graph.add_edge("rxnorm_enrichment",    END)

    return graph.compile(checkpointer=checkpointer) if checkpointer else graph.compile()


def run_pipeline(clinical_note: str, vdb: VectorKnowledgeBase, human_codes=None, thread_id: str = None) -> PipelineState:
    """
    Run the medical coding pipeline with optional checkpoint persistence.
    
    Args:
        clinical_note: Clinical text to process
        vdb: Vector knowledge base
        human_codes: Optional human-assigned codes for validation mode
        thread_id: Optional thread ID for checkpoint tracking (auto-generated if not provided)
    
    Returns:
        Final pipeline state with all agent outputs
    """
    pipeline = build_pipeline(vdb)
    if not thread_id:
        thread_id = str(uuid.uuid4())
    
    initial = PipelineState(
        raw_clinical_text=clinical_note,
        human_code_input=human_codes,
    ).model_dump()
    
    config = {"configurable": {"thread_id": thread_id}}
    return PipelineState(**pipeline.invoke(initial, config))