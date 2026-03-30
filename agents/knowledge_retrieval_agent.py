"""
Knowledge Retrieval Agent  (split retrieval per agent)
───────────────────────────────────────────────────────
Fetches separate knowledge sets for each coding agent:
  clinical_guidelines  → ICD-10 codes + SNOMED + clinical coding rules
  revenue_guidelines   → CPT + HCPCS + billing policies + E&M guidelines
  retrieved_rules      → NCCI + MUE + LCD + NCD compliance rules
  retrieved_guidelines → combined (for justification agent)
"""
from core.vector_db import VectorKnowledgeBase
from core.models import PipelineState
from config.settings import (
    CHROMA_COLLECTION_SNOMED, CHROMA_COLLECTION_ICD10,
    CHROMA_COLLECTION_CPT,    CHROMA_COLLECTION_HCPCS,
    CHROMA_COLLECTION_NCCI,   CHROMA_COLLECTION_MUE,
    CHROMA_COLLECTION_LCD,    CHROMA_COLLECTION_NCD,
    CHROMA_COLLECTION_GUIDELINES,
)


def knowledge_retrieval_agent(state: PipelineState, vdb: VectorKnowledgeBase) -> PipelineState:
    entities = state.mapped_entities or state.clinical_entities
    if entities is None:
        state.errors.append("KnowledgeRetrievalAgent: no entities available")
        return state

    clinical_kb: list[str] = []
    revenue_kb:  list[str] = []
    rules_kb:    list[str] = []

    try:
        diag_queries = [d.text for d in entities.diagnoses[:5]]
        proc_queries = [p.text for p in entities.procedures[:5]]
        med_queries  = [m.text for m in entities.medications[:4]]
        all_queries  = diag_queries + proc_queries

        # ── Clinical knowledge: ICD-10 + SNOMED + clinical guidelines ─────────
        for q in diag_queries:
            for item in vdb.query(CHROMA_COLLECTION_ICD10, q, n_results=3):
                if item["text"] not in clinical_kb:
                    clinical_kb.append(item["text"])
            for item in vdb.query(CHROMA_COLLECTION_SNOMED, q, n_results=2):
                if item["text"] not in clinical_kb:
                    clinical_kb.append(item["text"])

        for item in vdb.query(CHROMA_COLLECTION_GUIDELINES,
                              "ICD-10 diagnosis sequencing principal secondary", n_results=4):
            if item["text"] not in clinical_kb:
                clinical_kb.append(item["text"])

        # ── Revenue knowledge: CPT + HCPCS + billing guidelines ──────────────
        for q in proc_queries:
            for item in vdb.query(CHROMA_COLLECTION_CPT, q, n_results=3):
                if item["text"] not in revenue_kb:
                    revenue_kb.append(item["text"])
        for q in med_queries:
            for item in vdb.query(CHROMA_COLLECTION_HCPCS, q, n_results=2):
                if item["text"] not in revenue_kb:
                    revenue_kb.append(item["text"])

        for item in vdb.query(CHROMA_COLLECTION_GUIDELINES,
                              "CPT procedure billing E&M level revenue HCPCS", n_results=4):
            if item["text"] not in revenue_kb:
                revenue_kb.append(item["text"])

        # ── Compliance rules (shared) ─────────────────────────────────────────
        for q in all_queries:
            for col in [CHROMA_COLLECTION_NCCI, CHROMA_COLLECTION_MUE,
                        CHROMA_COLLECTION_LCD,  CHROMA_COLLECTION_NCD]:
                for item in vdb.query(col, q, n_results=2):
                    if item["text"] not in rules_kb:
                        rules_kb.append(item["text"])

        state.clinical_guidelines  = clinical_kb
        state.revenue_guidelines   = revenue_kb
        state.retrieved_rules      = rules_kb
        state.retrieved_guidelines = clinical_kb + revenue_kb   # combined for justification

    except Exception as exc:
        state.errors.append(f"KnowledgeRetrievalAgent error: {exc}")

    return state
