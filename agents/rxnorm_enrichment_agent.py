"""
RxNorm Enrichment Agent (Post-Processing)
──────────────────────────────────────────
Runs AFTER report generation to enrich medications with RxNorm data.
Non-blocking: doesn't slow down initial UI feedback.
Optional: skips gracefully if RxNorm unavailable or disabled.
"""
from __future__ import annotations
import threading
from core.models import PipelineState
from core.rxnorm_client import enrich_medications, is_rxnorm_available
from rich.console import Console

console = Console()


def _enrich_meds_background(state: PipelineState) -> None:
    """
    Background thread: Enrich medications with RxNorm data.
    Does NOT block report generation.
    """
    if not state.clinical_entities or not state.clinical_entities.medications:
        return

    try:
        if not is_rxnorm_available():
            console.print("[dim]  → RxNorm enrichment: unavailable (offline)[/]")
            return

        med_texts = [m.text for m in state.clinical_entities.medications]
        if not med_texts:
            return

        console.print(f"[dim]🚀 Background RxNorm enriching {len(med_texts)} medication(s)...[/]")
        enriched = enrich_medications(tuple(med_texts))
        rxnorm_map = {e["original"]: e for e in enriched}
        found = sum(1 for e in enriched if e["found"])

        # Update medications with RxNorm data in-place
        for med in state.clinical_entities.medications:
            rx = rxnorm_map.get(med.text, {})
            if rx.get("found"):
                med.rxnorm_rxcui = rx.get("rxcui")
                med.rxnorm_name = rx.get("name")
                med.rxnorm_class = rx.get("drug_class")
                med.normalized_name = rx.get("name")

        console.print(f"[green]✅ RxNorm background enrichment complete: {found}/{len(med_texts)} matched[/]")

    except Exception as exc:
        console.print(f"[dim]⚠️  RxNorm background enrichment failed (non-fatal): {exc}[/]")
        state.errors.append(f"RxNorm enrichment (background, non-blocking): {exc}")


def rxnorm_enrichment_agent(state: PipelineState) -> PipelineState:
    """
    LangGraph node: Start background RxNorm enrichment (non-blocking).
    This runs AFTER report generation, so UI is not blocked.
    """
    # Start background thread
    thread = threading.Thread(target=_enrich_meds_background, args=(state,), daemon=True)
    thread.start()
    # Return immediately — don't wait for RxNorm

    return state
