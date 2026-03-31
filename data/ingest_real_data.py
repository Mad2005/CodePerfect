"""
Real Medical Coding Data Ingestion Script
──────────────────────────────────────────
Supported file formats:
  CSV  (.csv)  — comma, tab, or pipe delimited
  TXT  (.txt)  — tab or pipe delimited (CMS standard)
  XLSX (.xlsx) — Excel workbook (first sheet used)
  XLS  (.xls)  — Legacy Excel

Your files → expected names:
  icd10.txt       → ICD-10-CM codes
  cpt.xlsx        → CPT procedure codes
  hcpcs.xlsx      → HCPCS Level II codes
  lcd_rules.csv   → Local Coverage Determinations
  ncd_rules.csv   → National Coverage Determinations
  ncci_ptp.txt    → NCCI Procedure-to-Procedure edits
  ncci_mue.txt    → MUE limits

Usage:
  python data/ingest_real_data.py              # ingest all files in data/real/
  python data/ingest_real_data.py --status     # show DB record counts
  python data/ingest_real_data.py --clear      # wipe DB then ingest
  python data/ingest_real_data.py --collection icd10
"""
from __future__ import annotations
import sys, csv, argparse, time, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from chromadb.config import Settings
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, MofNCompleteColumn
from rich import box

from config.settings import (
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_ICD10, CHROMA_COLLECTION_CPT,
    CHROMA_COLLECTION_HCPCS, CHROMA_COLLECTION_NCCI,
    CHROMA_COLLECTION_MUE,   CHROMA_COLLECTION_LCD,
    CHROMA_COLLECTION_NCD,   CHROMA_COLLECTION_GUIDELINES,
)

console   = Console()
DATA_DIR  = Path(__file__).parent / "real"
BATCH     = 500


# ── File readers ──────────────────────────────────────────────────────────────

def _read_excel(filepath: Path) -> tuple[list[str], list[list[str]]]:
    """Read first sheet of an XLSX/XLS file."""
    try:
        import openpyxl
        wb   = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
        ws   = wb.active
        rows = [[str(cell.value or "").strip() for cell in row] for row in ws.iter_rows()]
        wb.close()
    except ImportError:
        try:
            import xlrd
            wb   = xlrd.open_workbook(filepath)
            ws   = wb.sheet_by_index(0)
            rows = [[str(ws.cell_value(r, c)).strip() for c in range(ws.ncols)]
                    for r in range(ws.nrows)]
        except ImportError:
            raise ImportError(
                "Install openpyxl to read XLSX files:  pip install openpyxl\n"
                "Or xlrd for XLS files:                pip install xlrd"
            )

    if not rows:
        return [], []
    headers = [h.lower().strip() for h in rows[0]]
    return headers, [r for r in rows[1:] if any(c for c in r)]


def _detect_delim(filepath: Path) -> str:
    first = filepath.read_text(encoding="utf-8", errors="replace").split("\n")[0]
    for d in ["\t", "|", ",", ";"]:
        if first.count(d) >= 1:
            return d
    return ","


def _read_csv_txt(filepath: Path) -> tuple[list[str], list[list[str]]]:
    delim = _detect_delim(filepath)
    rows, headers = [], []
    with open(filepath, encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f, delimiter=delim)
        for i, row in enumerate(reader):
            row = [c.strip() for c in row]
            if i == 0:
                headers = [h.lower().strip() for h in row]
            elif any(row):
                rows.append(row)
    return headers, rows


def read_file(filepath: Path) -> tuple[list[str], list[list[str]]]:
    """Universal reader — dispatches by extension."""
    ext = filepath.suffix.lower()
    if ext in (".xlsx", ".xls"):
        return _read_excel(filepath)
    else:
        return _read_csv_txt(filepath)


def col(row: list[str], headers: list[str], *names: str, default: str = "") -> str:
    for name in names:
        for i, h in enumerate(headers):
            if name in h and i < len(row):
                v = row[i].strip()
                if v and v.lower() not in ("none", "null", "nan", ""):
                    return v
    return default


# ── ChromaDB helpers ──────────────────────────────────────────────────────────

def get_client():
    return chromadb.PersistentClient(
        path=CHROMA_PERSIST_DIR,
        settings=Settings(anonymized_telemetry=False),
    )

def get_coll(client, name):
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})

def _upsert(coll, ids, texts, metas, label: str) -> int:
    if not ids:
        return 0
    with Progress(TextColumn(f"  [cyan]{label}[/]"), BarColumn(bar_width=28),
                  MofNCompleteColumn(), TimeElapsedColumn(), console=console) as p:
        task = p.add_task("", total=len(ids))
        for s in range(0, len(ids), BATCH):
            e = min(s + BATCH, len(ids))
            coll.upsert(ids=ids[s:e], documents=texts[s:e], metadatas=metas[s:e])
            p.advance(task, e - s)
    return len(ids)


# ── Per-collection ingestion ──────────────────────────────────────────────────

def ingest_icd10(client, filepath: Path) -> int:
    headers, rows = read_file(filepath)
    coll = get_coll(client, CHROMA_COLLECTION_ICD10)
    ids, texts, metas = [], [], []
    for i, row in enumerate(rows):
        code = col(row, headers, "code", "icd", "icd10", "diagnosis_code", "dx_code",
                   "order_num", "icd_10_cm_code", "icd10cm")
        desc = col(row, headers, "description", "desc", "long_description",
                   "short_description", "long_desc", "full_description", "diagnosis_desc")
        if not code or not desc or len(code) < 2:
            continue
        ids.append(f"icd_{code.replace('.','_')}_{i}")
        texts.append(f"{code} {desc}")
        metas.append({"code": code, "description": desc[:400], "category": "diagnosis"})
    return _upsert(coll, ids, texts, metas, "ICD-10")


def ingest_cpt(client, filepath: Path) -> int:
    headers, rows = read_file(filepath)
    coll = get_coll(client, CHROMA_COLLECTION_CPT)
    ids, texts, metas = [], [], []
    for i, row in enumerate(rows):
        code = col(row, headers, "code", "cpt", "cpt_code", "procedure_code",
                   "proc_code", "cptcode")
        desc = col(row, headers, "description", "desc", "long_description",
                   "medium_description", "short_description", "procedure_description")
        cat  = col(row, headers, "category", "section", "type", default="procedure")
        if not code or not desc or len(code) < 3:
            continue
        ids.append(f"cpt_{code}_{i}")
        texts.append(f"{code} {desc}")
        metas.append({"code": code, "description": desc[:400], "category": cat})
    return _upsert(coll, ids, texts, metas, "CPT")


def ingest_hcpcs(client, filepath: Path) -> int:
    headers, rows = read_file(filepath)
    coll = get_coll(client, CHROMA_COLLECTION_HCPCS)
    ids, texts, metas = [], [], []
    for i, row in enumerate(rows):
        code = col(row, headers, "code", "hcpcs", "hcpcs_code", "level_ii_code")
        desc = col(row, headers, "description", "desc", "long_description",
                   "short_description", "item_description")
        cat  = col(row, headers, "category", "type", "class", default="supply")
        if not code or not desc:
            continue
        ids.append(f"hcpcs_{code}_{i}")
        texts.append(f"{code} {desc}")
        metas.append({"code": code, "description": desc[:400], "category": cat})
    return _upsert(coll, ids, texts, metas, "HCPCS")


def ingest_ncci_ptp(client, filepath: Path) -> int:
    """
    CMS NCCI PTP standard format:
    Column1 Code | Column2 Code | Modifier Indicator | Effective Date | Deletion Date
    """
    headers, rows = read_file(filepath)
    coll = get_coll(client, CHROMA_COLLECTION_NCCI)
    ids, texts, metas = [], [], []
    for i, row in enumerate(rows):
        c1  = col(row, headers, "column1", "col1", "column_1", "code1",
                  "comprehensive_code", "comp_code")
        c2  = col(row, headers, "column2", "col2", "column_2", "code2",
                  "component_code", "comp_code2")
        mod = col(row, headers, "modifier", "modifier_indicator", "mod", default="0")
        # For fixed-width or positional TXT (no header): take first two non-empty cols
        if not c1 and len(row) >= 2:
            c1, c2 = row[0].strip(), row[1].strip()
            mod    = row[2].strip() if len(row) > 2 else "0"
        if not c1 or not c2 or len(c1) < 3:
            continue
        mod_ok = mod.strip() in ("1", "9")
        text = (f"NCCI PTP Edit: CPT {c1} and CPT {c2} cannot be billed together. "
                f"Modifier allowed: {'Yes' if mod_ok else 'No'}.")
        ids.append(f"ncci_ptp_{c1}_{c2}_{i}")
        texts.append(text)
        metas.append({"col1": c1, "col2": c2,
                      "modifier_allowed": str(mod_ok).lower(), "type": "ptp"})
    return _upsert(coll, ids, texts, metas, "NCCI-PTP")


def ingest_mue(client, filepath: Path) -> int:
    """
    CMS MUE format:
    HCPCS/CPT Code | MUE Value | MUE Adjudication Indicator | Rationale
    """
    headers, rows = read_file(filepath)
    coll = get_coll(client, CHROMA_COLLECTION_MUE)
    ids, texts, metas = [], [], []
    for i, row in enumerate(rows):
        code  = col(row, headers, "code", "hcpcs", "cpt", "procedure_code",
                    "hcpcs_cpt_code")
        units = col(row, headers, "mue_value", "mue", "max_units", "units",
                    "mue_values", default="1")
        mai   = col(row, headers, "adjudication", "mue_adj", "indicator",
                    "mue_adjudication_indicator", default="3")
        rationale = col(row, headers, "rationale", "reason", "note", default="")
        # Positional fallback
        if not code and len(row) >= 2:
            code, units = row[0].strip(), row[1].strip()
        if not code or len(code) < 3:
            continue
        text = (f"MUE Limit: CPT/HCPCS {code} maximum {units} unit(s) per day. "
                f"Adjudication indicator: {mai}. {rationale}".strip())
        ids.append(f"mue_{code}_{i}")
        texts.append(text)
        metas.append({"code": code, "max_units": units,
                      "adjudication_indicator": mai, "rationale": rationale[:200]})
    return _upsert(coll, ids, texts, metas, "MUE")


def ingest_ncci_combined(client, filepath: Path) -> int:
    """
    Handle a combined NCCI file that contains both PTP and MUE sections.
    Detects which section each row belongs to by column headers or structure.
    """
    headers, rows = read_file(filepath)
    header_str = " ".join(headers)

    # If it looks like MUE (has mue_value column)
    if any("mue" in h for h in headers):
        return ingest_mue(client, filepath)
    # If it looks like PTP (has column1/column2)
    elif any("column" in h or "col1" in h or "col2" in h for h in headers):
        return ingest_ncci_ptp(client, filepath)
    else:
        # Try PTP first (more common), then MUE
        n = ingest_ncci_ptp(client, filepath)
        return n


def ingest_lcd(client, filepath: Path) -> int:
    headers, rows = read_file(filepath)
    coll = get_coll(client, CHROMA_COLLECTION_LCD)

    ids, texts, metas = [], [], []

    def chunk_text(text, size=500):
        return [text[i:i+size] for i in range(0, len(text), size)]

    for i, row in enumerate(rows):

        # ✅ ID
        lid = col(row, headers, "lcd_id", "id", default=f"LCD_{i}")

        # ✅ MAIN TEXT (rules)
        rules = col(row, headers, "rules", "description", "desc", default="")

        # ✅ SECTION TEXT (optional but powerful)
        sections = col(row, headers, "sections", default="")

        # ✅ ICD codes
        icd_codes = col(row, headers, "icd_codes", "codes", default="")

        if not rules and not sections:
            continue

        # 🔥 Combine intelligently
        full_text = f"LCD {lid}: {rules}\n{sections}"

        # ✅ CHUNK (VERY IMPORTANT)
        chunks = chunk_text(full_text, 500)

        for j, chunk in enumerate(chunks):
            ids.append(f"lcd_{lid}_{i}_{j}")
            texts.append(chunk)

            metas.append({
                "lcd_id": lid,
                "chunk": j,
                "icd_codes": icd_codes[:200]
            })

    return _upsert(coll, ids, texts, metas, "LCD")

def ingest_ncd(client, filepath: Path) -> int:
    headers, rows = read_file(filepath)
    coll = get_coll(client, CHROMA_COLLECTION_NCD)
    ids, texts, metas = [], [], []
    for i, row in enumerate(rows):
        nid   = col(row, headers, "ncd_id", "id", "ncd", "ncd_number", default=f"NCD_{i}")
        title = col(row, headers, "title", "name", "ncd_name", "topic", default="")
        desc  = col(row, headers, "description", "desc", "coverage", "indication",
                    "narrative", default="")
        codes = col(row, headers, "codes", "applicable_codes", default="")
        if not desc and not title:
            continue
        text = f"NCD {nid}: {title}. {desc}"
        ids.append(f"ncd_{nid}_{i}")
        texts.append(text[:1000])
        metas.append({"ncd_id": nid, "title": title[:200],
                      "description": desc[:400], "applicable_codes": codes[:200]})
    return _upsert(coll, ids, texts, metas, "NCD")


def ingest_txt_guidelines(client, filepath: Path) -> int:
    """Plain-text guidelines — split by blank lines."""
    coll    = get_coll(client, CHROMA_COLLECTION_GUIDELINES)
    content = filepath.read_text(encoding="utf-8", errors="replace")
    chunks  = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 30]
    if not chunks:
        chunks = [l.strip() for l in content.splitlines() if len(l.strip()) > 30]
    ids   = [f"guide_{filepath.stem}_{i}"  for i in range(len(chunks))]
    texts = [c[:1000] for c in chunks]
    metas = [{"source": filepath.name, "chunk": i} for i in range(len(chunks))]
    return _upsert(coll, ids, texts, metas, "Guidelines")



def ingest_snomed(client, filepath: Path) -> int:
    """
    SNOMED CT ingestion — supports three formats:

    RF2 (official SNOMED release, sct2_Description_*.txt):
      id | effectiveTime | active | moduleId | conceptId | languageCode | typeId | term | caseSignificanceId
      Only active rows (active=1) and FSN/synonym typeIds are loaded.

    RF2 Concept file (sct2_Concept_*.txt):
      id | effectiveTime | active | moduleId | definitionStatusId
      (no human-readable term — skip this file, use Description instead)

    Simplified CSV/TXT:
      columns: conceptId/id/code + term/description/fsn + type/semanticTag

    Semantic type → entity type mapping:
      disorder, disease, finding, symptom  → diagnosis
      procedure, operation, therapy        → procedure
      substance                            → substance (medication)
      all others                           → concept
    """
    from config.settings import CHROMA_COLLECTION_SNOMED
    headers, rows = read_file(filepath)
    coll = get_coll(client, CHROMA_COLLECTION_SNOMED)
    ids, texts, metas = [], [], []

    import re as _re

    is_rf2_desc    = any(h in headers for h in ["descriptionid","typeid","languagecode"])
    is_rf2_concept = (any(h in headers for h in ["definitionstatusid","moduleid"])
                      and "typeid" not in headers)

    if is_rf2_concept:
        console.print("[yellow]  SNOMED: RF2 Concept file detected — "
                      "use the Description file (sct2_Description_*.txt) for terms.[/]")
        return 0

    for i, row in enumerate(rows):
        if is_rf2_desc:
            active = col(row, headers, "active", default="1")
            if active != "1":
                continue
            concept_id = col(row, headers, "conceptid")
            term       = col(row, headers, "term")
            type_id    = col(row, headers, "typeid", default="")
            # FSN = 900000000000003001, synonym = 900000000000013009
            if type_id not in ("900000000000003001", "900000000000013009", ""):
                continue
            if not concept_id or not term or len(term) < 3:
                continue
            m = _re.search(r"\(([^)]+)\)\s*$", term)
            sem_tag = m.group(1).lower() if m else "concept"
        else:
            concept_id = col(row, headers, "conceptid","id","snomedid","sctid","code","concept_id")
            term       = col(row, headers, "term","fsn","description","preferred_term",
                             "fully_specified_name","name")
            sem_tag    = col(row, headers, "type","semantic_tag","semantictag",
                             "hierarchy","semtag", default="concept").lower()
            if not concept_id or not term or len(term) < 3:
                continue

        entity_type = ("diagnosis"  if any(x in sem_tag for x in
                        ["disorder","disease","finding","symptom","morpholog"])
                       else "procedure" if any(x in sem_tag for x in
                        ["procedure","operation","therapy","regime","intervention"])
                       else "substance" if "substance" in sem_tag
                       else "concept")

        ids.append(f"sn_{concept_id}_{i}")
        texts.append(f"{concept_id} {term}")
        metas.append({"code": concept_id, "term": term[:300],
                      "semantic_tag": sem_tag[:50], "type": entity_type})

    return _upsert(coll, ids, texts, metas, "SNOMED CT")


# ── File → ingestor mapping (by stem / suffix patterns) ──────────────────────

def _route_file(client, filepath: Path) -> tuple[str, int]:
    """Auto-route a file to the correct ingestor based on its name."""
    stem = filepath.stem.lower()
    ext  = filepath.suffix.lower()

    if "snomed" in stem or "sct2_description" in stem or "sct2_concept" in stem:
        return "SNOMED CT", ingest_snomed(client, filepath)
    elif "icd" in stem:
        return "ICD-10", ingest_icd10(client, filepath)
    elif "cpt" in stem:
        return "CPT", ingest_cpt(client, filepath)
    elif "hcpcs" in stem or "hcpc" in stem:
        return "HCPCS", ingest_hcpcs(client, filepath)
    elif "ncci_ptp" in stem or "ptp" in stem:
        return "NCCI-PTP", ingest_ncci_ptp(client, filepath)
    elif "ncci_mue" in stem or "mue" in stem:
        return "MUE", ingest_mue(client, filepath)
    elif "ncci" in stem:
        return "NCCI-combined", ingest_ncci_combined(client, filepath)
    elif "lcd" in stem:
        return "LCD", ingest_lcd(client, filepath)
    elif "ncd" in stem:
        return "NCD", ingest_ncd(client, filepath)
    elif "guideline" in stem or "guide" in stem or "coding_rules" in stem:
        if ext == ".txt":
            return "Guidelines", ingest_txt_guidelines(client, filepath)
        return "Guidelines", ingest_lcd(client, filepath)  # use generic CSV reader
    else:
        return f"Unknown ({filepath.name})", 0


# ── Status ────────────────────────────────────────────────────────────────────

def show_status(client):
    from config.settings import CHROMA_COLLECTION_SNOMED
    entries = [
        (CHROMA_COLLECTION_SNOMED, "SNOMED CT",   "sct2_Description_*.txt / snomed.csv"),
        (CHROMA_COLLECTION_ICD10,  "ICD-10-CM",   "icd10.txt / icd10_codes.csv"),
        (CHROMA_COLLECTION_CPT,    "CPT",          "cpt.xlsx / cpt_codes.csv"),
        (CHROMA_COLLECTION_HCPCS,  "HCPCS",        "hcpcs.xlsx / hcpcs_codes.csv"),
        (CHROMA_COLLECTION_NCCI,   "NCCI PTP",     "ncci_ptp.txt"),
        (CHROMA_COLLECTION_MUE,    "MUE",          "ncci_mue.txt"),
        (CHROMA_COLLECTION_LCD,    "LCD",          "lcd_rules.csv"),
        (CHROMA_COLLECTION_NCD,    "NCD",          "ncd_rules.csv"),
        (CHROMA_COLLECTION_GUIDELINES, "Guidelines", "guidelines.txt (optional)"),
    ]
    t = Table(title="ChromaDB Knowledge Base Status",
              box=box.ROUNDED, border_style="cyan")
    t.add_column("Collection", style="bold yellow", width=14)
    t.add_column("Records",    style="bold",        width=10)
    t.add_column("Expected file",   style="dim",    width=30)
    t.add_column("Status",          width=14)
    for name, label, src in entries:
        try:
            count  = client.get_collection(name).count()
            status = "[green]✓ loaded[/]" if count > 50 else \
                     "[yellow]⚠ sparse[/]" if count > 0 else "[red]✗ empty[/]"
        except Exception:
            count, status = 0, "[red]✗ missing[/]"
        t.add_row(label, f"{count:,}", src, status)
    console.print(t)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ingest real medical coding data into ChromaDB")
    parser.add_argument("--collection",
                        choices=["snomed","icd10","cpt","hcpcs","ncci","mue","lcd","ncd","guidelines"],
                        help="Ingest only a specific collection")
    parser.add_argument("--file",    type=str, help="Path to a specific file to ingest")
    parser.add_argument("--clear",   action="store_true",
                        help="Delete and recreate all collections before ingesting")
    parser.add_argument("--status",  action="store_true",
                        help="Show current database record counts and exit")
    parser.add_argument("--data-dir", default=str(DATA_DIR),
                        help=f"Directory containing data files (default: {DATA_DIR})")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    client   = get_client()

    if args.status:
        show_status(client)
        return

    console.print(Panel(
        f"[bold cyan]Medical Coding AI — Data Ingestion[/]\n"
        f"Source directory : [yellow]{data_dir}[/]\n"
        f"ChromaDB path    : [yellow]{CHROMA_PERSIST_DIR}[/]\n"
        f"Supported formats: [dim]CSV, TXT, XLSX, XLS[/]",
        border_style="cyan"))

    if args.clear:
        console.print("[yellow]Clearing existing collections...[/]")
        for n in [CHROMA_COLLECTION_ICD10, CHROMA_COLLECTION_CPT, CHROMA_COLLECTION_HCPCS,
                  CHROMA_COLLECTION_NCCI, CHROMA_COLLECTION_MUE,
                  CHROMA_COLLECTION_LCD, CHROMA_COLLECTION_NCD, CHROMA_COLLECTION_GUIDELINES]:
            try: client.delete_collection(n)
            except Exception: pass
        console.print("[green]✓ Collections cleared[/]")

    # Specific file
    if args.file:
        fp = Path(args.file)
        if not fp.exists():
            console.print(f"[red]File not found: {fp}[/]")
            return
        console.print(f"\n[bold]Loading {fp.name}...[/]")
        label, n = _route_file(client, fp)
        console.print(f"  [green]✓ {label}: {n:,} records[/]")
        show_status(client)
        return

    # All files in data_dir
    SUPPORTED = {".csv", ".txt", ".xlsx", ".xls"}
    files = sorted([f for f in data_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in SUPPORTED
                    and not f.name.startswith(".")])

      # 🔥 COLLECTION FILTER (FIXED)
    if args.collection:
        COLLECTION_FILE_MAP = {
            "snomed": ["snomed", "sct2_description"],
            "icd10": ["icd"],
            "cpt": ["cpt"],
            "hcpcs": ["hcpcs", "hcpc"],
            "ncci": ["ncci_ptp", "ptp"],
            "mue": ["mue"],
            "lcd": ["lcd"],
            "ncd": ["ncd"],
            "guidelines": ["guideline", "guide"]
        }

        keywords = COLLECTION_FILE_MAP.get(args.collection, [])
        files = [
            f for f in files
            if any(k in f.stem.lower() for k in keywords)
        ]

        console.print(f"[cyan]Filtered collection: {args.collection}[/]")
        console.print(f"[dim]Files selected: {[f.name for f in files]}[/]")

    if not files:
        console.print(f"\n[yellow]No data files found in {data_dir}[/]")
        console.print(f"[dim]Supported: {', '.join(sorted(SUPPORTED))}[/]")
        console.print(f"[dim]See data/real/README.md for expected file names and formats.[/]")
        return

    total = 0
    t0    = time.time()
    for fp in files:
        console.print(f"\n[bold]→ {fp.name}[/]")
        try:
            label, n = _route_file(client, fp)
            if n == 0:
                console.print(f"  [yellow]⚠ No records ingested from {fp.name}[/]")
            else:
                console.print(f"  [green]✓ {label}: {n:,} records[/]")
                total += n
        except Exception as exc:
            console.print(f"  [red]✗ Failed: {exc}[/]")

    console.print(f"\n[bold green]✅ Done: {total:,} records in {time.time()-t0:.1f}s[/]")
    console.print()
    show_status(client)


if __name__ == "__main__":
    main()

