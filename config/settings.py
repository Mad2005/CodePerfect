"""
Configuration — all values from .env
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL",   "meta-llama/llama-4-scout-17b-16e-instruct")

# ChromaDB lives inside the data/ folder (not project root)
_BASE = Path(__file__).parent.parent / "data"
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(_BASE / "chroma_db"))

CHROMA_COLLECTION_SNOMED     = "snomed_ct"
CHROMA_COLLECTION_ICD10      = "icd10_codes"
CHROMA_COLLECTION_CPT        = "cpt_codes"
CHROMA_COLLECTION_HCPCS      = "hcpcs_codes"
CHROMA_COLLECTION_NCCI       = "ncci_edits"
CHROMA_COLLECTION_MUE        = "mue_limits"
CHROMA_COLLECTION_LCD        = "lcd_rules"
CHROMA_COLLECTION_NCD        = "ncd_rules"
CHROMA_COLLECTION_GUIDELINES = "coding_guidelines"

HIGH_CONFIDENCE_THRESHOLD   = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.65
LOW_CONFIDENCE_THRESHOLD    = 0.45

HIGH_RISK_THRESHOLD   = float(os.getenv("HIGH_RISK_THRESHOLD",   "0.70"))
MEDIUM_RISK_THRESHOLD = float(os.getenv("MEDIUM_RISK_THRESHOLD", "0.40"))