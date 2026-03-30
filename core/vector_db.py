"""
ChromaDB Vector Knowledge Base Manager
────────────────────────────────────────
Collections:
  icd10_codes        – ICD-10-CM diagnosis codes
  cpt_codes          – CPT procedure codes
  hcpcs_codes        – HCPCS Level II codes
  ncci_edits         – NCCI PTP bundling edits
  mue_limits         – Medically Unlikely Edit limits
  lcd_rules          – Local Coverage Determinations
  ncd_rules          – National Coverage Determinations
  coding_guidelines  – AHA/AMA/CMS coding guidelines
  snomed_ct          – SNOMED CT concepts (optional)

Data is loaded via: python data/ingest_real_data.py
Mock seed data has been removed — use real data files in data/real/.
"""
from __future__ import annotations
import chromadb
from chromadb.config import Settings
from rich.console import Console
from config.settings import (
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_SNOMED, CHROMA_COLLECTION_ICD10,
    CHROMA_COLLECTION_CPT,    CHROMA_COLLECTION_HCPCS,
    CHROMA_COLLECTION_NCCI,   CHROMA_COLLECTION_MUE,
    CHROMA_COLLECTION_LCD,    CHROMA_COLLECTION_NCD,
    CHROMA_COLLECTION_GUIDELINES,
)

console = Console()

ALL_COLLECTIONS = [
    CHROMA_COLLECTION_SNOMED,
    CHROMA_COLLECTION_ICD10,
    CHROMA_COLLECTION_CPT,
    CHROMA_COLLECTION_HCPCS,
    CHROMA_COLLECTION_NCCI,
    CHROMA_COLLECTION_MUE,
    CHROMA_COLLECTION_LCD,
    CHROMA_COLLECTION_NCD,
    CHROMA_COLLECTION_GUIDELINES,
]


class VectorKnowledgeBase:
    """ChromaDB manager — reads from real ingested data, no mock seeds."""

    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collections: dict[str, chromadb.Collection] = {}
        self._init_collections()

    def _init_collections(self) -> None:
        low_count_warned = []
        for name in ALL_COLLECTIONS:
            col = self.client.get_or_create_collection(
                name=name, metadata={"hnsw:space": "cosine"})
            self._collections[name] = col
            count = col.count()
            if count < 10 and name != CHROMA_COLLECTION_SNOMED:
                low_count_warned.append(f"{name}({count})")

        if low_count_warned:
            console.print(
                f"\n[yellow]⚠  Low record count in: {', '.join(low_count_warned)}\n"
                f"   Run: [bold]python data/ingest_real_data.py[/] to load real data.\n"
                f"   See: [bold]data/real/README.md[/] for required file formats.[/]\n"
            )

    def query(self, collection_name: str, query_text: str, n_results: int = 5) -> list[dict]:
        col = self._collections.get(collection_name)
        if col is None:
            return []
        count = col.count()
        if count == 0:
            return []
        n = min(n_results, count)
        try:
            results = col.query(query_texts=[query_text], n_results=n)
        except Exception:
            return []
        output = []
        for i, doc in enumerate(results["documents"][0]):
            output.append({
                "id"      : results["ids"][0][i],
                "text"    : doc,
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })
        return output

    def query_multi(self, collections: list[str], query_text: str,
                    n_results: int = 5) -> list[dict]:
        combined = []
        for name in collections:
            combined.extend(self.query(name, query_text, n_results))
        return combined

    def collection_count(self, name: str) -> int:
        col = self._collections.get(name)
        return col.count() if col else 0

    def status(self) -> dict[str, int]:
        return {name: self.collection_count(name) for name in ALL_COLLECTIONS}
