# 🏥 Medical Coding AI System

An enterprise-grade AI-powered medical coding and compliance auditing system built with:

| Layer | Technology |
|-------|-----------|
| LLM | Google Gemini 2.0 Flash Preview |
| Agent Framework | LangGraph |
| Vector Database | ChromaDB |
| Compliance | NCCI + MUE + LCD + NCD |
| Code Sets | ICD-10-CM + CPT + HCPCS + SNOMED CT |

---

## System Architecture

```
Hospital EHR / Clinical Note
         │
         ▼
┌─────────────────────────────┐
│  Text Processing Agent      │  Clean notes, expand abbreviations, normalise
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│  NLP Extraction Agent       │  Extract diagnoses, procedures, medications
│  (Gemini LLM)               │
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│  SNOMED CT Terminology      │  Map entities → SNOMED CT concepts
│  Mapping Agent              │
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│  Knowledge Retrieval Agent  │  RAG from ChromaDB:
│  (RAG via ChromaDB)         │  ICD-10 / CPT / HCPCS / NCCI / MUE / LCD / NCD
└────────────┬────────────────┘
             │
    ┌────────┴────────┐
    │                 │
┌───▼───────┐  ┌──────▼──────────┐
│ Clinical  │  │ Revenue         │
│ Accuracy  │  │ Optimization    │
│ Agent     │  │ Agent           │
│ (ICD-10)  │  │ (CPT + HCPCS)   │
└───┬───────┘  └──────┬──────────┘
    └────────┬────────┘
             │
┌────────────▼────────────────┐
│  Rule Validation Engine     │  NCCI edits, MUE limits, LCD/NCD checks
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│  Auditor Agent              │  Upcoding / downcoding detection
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│  Justification Agent        │  Clinical evidence + guideline references
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│  Confidence Scoring Engine  │  Per-code confidence + compliance risk score
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│  Report Generation Agent    │  Assemble final FinalCodingReport
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│  FINAL COMPLIANCE REPORT    │
│  • ICD-10 / CPT / HCPCS     │
│  • Compliance violations    │
│  • Audit findings           │
│  • Confidence scores        │
│  • Clinical justifications  │
└─────────────────────────────┘
```

---

## Compliance Validation Layer

| Rule | Purpose |
|------|---------|
| NCCI Edits | Prevent incorrect CPT code combinations |
| MUE Limits | Limit number of services billed per day |
| LCD Rules | Regional Medicare coverage criteria |
| NCD Rules | National Medicare coverage policy |

---

## Project Structure

```
medical_coding_ai/
├── main.py                          # Entry point
├── requirements.txt
├── .env.example
├── config/
│   └── settings.py                  # API keys, thresholds, collection names
├── core/
│   ├── models.py                    # Pydantic data models + LangGraph state
│   ├── llm.py                       # Gemini LLM wrapper
│   ├── vector_db.py                 # ChromaDB manager + seed data
│   └── pipeline.py                  # LangGraph graph wiring
├── agents/
│   ├── text_processing_agent.py     # Clean + normalise clinical text
│   ├── nlp_extraction_agent.py      # Extract clinical entities
│   ├── terminology_mapping_agent.py # Map to SNOMED CT
│   ├── knowledge_retrieval_agent.py # RAG retrieval
│   ├── coding_agents.py             # Clinical Accuracy + Revenue Optimization
│   ├── rule_validation_engine.py    # NCCI + MUE + LCD + NCD
│   ├── auditor_agent.py             # Upcoding/downcoding detection
│   ├── justification_agent.py       # Clinical justifications
│   ├── confidence_scoring_engine.py # Confidence + risk scoring
│   └── report_generation_agent.py  # Assemble final report
├── data/
│   └── sample_notes.py              # 3 realistic clinical notes
└── utils/
    └── report_renderer.py           # Rich console report renderer
```

---

## Setup

### 1. Install dependencies

```bash
cd medical_coding_ai
pip install -r requirements.txt
```

### 2. Set your Gemini API key

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

Or export directly:
```bash
export GEMINI_API_KEY="your_api_key_here"
```

### 3. Run

```bash
# Default: run diabetes/hypertension note
python main.py

# Specific sample note
python main.py --note 1    # Diabetes + Hypertension + CKD
python main.py --note 2    # Acute Appendicitis
python main.py --note 3    # STEMI + Three-Vessel CAD

# All sample notes
python main.py --all

# Custom clinical note
python main.py --custom "Patient presents with chest pain and shortness of breath..."
```

---

## Output

The system produces a rich console report containing:

- **ICD-10-CM codes** with descriptions, type (principal/secondary), and confidence
- **CPT procedure codes** with units and confidence scores
- **HCPCS Level II codes** for drugs, DME, and supplies
- **Compliance validation** – NCCI, MUE, LCD, NCD results
- **Audit findings** – upcoding, downcoding, missing codes flagged by severity
- **Code justifications** – clinical evidence + guideline references per code
- **Confidence & risk scores** – visual bars for each code type + risk level
- **Recommendations** – actionable items before claim submission

---

## Extending the System

### Add real NCCI/MUE/LCD/NCD data
Replace or augment the seed data in `core/vector_db.py` with official CMS data files.

### Add a REST API
Wrap `run_pipeline()` in a FastAPI route for EHR integration.

### Add human-in-the-loop
Use LangGraph's `interrupt_before` to pause at the auditor node for human review.

### Scale the knowledge base
Import full ICD-10, CPT, and HCPCS code sets into ChromaDB using the existing `VectorKnowledgeBase` API.
