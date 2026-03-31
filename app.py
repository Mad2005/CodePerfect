
from __future__ import annotations
import sys, os, json, time, threading, csv, re
from pathlib import Path
from typing import List, Dict, Any, Optional

from flask import Flask, request, jsonify, send_from_directory, render_template
import sqlite3
import uuid
from dotenv import load_dotenv

# Load env and local packages
load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from core.vector_db import VectorKnowledgeBase
from core.pipeline import run_pipeline
from core.models import HumanCodeInput, HumanCode
from utils.html_report import save_report

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
REPORTS = BASE_DIR / 'reports'
REPORTS.mkdir(exist_ok=True)
UPLOADS = BASE_DIR / 'uploads'
UPLOADS.mkdir(exist_ok=True)

_vdb: Optional[VectorKnowledgeBase] = None
_vdb_lock = threading.Lock()


def get_vdb() -> VectorKnowledgeBase:
    global _vdb
    with _vdb_lock:
        if _vdb is None:
            _vdb = VectorKnowledgeBase()
    return _vdb


# ------------------------
# Helper functions
# ------------------------

ICD10_RE = re.compile(r"^[A-Z][0-9]{2}(?:\.[A-Z0-9]{1,4})?$")
CPT_RE = re.compile(r"^[0-9]{5}$|^[0-9]{4}[A-Z]$")
HCPCS_RE = re.compile(r"^[A-Z][0-9]{4}$")


def detect_code_type(code: str) -> str:
    """Rudimentary code type detection from format."""
    c = code.strip().upper().replace(' ', '')
    if not c:
        return 'UNKNOWN'
    if CPT_RE.match(c):
        return 'CPT'
    if HCPCS_RE.match(c):
        return 'HCPCS'
    if ICD10_RE.match(c):
        return 'ICD-10'
    # Fallback: alphanumeric 3–7 chars treated as ICD-10
    return 'ICD-10'


def parse_human_codes_csv(path: Path) -> Dict[str, list]:
    """Parse CSV/TXT of human codes into icd10/cpt/hcpcs buckets.

    Supported formats:
      - header: code, description, type
      - header: code, description (type inferred from code format)
      - no header: code[, description][, type]
    """
    raw = path.read_text(encoding='utf-8', errors='replace')
    if not raw.strip():
        return {'icd10': [], 'cpt': [], 'hcpcs': []}

    # Try to guess delimiter from first line
    first = raw.splitlines()[0]
    delim = ','
    if first.count('	') > first.count(','):
        delim = '	'

    rows = [r for r in csv.reader(raw.splitlines(), delimiter=delim)]
    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        return {'icd10': [], 'cpt': [], 'hcpcs': []}

    header = [c.strip().lower() for c in rows[0]]
    has_header = any(k in header for k in ['code', 'icd', 'cpt', 'hcpcs', 'description', 'desc', 'type'])
    data_rows = rows[1:] if has_header else rows

    def get(row, names, default=''):
        if has_header:
            for name in names:
                if name in header:
                    idx = header.index(name)
                    if idx < len(row) and row[idx].strip():
                        return row[idx].strip()
        return default

    icd10, cpt, hcpcs = [], [], []

    for r in data_rows:
        # Best-effort positional fallback
        cells = [c.strip() for c in r if c.strip()]
        if not cells:
            continue

        code = get(r, ['code', 'icd', 'cpt', 'hcpcs']) or cells[0]
        desc = get(r, ['description', 'desc', 'name']) or (cells[1] if len(cells) > 1 else '')
        ctype = get(r, ['type', 'codetype', 'category']) or (cells[2] if len(cells) > 2 else '')
        units = 1
        try:
            units_txt = get(r, ['units', 'qty', 'quantity'])
            if units_txt.isdigit():
                units = int(units_txt)
        except Exception:
            units = 1

        if not code or len(code) < 3:
            continue

        if ctype:
            t = ctype.upper()
            if any(x in t for x in ['ICD', 'DIAG']):
                bucket = 'ICD-10'
            elif 'CPT' in t or 'PROC' in t:
                bucket = 'CPT'
            elif 'HCPCS' in t or 'HCPC' in t or 'SUPPLY' in t:
                bucket = 'HCPCS'
            else:
                bucket = detect_code_type(code)
        else:
            bucket = detect_code_type(code)

        entry = {'code': code.upper(), 'description': desc, 'units': units}
        if bucket == 'ICD-10':
            icd10.append(entry)
        elif bucket == 'CPT':
            cpt.append(entry)
        elif bucket == 'HCPCS':
            hcpcs.append(entry)
        else:
            icd10.append(entry)

    return {'icd10': icd10, 'cpt': cpt, 'hcpcs': hcpcs}


def infer_report_compliance_status(report_file: Path) -> Dict[str, Any]:
    """Infer report compliance status from saved HTML content.

    Returns:
      - status: "Completed" | "Needs Review"
      - is_compliant: bool | None
    """
    try:
        html = report_file.read_text(encoding='utf-8', errors='ignore')
        normalized = html.upper()

        if "✅ COMPLIANT" in normalized:
            return {"status": "Completed", "is_compliant": True}

        if "❌ NON-COMPLIANT" in normalized:
            return {"status": "Needs Review", "is_compliant": False}

        # Fallback if report doesn't include explicit compliance section.
        if "COMPLIANCE & RISK ASSESSMENT" in normalized:
            return {"status": "Needs Review", "is_compliant": None}

        return {"status": "Completed", "is_compliant": None}
    except Exception:
        return {"status": "Needs Review", "is_compliant": None}


def extract_text_from_file(path: Path) -> str:
    """Extract text from PDF/DOCX/TXT; fall back gracefully."""
    ext = path.suffix.lower()
    if ext == '.pdf':
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                return ''.join(p.extract_text() or '' for p in pdf.pages)
        except Exception:
            try:
                import PyPDF2
                with open(path, 'rb') as f:
                    r = PyPDF2.PdfReader(f)
                    return ' '.join(p.extract_text() or '' for p in r.pages)
            except Exception as e:
                raise RuntimeError(f'PDF parsing failed: {e}')
    elif ext in ('.docx', '.doc'):
        try:
            import docx
            d = docx.Document(path)
            return ' '.join(p.text for p in d.paragraphs)
        except Exception as e:
            raise RuntimeError(f'DOCX parsing failed: {e}')
    else:
        return path.read_text(encoding='utf-8', errors='replace')




@app.route('/report/<path:name>')
def serve_report(name: str):
    return send_from_directory(str(REPORTS), name)


# ------------------------
# API routes
# ------------------------

@app.route('/api/extract', methods=['POST'])
def api_extract():
    """Auto coding mode: generate codes from clinical notes only."""
    data = request.get_json() or {}
    note_text = (data.get('clinical_note') or '').strip()
    
    if not note_text:
        return jsonify({'status': 'error', 'message': 'Clinical note is required.'}), 400
    
    try:
        vdb = get_vdb()
        state = run_pipeline(note_text, vdb, human_codes=None)
        final = getattr(state, 'final_report', None)
        
        if not final:
            return jsonify({
                'status': 'error',
                'message': 'No report generated.',
                'errors': getattr(state, 'errors', [])
            }), 500
        
        # Convert to dict first, before saving report
        final_dict = final.model_dump() if hasattr(final, 'model_dump') else final.dict() if hasattr(final, 'dict') else (final if isinstance(final, dict) else vars(final))
        
        # Save HTML report automatically (may fail gracefully)
        ts = int(time.time())
        report_filename = f"generate_{ts}.html"
        try:
            report_path = save_report(final, str(REPORTS), report_filename)
        except Exception as e:
            state.errors.append(f"Report saving error: {str(e)}")
            report_path = None
        
        # Parse report data for JSON response
        report_data = {
            'status': 'ok',
            'mode': 'auto',
            'clinical_note': note_text[:500],
            'report': final_dict,
            'report_url': f"/report/{report_filename}",
            'report_path': str(report_path),
            'errors': getattr(state, 'errors', [])
        }
        
        return jsonify(report_data)
    except Exception as exc:
        import traceback
        return jsonify({
            'status': 'error',
            'message': str(exc),
            'trace': traceback.format_exc()
        }), 500


@app.route('/api/validate', methods=['POST'])
def api_validate():
    """Assisted coding mode: validate and enhance human codes with AI suggestions."""
    data = request.get_json() or {}
    note_text = (data.get('clinical_note') or '').strip()
    human_codes_list = data.get('human_codes') or []
    
    if not note_text:
        return jsonify({'status': 'error', 'message': 'Clinical note is required.'}), 400
    
    if not human_codes_list or not isinstance(human_codes_list, list):
        return jsonify({'status': 'error', 'message': 'Human codes are required.'}), 400
    
    try:
        # Parse human codes into buckets
        icdlist = []
        cptlist = []
        hcpcslist = []
        
        for code_str in human_codes_list:
            code = str(code_str).strip().upper()
            if not code:
                continue
            
            code_type = detect_code_type(code)
            entry = {'code': code, 'description': '', 'units': 1}
            
            if code_type == 'CPT':
                cptlist.append(entry)
            elif code_type == 'HCPCS':
                hcpcslist.append(entry)
            else:
                icdlist.append(entry)
        
        # Check if any valid codes were found after parsing
        total_codes = len(icdlist) + len(cptlist) + len(hcpcslist)
        if total_codes == 0:
            return jsonify({'status': 'error', 'message': 'No valid codes provided. Please enter at least one valid ICD-10, CPT, or HCPCS code.'}), 400
        
        human_codes = HumanCodeInput(
            coder_name='Human Coder',
            icd10_codes=[HumanCode(code=e['code'], description=e['description'], code_type='ICD-10', units=e['units']) for e in icdlist],
            cpt_codes=[HumanCode(code=e['code'], description=e['description'], code_type='CPT', units=e['units']) for e in cptlist],
            hcpcs_codes=[HumanCode(code=e['code'], description=e['description'], code_type='HCPCS', units=e['units']) for e in hcpcslist],
        )
        
        vdb = get_vdb()
        state = run_pipeline(note_text, vdb, human_codes=human_codes)
        final = getattr(state, 'final_report', None)
        
        if not final:
            return jsonify({
                'status': 'error',
                'message': 'No report generated.',
                'errors': getattr(state, 'errors', [])
            }), 500
        
        # Convert to dict first, before saving report
        final_dict = final.model_dump() if hasattr(final, 'model_dump') else final.dict() if hasattr(final, 'dict') else (final if isinstance(final, dict) else vars(final))
        
        # Save HTML report automatically (may fail gracefully)
        ts = int(time.time())
        report_filename = f"validate_{ts}.html"
        try:
            report_path = save_report(final, str(REPORTS), report_filename)
        except Exception as e:
            state.errors.append(f"Report saving error: {str(e)}")
            report_path = None
        
        report_data = {
            'status': 'ok',
            'mode': 'assisted',
            'clinical_note': note_text[:500],
            'report': final_dict,
            'report_url': f"/report/{report_filename}",
            'report_path': str(report_path),
            'errors': getattr(state, 'errors', [])
        }
        
        return jsonify(report_data)
    except Exception as exc:
        import traceback
        return jsonify({
            'status': 'error',
            'message': str(exc),
            'trace': traceback.format_exc()
        }), 500


@app.route('/api/reports')
def api_reports():
    files = sorted(REPORTS.glob('*.html'), key=lambda p: p.stat().st_mtime, reverse=True)

    def _build_report_item(f: Path) -> Dict[str, Any]:
        inferred = infer_report_compliance_status(f)
        return {
            'name': f.name,
            'mode': 'compare' if ('compare' in f.name or 'validate' in f.name) else 'generate',
            'status': inferred['status'],
            'is_compliant': inferred['is_compliant'],
        }

    return jsonify(
        reports=[_build_report_item(f) for f in files]
    )


@app.route('/api/delete/<filename>', methods=['DELETE'])
def api_delete_report(filename: str):
    """Delete a report file."""
    try:
        # Prevent directory traversal attacks
        if '/' in filename or '\\' in filename or '..' in filename:
            return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
        
        file_path = REPORTS / filename
        if not file_path.exists():
            return jsonify({'status': 'error', 'message': 'File not found'}), 404
        
        file_path.unlink()
        return jsonify({'status': 'ok', 'message': f'Deleted {filename}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/download/<filename>', methods=['GET'])
def api_download_report(filename: str):
    """Download report as HTML (user can print to PDF via browser)."""
    try:
        # Prevent directory traversal attacks
        if '/' in filename or '\\' in filename or '..' in filename:
            return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
        
        file_path = REPORTS / filename
        if not file_path.exists():
            return jsonify({'status': 'error', 'message': 'File not found'}), 404
        
        # Ensure it's an HTML file
        if not filename.endswith('.html'):
            return jsonify({'status': 'error', 'message': 'Only HTML reports can be downloaded'}), 400
        
        # Send file with attachment header so browser downloads it
        return send_from_directory(
            str(REPORTS), 
            filename,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/db-status')
def api_db_status():
    try:
        return jsonify(get_vdb().status)
    except Exception:
        return jsonify({}), 500


@app.route('/api/sample/<int:n>')
def api_sample(n: int):
    try:
        from data.sample_notes import (
            SAMPLE_NOTE_1_DIABETES_HYPERTENSION,
            SAMPLE_NOTE_2_APPENDECTOMY,
            SAMPLE_NOTE_3_CARDIAC,
            SAMPLE_NOTE_4_SIMPLE_PNEUMONIA,
        )
        mapping = {
            1: SAMPLE_NOTE_1_DIABETES_HYPERTENSION.strip(),
            2: SAMPLE_NOTE_2_APPENDECTOMY.strip(),
            3: SAMPLE_NOTE_3_CARDIAC.strip(),
            4: SAMPLE_NOTE_4_SIMPLE_PNEUMONIA.strip(),
        }
        return jsonify({'note': mapping.get(n, '')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/parse-codes', methods=['POST'])
def api_parse_codes():
    f = request.files.get('file')
    if not f or not f.filename:
        return jsonify({'icd10': [], 'cpt': [], 'hcpcs': []}), 400

    tmp = UPLOADS / f"codes_{int(time.time())}_{f.filename}"
    f.save(str(tmp))
    try:
        parsed = parse_human_codes_csv(tmp)
        return jsonify(parsed)
    except Exception as e:
        return jsonify({'error': str(e), 'icd10': [], 'cpt': [], 'hcpcs': []}), 500
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass


@app.route('/api/extract-note-file', methods=['POST'])
def api_extract_note_file():
    """Extract readable clinical note text from an uploaded file."""
    f = request.files.get('file')
    if not f or not f.filename:
        return jsonify({'status': 'error', 'message': 'No file uploaded.'}), 400

    ext = Path(f.filename).suffix.lower()
    if ext not in ('.txt', '.pdf', '.docx', '.doc'):
        return jsonify({'status': 'error', 'message': f'Unsupported file type {ext}. Use .txt, .pdf, or .docx.'}), 400

    tmp = UPLOADS / f"note_extract_{int(time.time())}_{f.filename}"
    f.save(str(tmp))
    try:
        extracted = extract_text_from_file(tmp)
        cleaned = '\n'.join(line.strip() for line in extracted.splitlines() if line.strip()).strip()
        if not cleaned:
            return jsonify({'status': 'error', 'message': 'No clinical text could be extracted from this file.'}), 400

        return jsonify({
            'status': 'ok',
            'filename': f.filename,
            'extracted_text': cleaned,
            'char_count': len(cleaned),
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass


@app.route('/api/run', methods=['POST'])
def api_run():
    mode = request.form.get('mode', 'generate')

    note_file = request.files.get('notefile')
    note_text = (request.form.get('note') or '').strip()

    if note_file and note_file.filename:
        ext = Path(note_file.filename).suffix.lower()
        if ext not in ('.txt', '.pdf', '.docx', '.doc', '.rtf'):
            return jsonify({'status': 'error', 'message': f'Unsupported file type {ext}'}), 400
        tmp = UPLOADS / f"note_{int(time.time())}_{note_file.filename}"
        note_file.save(str(tmp))
        try:
            note_text = extract_text_from_file(tmp).strip()
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 400
        finally:
            try:
                tmp.unlink()
            except Exception:
                pass

    if not note_text:
        return jsonify({'status': 'error', 'message': 'Clinical note is required.'}), 400

    # Human codes handling
    icdlist: list = []
    cptlist: list = []
    hcpcslist: list = []

    codes_file = request.files.get('codesfile')
    if codes_file and codes_file.filename:
        tmp2 = UPLOADS / f"codes_{int(time.time())}_{codes_file.filename}"
        codes_file.save(str(tmp2))
        try:
            parsed = parse_human_codes_csv(tmp2)
            icdlist.extend(parsed.get('icd10', []))
            cptlist.extend(parsed.get('cpt', []))
            hcpcslist.extend(parsed.get('hcpcs', []))
        except Exception:
            pass
        finally:
            try:
                tmp2.unlink()
            except Exception:
                pass

    # Manual JSON lists from UI
    for key, bucket, label in (
        ('icd10', icdlist, 'ICD-10'),
        ('cpt', cptlist, 'CPT'),
        ('hcpcs', hcpcslist, 'HCPCS'),
    ):
        raw = request.form.get(key, '').strip()
        if not raw:
            continue
        try:
            arr = json.loads(raw)
        except Exception:
            continue
        for e in arr:
            code = (e.get('code') or '').strip().upper()
            if not code:
                continue
            desc = e.get('description') or ''
            units = int(e.get('units') or 1)
            bucket.append({'code': code, 'description': desc, 'units': units, 'codetype': label})

    human_codes = None
    if icdlist or cptlist or hcpcslist:
        human_codes = HumanCodeInput(
            coder_name=request.form.get('codername') or 'Human Coder',
            icd10_codes=[HumanCode(code=e['code'], description=e['description'], code_type='ICD-10', units=e['units']) for e in icdlist],
            cpt_codes=[HumanCode(code=e['code'], description=e['description'], code_type='CPT', units=e['units']) for e in cptlist],
            hcpcs_codes=[HumanCode(code=e['code'], description=e['description'], code_type='HCPCS', units=e['units']) for e in hcpcslist],
        )

    try:
        vdb = get_vdb()
        state = run_pipeline(note_text, vdb, human_codes)
        final = getattr(state, 'final_report', None)
        if not final:
            return jsonify({'status': 'error', 'message': 'No report generated.', 'errors': getattr(state, 'errors', [])}), 500

        ts = int(time.time())
        tag = 'compare' if human_codes is not None or mode == 'compare' else 'generate'
        fname = f"{tag}_{ts}.html"
        save_report(final, str(REPORTS), fname)

        return jsonify({'status': 'ok', 'url': f"/report/{fname}", 'mode': tag, 'errors': getattr(state, 'errors', [])})
    except Exception as exc:
        import traceback
        return jsonify({'status': 'error', 'message': str(exc), 'trace': traceback.format_exc()}), 500


# ------------------------
# Review queue endpoints
# ------------------------


# ------------------------
# Entrypoint
# ------------------------


def main():
    import argparse, webbrowser

    p = argparse.ArgumentParser()
    p.add_argument('--port', type=int, default=5000)
    p.add_argument('--no-browser', action='store_true')
    args = p.parse_args()

    print(f"MedCode AI http://localhost:{args.port}")
    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{args.port}")).start()

    app.run(host='0.0.0.0', port=args.port, debug=False)


if __name__ == '__main__':
    main()
