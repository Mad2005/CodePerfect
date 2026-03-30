"""
Clinical Terminology Mapping Agent
────────────────────────────────────
Maps extracted entities to SNOMED CT concepts using ChromaDB vector search.
Works with both mock seed data and real SNOMED RF2 / simplified datasets.

If SNOMED collection is empty, passes entities through unchanged
(pipeline continues — SNOMED mapping is optional enrichment).
"""
import copy
from core.vector_db import VectorKnowledgeBase
from core.models    import PipelineState, ClinicalEntities
from config.settings import CHROMA_COLLECTION_SNOMED


def _snomed_type_ok(meta: dict, expected: str) -> bool:
    """Accept if type matches, or if type is unset/concept (real data may vary)."""
    t = meta.get("type", "concept").lower()
    return t in (expected, "concept", "")


def terminology_mapping_agent(
    state: PipelineState,
    vdb: VectorKnowledgeBase,
) -> PipelineState:
    """LangGraph node: SNOMED CT mapping via vector similarity."""

    if state.clinical_entities is None:
        state.errors.append("TerminologyMappingAgent: no clinical entities to map")
        state.mapped_entities = ClinicalEntities()
        return state

    # Skip gracefully if SNOMED collection has no data
    snomed_count = vdb.collection_count(CHROMA_COLLECTION_SNOMED)
    if snomed_count == 0:
        state.mapped_entities = copy.deepcopy(state.clinical_entities)
        return state

    try:
        entities = copy.deepcopy(state.clinical_entities)

        for diag in entities.diagnoses:
            results = vdb.query(CHROMA_COLLECTION_SNOMED, diag.text, n_results=3)
            for r in results:
                meta = r.get("metadata", {})
                if _snomed_type_ok(meta, "diagnosis"):
                    diag.snomed_code        = meta.get("code", "")
                    diag.snomed_description = meta.get("term", r["text"])[:200]
                    break

        for proc in entities.procedures:
            results = vdb.query(CHROMA_COLLECTION_SNOMED, proc.text, n_results=3)
            for r in results:
                meta = r.get("metadata", {})
                if _snomed_type_ok(meta, "procedure"):
                    proc.snomed_code = meta.get("code", "")
                    break

        state.mapped_entities = entities

    except Exception as exc:
        state.errors.append(f"TerminologyMappingAgent error: {exc}")
        state.mapped_entities = copy.deepcopy(state.clinical_entities)

    return state
