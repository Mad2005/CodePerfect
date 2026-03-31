"""
ChromaDB Migration Script
──────────────────────────
Moves existing chroma_db from project root to data/chroma_db/
Run ONCE after updating to v19+:
    python migrate_chromadb.py
"""
import sys, shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

old_path = Path("./chroma_db")
new_path = Path("./data/chroma_db")

if old_path.exists() and not new_path.exists():
    print(f"Moving {old_path} → {new_path} ...")
    shutil.copytree(str(old_path), str(new_path))
    print(f"✓ Done. Old path still exists at {old_path} — you can delete it manually.")
elif new_path.exists():
    print(f"✓ data/chroma_db already exists ({sum(1 for _ in new_path.rglob('*'))} files). Nothing to do.")
elif not old_path.exists():
    print("No existing chroma_db found. Starting fresh — run: python data/ingest_real_data.py")
else:
    print(f"Both paths exist — using data/chroma_db (new location).")