"""
Flask Web Server
────────────────
Serves the HTML report in your browser with live reloading.
Also exposes a simple REST endpoint to run the pipeline on demand.

Usage:
    python server.py                  # serves latest report on http://localhost:5000
    python server.py --port 8080      # custom port
    python server.py --run-note 1     # run pipeline for note 1 then serve
"""
import sys
import argparse
import threading
import webbrowser
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, render_template_string, jsonify, request, send_from_directory
from rich.console import Console

console = Console()

import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

# In-memory store for the latest report HTML
_latest_html: str = ""
_latest_path: Path | None = None


# ── Index page ────────────────────────────────────────────────────────────────

INDEX = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>MedCode AI Server</title>
<style>
body{font-family:monospace;background:#0a0e1a;color:#e2e8f0;padding:40px;max-width:700px;margin:auto}
h1{color:#38bdf8;font-size:20px;margin-bottom:24px}
a{color:#818cf8;text-decoration:none}
a:hover{text-decoration:underline}
.btn{display:inline-block;background:#1f2937;border:1px solid #2d3748;padding:10px 20px;
     border-radius:6px;color:#38bdf8;margin:6px 0;cursor:pointer;font-family:monospace}
.btn:hover{background:#2d3748}
ul{list-style:none;padding:0}
li{padding:8px 0;border-bottom:1px solid #1f2937}
.ts{color:#94a3b8;font-size:11px;margin-left:12px}
</style>
</head>
<body>
<h1>🏥 MedCode AI — Report Server</h1>
<p style="color:#94a3b8;margin-bottom:24px">
  Server is running at <a href="http://localhost:{{port}}">http://localhost:{{port}}</a>
</p>

{% if reports %}
<h3 style="color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:.1em">
  Available Reports</h3>
<ul>
{% for r in reports %}
  <li>
    <a href="/report/{{r.name}}">{{r.name}}</a>
    <span class="ts">{{r.stat().st_size // 1024}} KB</span>
  </li>
{% endfor %}
</ul>
{% else %}
<p style="color:#94a3b8">No reports yet. Run the pipeline first:</p>
<pre style="background:#111827;padding:16px;border-radius:6px;color:#4ade80">
python main.py --note 1
</pre>
{% endif %}
</body>
</html>"""


@app.route("/")
def index():
    reports = sorted(REPORTS_DIR.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    port = request.host.split(":")[-1] if ":" in request.host else "5000"
    return render_template_string(INDEX, reports=reports, port=port)


@app.route("/report/<filename>")
def serve_report(filename):
    return send_from_directory(str(REPORTS_DIR), filename)


@app.route("/latest")
def latest():
    """Redirect to the most recently generated report."""
    reports = sorted(REPORTS_DIR.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not reports:
        return "<h2 style='font-family:monospace;color:#ef4444'>No reports found. Run python main.py first.</h2>", 404
    from flask import redirect
    return redirect(f"/report/{reports[0].name}")


@app.route("/api/run", methods=["POST"])
def api_run():
    """
    POST /api/run  { "note": "1" | "2" | "3", "human": true }
    Runs the pipeline and returns the report URL.
    """
    try:
        body     = request.get_json(force=True) or {}
        note_num = str(body.get("note", "1"))
        use_human = bool(body.get("human", True))

        from core.vector_db import VectorKnowledgeBase
        from core.pipeline  import run_pipeline
        from utils.html_report import save_report
        from data.sample_notes import (
            SAMPLE_NOTE_1_DIABETES_HYPERTENSION,
            SAMPLE_NOTE_2_APPENDECTOMY,
            SAMPLE_NOTE_3_CARDIAC,
        )
        from main import HUMAN_CODES_NOTE1, HUMAN_CODES_NOTE2, HUMAN_CODES_NOTE3, SAMPLE_NOTES

        title, text, human = SAMPLE_NOTES[note_num]
        vdb   = VectorKnowledgeBase()
        state = run_pipeline(text, vdb, human if use_human else None)

        if state.final_report:
            path = save_report(state.final_report, str(REPORTS_DIR),
                               f"report_note{note_num}.html")
            return jsonify({"status": "ok", "url": f"/report/{path.name}", "path": str(path)})
        else:
            return jsonify({"status": "error", "message": "Pipeline produced no report",
                            "errors": state.errors}), 500
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


def _open_browser(port: int) -> None:
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{port}/latest")


def main():
    parser = argparse.ArgumentParser(description="MedCode AI Report Server")
    parser.add_argument("--port",     type=int, default=5000, help="Port (default 5000)")
    parser.add_argument("--no-browser", action="store_true",  help="Don't auto-open browser")
    parser.add_argument("--run-note", choices=["1","2","3"],  help="Run pipeline before serving")
    args = parser.parse_args()

    if args.run_note:
        console.print(f"[cyan]Running pipeline for note {args.run_note} before starting server...[/]")
        from core.vector_db import VectorKnowledgeBase
        from core.pipeline  import run_pipeline
        from utils.html_report import save_report
        from main import SAMPLE_NOTES
        title, text, human = SAMPLE_NOTES[args.run_note]
        vdb   = VectorKnowledgeBase()
        state = run_pipeline(text, vdb, human)
        if state.final_report:
            path = save_report(state.final_report, str(REPORTS_DIR),
                               f"report_note{args.run_note}.html")
            console.print(f"[green]✅ Report saved: {path}[/]")
        else:
            console.print(f"[red]Pipeline errors: {state.errors}[/]")

    console.print(f"\n[bold cyan]🏥 MedCode AI Server[/]")
    console.print(f"[green]→ http://localhost:{args.port}[/]")
    console.print(f"[green]→ http://localhost:{args.port}/latest  (most recent report)[/]")
    console.print("[dim]Press Ctrl+C to stop[/]\n")

    if not args.no_browser:
        threading.Thread(target=_open_browser, args=(args.port,), daemon=True).start()

    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
