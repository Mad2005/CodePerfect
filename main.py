"""
Medical Coding AI System — Main Entry Point
═════════════════════════════════════════════
Usage:
    python main.py                         # Run with built-in sample human codes
    python main.py --note 1                # Diabetes note  (includes sample human codes)
    python main.py --note 2                # Appendectomy   (includes sample human codes)
    python main.py --note 3                # Cardiac        (includes sample human codes)
    python main.py --no-human              # Run WITHOUT human codes (AI-only mode)
    python main.py --all                   # All 3 notes
    python main.py --custom "note text"    # Custom note (no human codes)
"""
import sys
import argparse
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel

console = Console()

import os
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL",   "meta-llama/llama-4-scout-17b-16e-instruct")

if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
    console.print(Panel(
        "[bold red]❌  GROQ_API_KEY is missing or not set.[/]\n\n"
        "  1. Create a [bold].env[/] file in the project folder\n"
        "  2. Add your key:   [bold yellow]GROQ_API_KEY=gsk_...[/]\n"
        "  3. Optionally set: [bold yellow]GROQ_MODEL=meta-llama/llama-4-scout-17b-16e-instruct[/]\n"
        "  4. Get a free key: [bold cyan]https://console.groq.com/keys[/]",
        title="[bold red]API Key Error[/]", border_style="red",
    ))
    sys.exit(1)

from core.vector_db import VectorKnowledgeBase
from core.pipeline import run_pipeline
from core.models import HumanCodeInput, HumanCode
from utils.report_renderer import render_report
from utils.html_report import save_report
from data.sample_notes import (
    SAMPLE_NOTE_1_DIABETES_HYPERTENSION,
    SAMPLE_NOTE_2_APPENDECTOMY,
    SAMPLE_NOTE_3_CARDIAC,
    SAMPLE_NOTE_4_SIMPLE_PNEUMONIA,
)

# ─── Sample human codes (intentionally include some errors for demo) ──────────

HUMAN_CODES_NOTE1 = HumanCodeInput(
    coder_name="Jane Smith, CPC",
    icd10_codes=[
        HumanCode(code="E11.65",  description="Type 2 DM with hyperglycemia",   code_type="ICD-10"),
        HumanCode(code="N18.3",   description="Chronic kidney disease stage 3",  code_type="ICD-10"),
        HumanCode(code="I10",     description="Essential hypertension",          code_type="ICD-10"),
        HumanCode(code="E78.5",   description="Hyperlipidemia",                  code_type="ICD-10"),
        # Human missed: G47.33 (sleep apnea), E66.9 (obesity), Z79.4 (insulin use)
    ],
    cpt_codes=[
        HumanCode(code="99232",   description="Subsequent hospital care",        code_type="CPT", units=1),
        HumanCode(code="93000",   description="ECG routine",                     code_type="CPT", units=1),
        HumanCode(code="71046",   description="Chest X-ray 2 views",             code_type="CPT", units=1),
        HumanCode(code="85027",   description="CBC automated",                   code_type="CPT", units=1),
        HumanCode(code="36415",   description="Venipuncture",                    code_type="CPT", units=1),
        # Human included 36415 (NCCI bundling error) — AI should catch this
        # Human missed: 76770 (renal ultrasound), 83036 (HbA1c), 80053 (CMP)
    ],
    hcpcs_codes=[
        HumanCode(code="J1817",   description="Insulin 50 units",                code_type="HCPCS"),
        # Human missed: E0601 (CPAP), A4253 (test strips)
    ],
    notes="Initial coding pass — uncertain about sleep apnea and renal ultrasound codes.",
)

HUMAN_CODES_NOTE2 = HumanCodeInput(
    coder_name="Mark Johnson, CPC-H",
    icd10_codes=[
        HumanCode(code="K35.80",  description="Acute appendicitis without abscess", code_type="ICD-10"),
        HumanCode(code="R11.2",   description="Nausea and vomiting",                code_type="ICD-10"),
    ],
    cpt_codes=[
        HumanCode(code="44950",   description="Appendectomy",                       code_type="CPT", units=1),
        # Human used 44950 (open) — AI may assign 44970 (laparoscopic)
        HumanCode(code="99232",   description="Subsequent hospital care",            code_type="CPT", units=1),
        HumanCode(code="85027",   description="CBC",                                 code_type="CPT", units=1),
    ],
    hcpcs_codes=[],
    notes="Coded appendectomy as open — need to verify laparoscopic approach.",
)

HUMAN_CODES_NOTE3 = HumanCodeInput(
    coder_name="Dr. Roberts (Physician Coder)",
    icd10_codes=[
        HumanCode(code="I21.19",  description="STEMI inferior wall",               code_type="ICD-10"),
        HumanCode(code="I25.10",  description="Atherosclerotic heart disease",     code_type="ICD-10"),
        HumanCode(code="I10",     description="Hypertension",                      code_type="ICD-10"),
        HumanCode(code="E11.9",   description="Type 2 diabetes",                   code_type="ICD-10"),
        HumanCode(code="F17.210", description="Nicotine dependence, cigarettes",   code_type="ICD-10"),
    ],
    cpt_codes=[
        HumanCode(code="93510",   description="Left heart catheterisation",        code_type="CPT", units=1),
        HumanCode(code="93458",   description="Coronary angiography",              code_type="CPT", units=1),
        HumanCode(code="92928",   description="PCI with stent",                    code_type="CPT", units=1),
        HumanCode(code="93000",   description="ECG",                               code_type="CPT", units=1),
    ],
    hcpcs_codes=[],
    notes="Cardiac cath and PCI coded. CABG not yet scheduled so not coded.",
)

HUMAN_CODES_NOTE4 = HumanCodeInput(
    coder_name="Lisa Chen, CPC (trainee)",
    icd10_codes=[
        HumanCode(code="J18.9", description="Pneumonia unspecified", code_type="ICD-10"),
        # Human missed: no secondary codes — this is intentional for the demo
    ],
    cpt_codes=[
        HumanCode(code="99221", description="Initial hospital care low complexity",
                  code_type="CPT", units=1),
        HumanCode(code="71046", description="Chest X-ray 2 views", code_type="CPT", units=1),
        # Human missed: CBC (85027), BMP (80048)
        # Human missed: HCPCS J0690 for ceftriaxone
    ],
    hcpcs_codes=[
        # Human left HCPCS blank — AI should catch J0690 ceftriaxone
    ],
    notes="First pass — unsure about E&M level and drug codes.",
)

SAMPLE_NOTES = {
    "1": ("Diabetes + Hypertension + CKD Discharge",        SAMPLE_NOTE_1_DIABETES_HYPERTENSION, HUMAN_CODES_NOTE1),
    "2": ("Acute Appendicitis – Laparoscopic Appendectomy", SAMPLE_NOTE_2_APPENDECTOMY,          HUMAN_CODES_NOTE2),
    "3": ("STEMI + Three-Vessel CAD Cardiology Consult",    SAMPLE_NOTE_3_CARDIAC,               HUMAN_CODES_NOTE3),
    "4": ("Simple Pneumonia Discharge  ← Learning Example",  SAMPLE_NOTE_4_SIMPLE_PNEUMONIA,      HUMAN_CODES_NOTE4),
}


def print_pipeline_stages(has_human: bool) -> None:
    stages = [
        "📝  Text Processing Agent         → Clean & normalise clinical note",
        "🔬  NLP Extraction Agent          → Extract diagnoses, procedures, medications",
        "🗺️   SNOMED Terminology Mapping    → Map entities to SNOMED CT",
        "📚  Knowledge Retrieval (RAG)     → Split knowledge: clinical vs revenue",
        "🏥  Clinical Accuracy Agent       → Full ICD+CPT+HCPCS (clinical perspective)",
        "💰  Revenue Optimization Agent    → Full ICD+CPT+HCPCS (revenue perspective)",
        "⚖️   Debate Agent                  → Resolve conflicts between the two agents",
    ]
    if has_human:
        stages.append("🔀  Comparison Engine             → Diff final AI codes vs Human codes")
    stages += [
        "🛡️   Rule Validation Engine        → NCCI + MUE + LCD + NCD checks",
        "🔍  Auditor Agent                 → Detect upcoding / downcoding",
        "📜  Justification Agent           → Justify codes + comparison verdicts",
        "📊  Confidence Scoring Engine     → Confidence incl. debate + human match",
        "📋  Report Generation Agent       → Compile final coding report",
    ]
    console.print(Panel("\n".join(stages), title="[bold cyan]Pipeline Stages[/]", border_style="cyan"))


def run(note_text: str, note_title: str, human_codes=None) -> None:
    has_human = human_codes is not None
    console.print(f"\n[bold cyan]Processing:[/] {note_title}")
    if has_human:
        console.print(f"[magenta]Human Coder:[/] {human_codes.coder_name}\n")
    else:
        console.print("[dim]Running in AI-only mode (no human codes provided)[/]\n")

    print_pipeline_stages(has_human)
    console.print()

    with Progress(SpinnerColumn(), TextColumn("[bold blue]{task.description}"),
                  TimeElapsedColumn(), console=console) as p:
        t = p.add_task("Initialising ChromaDB knowledge base...", total=None)
        vdb = VectorKnowledgeBase()
        p.update(t, description="✅ Knowledge base ready")
        time.sleep(0.2)
    console.print("[green]✅ Vector knowledge base initialised[/]\n")

    start = time.time()
    with Progress(SpinnerColumn(), TextColumn("[bold blue]{task.description}"),
                  TimeElapsedColumn(), console=console) as p:
        t = p.add_task("Running LangGraph pipeline...", total=None)
        try:
            state = run_pipeline(note_text, vdb, human_codes)
            p.update(t, description="✅ Pipeline complete")
        except Exception as exc:
            p.update(t, description=f"❌ Pipeline failed: {exc}")
            console.print_exception()
            return

    console.print(f"\n[green]✅ Pipeline completed in {time.time()-start:.1f}s[/]\n")

    if state.errors:
        console.print("[yellow]⚠️  Pipeline warnings:[/]")
        for err in state.errors:
            console.print(f"  [yellow]• {err}[/]")
        console.print()

    if state.final_report:
        render_report(state.final_report)
        # ── Save HTML report ──────────────────────────────────────────────────
        import re as _re
        safe = _re.sub(r'[^\w]+', '_', note_title.lower())[:40]
        html_path = save_report(state.final_report, "reports", f"{safe}.html")
        console.print(f"\n[bold green]📄 HTML report saved:[/] [cyan]{html_path.resolve()}[/]")
        console.print(f"[dim]   Open in browser: file://{html_path.resolve()}[/]")
        console.print(f"[dim]   Or run:  python server.py  then visit http://localhost:5000/latest[/]\n")
    else:
        console.print("[red]❌ No final report generated. Check warnings above.[/]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Medical Coding AI System")
    parser.add_argument("--note",     choices=["1","2","3","4"], help="Sample note 1–4  (4 = simple pneumonia learning example)")
    parser.add_argument("--custom",   type=str,              help="Custom clinical note text")
    parser.add_argument("--all",      action="store_true",   help="Run all 4 sample notes")
    parser.add_argument("--no-human", action="store_true",   help="Disable human code comparison")
    args = parser.parse_args()

    console.print(Panel(
        "[bold cyan]Medical Coding AI System[/]\n"
        "LLM: Llama 4 Scout via Groq  |  Framework: LangGraph  |  Vector DB: ChromaDB\n"
        "Compliance: NCCI + MUE + LCD + NCD  |  Codes: ICD-10 + CPT + HCPCS + SNOMED CT\n"
        "Feature: AI vs Human Code Comparison  ← NEW",
        border_style="cyan",
    ))

    if args.custom:
        run(args.custom, "Custom Clinical Note", None)
    elif args.note:
        title, text, human = SAMPLE_NOTES[args.note]
        run(text, title, None if args.no_human else human)
    elif args.all:
        for num, (title, text, human) in SAMPLE_NOTES.items():
            run(text, f"[{num}/3] {title}", None if args.no_human else human)
            console.print("\n" + "═"*80 + "\n")
    else:
        title, text, human = SAMPLE_NOTES["1"]
        run(text, f"[Default] {title}", None if args.no_human else human)


if __name__ == "__main__":
    main()
