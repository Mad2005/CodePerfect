## LangGraph Checkpointer Setup & Testing

### Quick Start

#### 1. **Install Dependencies**

```powershell
# Option A: Use setup script
python setup_checkpointer.py

# Option B: Manual install
pip install langgraph-checkpoint-sqlite
```

#### 2. **Run Quick Test (No VectorDB needed)**

```powershell
python test_checkpointer.py
```

Expected output:
```
✅ Path              ✅ PASS
✅ Import            ✅ PASS    # After installing langgraph-checkpoint-sqlite
✅ Thread ID         ✅ PASS
✅ DB Structure      ⏳ PENDING # Will be ✅ after first pipeline run
✅ Records          ⏳ PENDING # Will be ✅ after first pipeline run
✅ .gitignore        ✅ PASS
```

#### 3. **Run Integration Test (After full setup)**

```powershell
python test_checkpointer_integration.py
```

This will:
- Initialize VectorDB
- Run a sample pipeline with checkpointing
- Verify checkpoints were saved to `data/checkpoints.db`
- Confirm thread_id tracking works

---

### What Gets Tested

#### **Test 1: Checkpoint DB Path**
✅ Confirms path: `data/checkpoints.db`

#### **Test 2: Pipeline Import & Checkpointer**
- ✅ Pipeline imports with `SqliteSaver`
- ✅ Graceful fallback if checkpointer fails

#### **Test 3: Thread ID Generation**
✅ Both auto-generated (UUID) and custom thread IDs work

#### **Test 4: Checkpoint DB Structure**
- ✅ SQLite database created (after first run)
- ✅ Checkpoint tables exist

#### **Test 5: Checkpoint Records**
✅ Checkpoint entries saved per thread_id

#### **Test 6: .gitignore**
✅ Checkpoint DB excluded from git

#### **Test 7: Pipeline Integration**
✅ Full pipeline execution with state persistence

---

### Manual Verification

```powershell
# Check if database exists
Test-Path data/checkpoints.db

# View checkpoint tables (requires sqlite3)
sqlite3 data/checkpoints.db ".tables"

# Count total checkpoints
sqlite3 data/checkpoints.db "SELECT COUNT(*) FROM checkpoints;"

# List unique thread IDs
sqlite3 data/checkpoints.db "SELECT DISTINCT thread_id FROM checkpoints LIMIT 10;"

# View latest checkpoint for a thread
sqlite3 data/checkpoints.db ^
  "SELECT thread_id, checkpoint_ns FROM checkpoints WHERE thread_id='thread_id_here' LIMIT 1;"
```

---

### File Locations

```
medical_coding_ai/
├── setup_checkpointer.py           # Install dependencies
├── test_checkpointer.py            # Quick validation (no VectorDB)
├── test_checkpointer_integration.py # Full test (requires VectorDB)
├── core/
│   └── pipeline.py                  # Contains _get_checkpointer()
├── data/
│   └── checkpoints.db               # Created on first run
└── .gitignore                       # Includes checkpoints.db*
```

---

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: langgraph.checkpoint.sqlite` | Run: `pip install langgraph-checkpoint-sqlite` |
| `cannot import name 'get_vdb'` | Fixed - use `from app import get_vdb` |
| `data/checkpoints.db not found` | Normal - created on first pipeline run |
| `sqlite3 command not found` | Install sqlite3: `choco install sqlite` (Windows) |

---

### How Checkpointing Works

1. **Pipeline builds** with `SqliteSaver` checkpointer
2. **Each agent execution** saves state to checkpoint
3. **Thread ID** tracks related executions
4. **DB location**: `data/checkpoints.db` (ignored in git)
5. **Graceful fallback**: If checkpointer fails, pipeline continues without checkpoints

---

### Using Thread IDs in Your Code

```python
from core.pipeline import run_pipeline
import uuid

# Auto-generate UUID
state = run_pipeline(clinical_note, vdb)  # thread_id auto-generated

# Custom thread ID for tracking
patient_id = "patient_12345"
state = run_pipeline(clinical_note, vdb, thread_id=patient_id)

# In Flask routes
@app.route('/api/code', methods=['POST'])
def api_code():
    session_id = request.headers.get('X-Session-ID', str(uuid.uuid4()))
    state = run_pipeline(note_text, vdb, thread_id=session_id)
    return jsonify({'report': state.final_report})
```

---

### Next Steps

✅ Run tests to verify setup
✅ Update Flask routes to include thread_id tracking  
✅ Monitor `data/checkpoints.db` growth (expect 1-5MB per 100 runs)
✅ Optionally query checkpoint history for auditing

