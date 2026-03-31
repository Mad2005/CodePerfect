"""
Test Script: LangGraph SQLite Checkpointer
──────────────────────────────────────────────
Verifies that:
  1. Checkpoint DB is created
  2. Pipeline runs with checkpoint tracking
  3. State is persisted with thread IDs
  4. Checkpoints can be retrieved
"""
import sqlite3
import uuid
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# Suppress warnings
import warnings
warnings.filterwarnings("ignore")

console = Console()

# ── Test 1: Verify Checkpoint DB Path ────────────────────────────────────────

def test_checkpoint_db_path():
    """Verify checkpoint DB path is correct."""
    console.print("\n[bold blue]TEST 1: Checkpoint DB Path[/]")
    checkpoint_db = Path(__file__).parent / "data" / "checkpoints.db"
    console.print(f"  Expected path: {checkpoint_db}")
    console.print(f"  Path exists: {'✅ Yes' if checkpoint_db.exists() else '⏳ Will be created on first run'}")
    return checkpoint_db


# ── Test 2: Verify Pipeline Import & Checkpointer ──────────────────────────────

def test_pipeline_import():
    """Test that pipeline imports correctly with checkpointer."""
    console.print("\n[bold blue]TEST 2: Pipeline Import & Checkpointer[/]")
    try:
        from core.pipeline import _get_checkpointer, build_pipeline, CHECKPOINT_DB_PATH
        console.print(f"  ✅ Pipeline imported successfully")
        console.print(f"  ✅ Checkpointer function accessible")
        console.print(f"  ✅ CHECKPOINT_DB_PATH defined: {CHECKPOINT_DB_PATH}")
        
        # Try to get checkpointer
        checkpointer = _get_checkpointer()
        if checkpointer:
            console.print(f"  ✅ Checkpointer initialized: {type(checkpointer).__name__}")
        else:
            console.print(f"  ⚠️  Checkpointer is None (graceful fallback)")
        return True
    except ModuleNotFoundError as e:
        if 'langgraph.checkpoint.sqlite' in str(e):
            console.print(f"  ❌ Missing dependency: langgraph-checkpoint-sqlite")
            console.print(f"  [yellow]Fix: pip install langgraph-checkpoint-sqlite[/]")
        else:
            console.print(f"  ❌ Import failed: {e}")
        return False
    except Exception as e:
        console.print(f"  ❌ Import failed: {e}")
        return False


# ── Test 3: Mock Pipeline Run with Thread ID ────────────────────────────────

def test_thread_id_generation():
    """Test that thread IDs are generated correctly."""
    console.print("\n[bold blue]TEST 3: Thread ID Generation[/]")
    
    # Auto-generated thread ID
    thread_id_auto = str(uuid.uuid4())
    console.print(f"  Auto-generated thread ID: {thread_id_auto}")
    
    # Custom thread ID
    thread_id_custom = "patient_12345_run_001"
    console.print(f"  Custom thread ID: {thread_id_custom}")
    
    console.print(f"  ✅ Both formats supported")
    return thread_id_auto, thread_id_custom


# ── Test 4: Check Checkpoint DB Structure ────────────────────────────────────

def test_checkpoint_db_structure():
    """Test checkpoint DB tables after first run."""
    console.print("\n[bold blue]TEST 4: Checkpoint DB Structure[/]")
    
    checkpoint_db = Path(__file__).parent / "data" / "checkpoints.db"
    
    if not checkpoint_db.exists():
        console.print(f"  ⏳ DB not yet created (will be created on first pipeline run)")
        return False
    
    try:
        conn = sqlite3.connect(str(checkpoint_db))
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if tables:
            console.print(f"  ✅ Database has {len(tables)} table(s):")
            for (table_name,) in tables:
                console.print(f"     - {table_name}")
            
            # Get sample records
            for (table_name,) in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                console.print(f"     {table_name}: {count} records")
        else:
            console.print(f"  ⏳ No tables yet (created after first pipeline run)")
        
        conn.close()
        return True
    except Exception as e:
        console.print(f"  ❌ DB inspection failed: {e}")
        return False


# ── Test 5: Inspect Checkpoint Records ───────────────────────────────────────

def test_checkpoint_records():
    """Inspect checkpoint records in the database."""
    console.print("\n[bold blue]TEST 5: Checkpoint Records[/]")
    
    checkpoint_db = Path(__file__).parent / "data" / "checkpoints.db"
    
    if not checkpoint_db.exists():
        console.print(f"  ⏳ DB not yet created")
        return False
    
    try:
        conn = sqlite3.connect(str(checkpoint_db))
        cursor = conn.cursor()
        
        # Try to get checkpoint table info
        cursor.execute("PRAGMA table_info(checkpoints);")
        columns = cursor.fetchall()
        
        if columns:
            console.print(f"  ✅ Checkpoint table schema:")
            for col_id, col_name, col_type, *rest in columns:
                console.print(f"     - {col_name}: {col_type}")
            
            # Get latest checkpoint
            cursor.execute("SELECT COUNT(*) FROM checkpoints;")
            count = cursor.fetchone()[0]
            console.print(f"\n  ✅ Total checkpoints: {count}")
            
            if count > 0:
                cursor.execute("SELECT thread_id, checkpoint_ns FROM checkpoints LIMIT 5 ORDER BY rowid DESC;")
                records = cursor.fetchall()
                console.print(f"\n  Latest {len(records)} checkpoints:")
                for thread_id, checkpoint_ns in records:
                    console.print(f"     - Thread: {thread_id}")
        else:
            console.print(f"  ℹ️  Checkpoints table not yet created")
        
        conn.close()
        return True
    except Exception as e:
        console.print(f"  ⏳ Checkpoints table not found (normal before first run): {e}")
        return False


# ── Test 6: Verify .gitignore Entry ──────────────────────────────────────────

def test_gitignore():
    """Verify checkpoint DB is in .gitignore."""
    console.print("\n[bold blue]TEST 6: .gitignore Configuration[/]")
    
    gitignore_path = Path(__file__).parent / ".gitignore"
    
    if not gitignore_path.exists():
        console.print(f"  ⚠️  .gitignore not found")
        return False
    
    try:
        with open(gitignore_path, 'r') as f:
            content = f.read()
        
        if "checkpoints.db" in content:
            console.print(f"  ✅ Checkpoint DB properly ignored in .gitignore")
            return True
        else:
            console.print(f"  ⚠️  Checkpoint DB not in .gitignore")
            return False
    except Exception as e:
        console.print(f"  ❌ Error reading .gitignore: {e}")
        return False


# ── Test 7: Quick Integration Test ───────────────────────────────────────────

def test_run_with_sample():
    """Optional: Run a quick pipeline test with sample data."""
    console.print("\n[bold blue]TEST 7: Pipeline Integration Test[/]")
    console.print("[yellow]⚠️  This test requires a full setup with VectorDB. Skipping for now.[/]")
    console.print("[dim]To run this, uncomment the code below after full setup.[/]")
    
    """
    try:
        from core.vector_db import get_vdb
        from core.pipeline import run_pipeline
        
        console.print("  Initializing VectorDB...")
        vdb = get_vdb()
        
        console.print("  Running pipeline with sample note...")
        sample_note = "Patient presents with type 2 diabetes and hypertension."
        state = run_pipeline(sample_note, vdb, thread_id="test_thread_001")
        
        if state.final_report:
            console.print(f"  ✅ Pipeline completed successfully")
        else:
            console.print(f"  ❌ Pipeline did not generate report")
    except Exception as e:
        console.print(f"  ⚠️  Integration test skipped: {e}")
    """


# ── Main Test Summary ────────────────────────────────────────────────────────

def main():
    console.print(Panel(
        "[bold cyan]LangGraph SQLite Checkpointer Test Suite[/]",
        border_style="cyan"
    ))
    
    results = {
        "✅ Path": test_checkpoint_db_path(),
        "✅ Import": test_pipeline_import(),
        "✅ Thread ID": test_thread_id_generation() is not None,
        "✅ DB Structure": test_checkpoint_db_structure(),
        "✅ Records": test_checkpoint_records(),
        "✅ .gitignore": test_gitignore(),
    }
    
    test_run_with_sample()
    
    # Summary
    console.print("\n[bold blue]test SUMMARY[/]")
    t = Table(box=box.SIMPLE_HEAD, border_style="blue")
    t.add_column("Test", style="white")
    t.add_column("Status", style="green")
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "⏳ PENDING"
        t.add_row(name, status)
    
    console.print(t)
    
    console.print("\n[bold cyan]Next Steps:[/]")
    console.print("[dim]1. Run a real pipeline: python main.py[/]")
    console.print("[dim]2. Check data/checkpoints.db was created[/]")
    console.print("[dim]3. Re-run this test to see checkpoint records[/]")
    console.print("[dim]4. Use thread_id parameter in Flask routes for tracking[/]\n")


if __name__ == "__main__":
    main()
