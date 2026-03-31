"""
RxNorm API Client  — Full Generic Implementation
══════════════════════════════════════════════════════════════════════════════
Uses the free NLM RxNorm REST API (rxnav.nlm.nih.gov/REST).
No API key required.  Rate limit: 20 req/s  (we stay at ~16 req/s).

COVERED API FUNCTIONS (from official NLM documentation)
────────────────────────────────────────────────────────
Core lookup
  findRxcuiByString          /rxcui?name=…
  findRxcuiById              /rxcui?idtype=…&id=…
  getApproximateMatch        /approximateTerm.json
  getRxNormName              /rxcui/{rxcui}
  getRxConceptProperties     /rxcui/{rxcui}/properties
  getAllProperties            /rxcui/{rxcui}/allProperties
  getRxProperty              /rxcui/{rxcui}/property
  getDisplayTerms            /displaynames
  getSpellingSuggestions     /spellingsuggestions

Related concepts
  getAllRelatedInfo           /rxcui/{rxcui}/allrelated
  getRelatedByType           /rxcui/{rxcui}/related?tty=…
  getRelatedByRelationship   /rxcui/{rxcui}/related?rela=…
  getDrugs                   /drugs?name=…
  getGenericProduct          /rxcui/{rxcui}/generic
  getMultiIngredBrand        /brands?ingredientids=…
  filterByProperty           /rxcui/{rxcui}/filterConcept
  getReformulationConcepts   /reformulationConcepts

NDC / Product
  getNDCs                    /rxcui/{rxcui}/ndcs
  getNDCProperties           /ndcproperties?id=…
  getNDCStatus               /ndcstatus?ndc=…
  getAllHistoricalNDCs        /rxcui/{rxcui}/allhistoricalndcs
  findRelatedNDCs            /relatedndcs
  findActiveProducts         /rxcui/{rxcui}/active

History / Status
  getRxcuiHistoryStatus      /rxcui/{rxcui}/historystatus
  getAllConceptsByStatus      /allstatus?status=…
  getAllConceptsByTTY         /allconcepts?tty=…
  getAllNDCsByStatus          /allNDCstatus?ndcstatus=…

Metadata
  getRxNormVersion           /version
  getTermTypes               /termtypes
  getIdTypes                 /idtypes
  getSourceTypes             /sourcetypes
  getPropCategories          /propCategories
  getPropNames               /propnames
  getRelaTypes               /relatypes
  getRelaPaths               /relapaths

Drug class  (RxClass API)
  get_drug_classes           /rxclass/class/byRxcui.json  (VA, ATC, MeSH …)

High-level helpers (used by pipeline)
  enrich_medications(texts)  — batch-enrich NER medication strings
  enrich_single(text)        — fully enrich one medication string
  is_rxnorm_available()      — connectivity check

All functions return plain dicts or lists; never raise on API failure.
"""
from __future__ import annotations

import re
import time
import json
import urllib.request
import urllib.parse
from functools import lru_cache
from typing import Optional, Any

# ── Constants ─────────────────────────────────────────────────────────────────

RXNORM_BASE  = "https://rxnav.nlm.nih.gov/REST"
RXCLASS_BASE = "https://rxnav.nlm.nih.gov/REST/rxclass"
_TIMEOUT     = 6       # seconds per HTTP request
_RATE_GAP    = 0.065   # ~15 req/s  (limit is 20/s)


# ═════════════════════════════════════════════════════════════════════════════
#  LOW-LEVEL HTTP
# ═════════════════════════════════════════════════════════════════════════════

def _get(url: str) -> Optional[dict]:
    """HTTP GET → parsed JSON dict, or None on any failure. Never raises."""
    try:
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "MedCodeAI/1.0"},
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _q(text: str) -> str:
    """URL-encode a query string."""
    return urllib.parse.quote(str(text), safe="")


# ═════════════════════════════════════════════════════════════════════════════
#  MEDICATION NAME CLEANING
# ═════════════════════════════════════════════════════════════════════════════

_DOSE_RE = re.compile(
    r'\b\d+(\.\d+)?\s*(mg|mcg|ug|g|ml|l|cc|%|units?|iu|meq|mmol|mEq)\b',
    re.IGNORECASE,
)
_ROUTE_RE = re.compile(
    r'\b(IV|IM|PO|SC|SQ|SL|PR|TOP|INH|OPH|ORAL|INHAL|INTRANASAL|TRANSDERMAL'
    r'|SUBCUT|INTRAMUSCULAR|INTRAVENOUS|SUBLINGUAL|TOPICAL|OPHTHALMIC)\b',
    re.IGNORECASE,
)
_FREQ_RE = re.compile(
    r'\b(QD|BID|TID|QID|PRN|QHS|QAM|QPM|Q\d+H|ONCE\s*DAILY|TWICE\s*DAILY'
    r'|DAILY|WEEKLY|MONTHLY|EVERY\s*\d+\s*(HOURS?|DAYS?|WEEKS?))\b',
    re.IGNORECASE,
)
_FORM_RE = re.compile(
    r'\b(TABLET|CAPSULE|SOLUTION|SUSPENSION|INJECTION|CREAM|OINTMENT|GEL'
    r'|PATCH|INHALER|SYRUP|DROPS?|SPRAY|INFUSION|EXTENDED.RELEASE|XR|ER|SR)\b',
    re.IGNORECASE,
)


def clean_med_name(text: str) -> str:
    """
    Strip dose, route, frequency, and dosage-form details from a raw
    medication string to produce a clean drug name for RxNorm lookup.

    Examples:
      "metformin 500mg BID"          -> "metformin"
      "IV ceftriaxone 1g daily"      -> "ceftriaxone"
      "lisinopril 10 mg oral tablet" -> "lisinopril"
      "insulin glargine 100 units"   -> "insulin glargine"
    """
    text = _DOSE_RE.sub("", text)
    text = _ROUTE_RE.sub("", text)
    text = _FREQ_RE.sub("", text)
    text = _FORM_RE.sub("", text)
    return " ".join(text.split()).strip()


# ═════════════════════════════════════════════════════════════════════════════
#  CORE LOOKUP FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1024)
def find_rxcui_by_string(name: str, search: int = 2, active_only: bool = False) -> Optional[str]:
    """
    findRxcuiByString — GET /rxcui.json?name=…

    search: 0=exact  1=normalized  2=approximate (default)
    Returns first matching RxCUI or None.
    """
    params = f"name={_q(name)}&search={search}"
    if active_only:
        params += "&allsrc=0"
    data = _get(f"{RXNORM_BASE}/rxcui.json?{params}")
    try:
        return data["idGroup"]["rxnormId"][0]
    except (KeyError, IndexError, TypeError):
        return None


@lru_cache(maxsize=1024)
def find_rxcui_by_id(id_type: str, id_value: str, active_only: bool = False) -> Optional[str]:
    """
    findRxcuiById — GET /rxcui.json?idtype=…&id=…

    id_type: 'NDC', 'NUI', 'UMLSCUI', 'VUID', 'RXAUI', 'ATC',
             'SNOMEDCT', 'CVX', 'DRUGBANK', 'FDBMK', 'GCN_SEQNO', …
    """
    scope = "ACTIVE" if active_only else "CURRENT"
    data  = _get(f"{RXNORM_BASE}/rxcui.json?idtype={_q(id_type)}&id={_q(id_value)}"
                 f"&allsrc=0&srclist={scope}")
    try:
        return data["idGroup"]["rxnormId"][0]
    except (KeyError, IndexError, TypeError):
        return None


@lru_cache(maxsize=1024)
def get_approximate_match(term: str, max_entries: int = 5) -> list[dict]:
    """
    getApproximateMatch — GET /approximateTerm.json?term=…&maxEntries=…

    Returns up to max_entries candidates sorted by score (highest first).
    Each dict contains: rxcui, rxaui, score, rank
    """
    data = _get(f"{RXNORM_BASE}/approximateTerm.json?term={_q(term)}&maxEntries={max_entries}")
    try:
        return data["approximateGroup"]["candidate"] or []
    except (KeyError, TypeError):
        return []


@lru_cache(maxsize=1024)
def get_rxnorm_name(rxcui: str) -> Optional[str]:
    """
    getRxNormName — GET /rxcui/{rxcui}.json

    Returns the official RxNorm display name string or None.
    """
    data = _get(f"{RXNORM_BASE}/rxcui/{_q(rxcui)}.json")
    try:
        return data["idGroup"]["name"]
    except (KeyError, TypeError):
        return None


@lru_cache(maxsize=1024)
def get_rxconcept_properties(rxcui: str) -> dict:
    """
    getRxConceptProperties — GET /rxcui/{rxcui}/properties.json

    Returns dict: {rxcui, name, synonym, tty, language, suppress, umlscui}
    Empty dict on failure.
    """
    data = _get(f"{RXNORM_BASE}/rxcui/{_q(rxcui)}/properties.json")
    try:
        return data["properties"] or {}
    except (KeyError, TypeError):
        return {}


@lru_cache(maxsize=256)
def get_all_properties(rxcui: str, prop_categories: str = "ALL") -> list[dict]:
    """
    getAllProperties — GET /rxcui/{rxcui}/allProperties.json?prop=…

    prop_categories: 'ALL'  or comma-separated e.g. 'NAMES,CODES,ATTRIBUTES'
    Returns list of {propName, propValue, propCategory} dicts.
    """
    data = _get(f"{RXNORM_BASE}/rxcui/{_q(rxcui)}/allProperties.json?prop={_q(prop_categories)}")
    try:
        return data["propConceptGroup"]["propConcept"] or []
    except (KeyError, TypeError):
        return []


def get_rx_property(rxcui: str, prop_name: str) -> Optional[str]:
    """
    getRxProperty — GET /rxcui/{rxcui}/property.json?propName=…

    Common propName values:
      'RxNorm Name'  'RxNorm Synonym'  'UMLSCUI'
      'RxNorm Dose Form'  'Prescribable Synonym'

    Returns the property value string or None.
    """
    data = _get(f"{RXNORM_BASE}/rxcui/{_q(rxcui)}/property.json?propName={_q(prop_name)}")
    try:
        return data["propConceptGroup"]["propConcept"][0]["propValue"]
    except (KeyError, IndexError, TypeError):
        return None


@lru_cache(maxsize=1)
def get_display_terms() -> list[str]:
    """
    getDisplayTerms — GET /displaynames.json

    All strings suitable for drug-name auto-completion.
    Cached once per session (list can be large).
    """
    data = _get(f"{RXNORM_BASE}/displaynames.json")
    try:
        return data["displayTermsList"]["term"] or []
    except (KeyError, TypeError):
        return []


def get_spelling_suggestions(name: str) -> list[str]:
    """
    getSpellingSuggestions — GET /spellingsuggestions.json?name=…

    Returns a list of suggestion strings for a misspelled drug name.
    """
    data = _get(f"{RXNORM_BASE}/spellingsuggestions.json?name={_q(name)}")
    try:
        return data["suggestionGroup"]["suggestionList"]["suggestion"] or []
    except (KeyError, TypeError):
        return []


# ═════════════════════════════════════════════════════════════════════════════
#  RELATED CONCEPTS
# ═════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=512)
def get_all_related_info(rxcui: str) -> dict:
    """
    getAllRelatedInfo — GET /rxcui/{rxcui}/allrelated.json

    Returns a dict keyed by TTY (term type), each value a list of concept dicts.
    e.g. {"SCD": [...], "SBD": [...], "IN": [...]}
    """
    data = _get(f"{RXNORM_BASE}/rxcui/{_q(rxcui)}/allrelated.json")
    try:
        groups  = data["allRelatedGroup"]["conceptGroup"] or []
        result: dict[str, list] = {}
        for g in groups:
            tty      = g.get("tty", "UNKNOWN")
            concepts = g.get("conceptProperties", []) or []
            if concepts:
                result[tty] = concepts
        return result
    except (KeyError, TypeError):
        return {}


@lru_cache(maxsize=512)
def get_related_by_type(rxcui: str, tty: str) -> list[dict]:
    """
    getRelatedByType — GET /rxcui/{rxcui}/related.json?tty=…

    tty: term type(s). Single: 'SCD'. Multiple: 'SCD+SBD'.
    Common values: 'IN' ingredient  'BN' brand  'SCD' clinical drug
                   'SBD' branded drug  'PIN' precise ingredient
                   'MIN' multiple ingredient  'SCDC' clinical drug component

    Returns list of concept dicts: {rxcui, name, tty, synonym, …}
    """
    data = _get(f"{RXNORM_BASE}/rxcui/{_q(rxcui)}/related.json?tty={_q(tty)}")
    try:
        groups   = data["relatedGroup"]["conceptGroup"] or []
        concepts: list[dict] = []
        for g in groups:
            concepts.extend(g.get("conceptProperties", []) or [])
        return concepts
    except (KeyError, TypeError):
        return []


@lru_cache(maxsize=512)
def get_related_by_relationship(rxcui: str, rela: str) -> list[dict]:
    """
    getRelatedByRelationship — GET /rxcui/{rxcui}/related.json?rela=…

    rela examples:
      'has_ingredient'          'ingredient_of'
      'has_dose_form'           'tradename_of'
      'has_tradename'           'reformulation_of'
      'has_precise_ingredient'  'constitutes'
      'contains'                'isa'

    Returns list of related concept dicts.
    """
    data = _get(f"{RXNORM_BASE}/rxcui/{_q(rxcui)}/related.json?rela={_q(rela)}")
    try:
        groups   = data["relatedGroup"]["conceptGroup"] or []
        concepts: list[dict] = []
        for g in groups:
            concepts.extend(g.get("conceptProperties", []) or [])
        return concepts
    except (KeyError, TypeError):
        return []


def get_drugs(name: str) -> list[dict]:
    """
    getDrugs — GET /drugs.json?name=…

    Returns all drug products related to an ingredient name.
    Each dict: {rxcui, name, tty, synonym, language, suppress, umlscui}
    """
    data = _get(f"{RXNORM_BASE}/drugs.json?name={_q(name)}")
    try:
        groups  = data["drugGroup"]["conceptGroup"] or []
        results: list[dict] = []
        for g in groups:
            results.extend(g.get("conceptProperties", []) or [])
        return results
    except (KeyError, TypeError):
        return []


@lru_cache(maxsize=512)
def get_generic_product(rxcui: str) -> Optional[dict]:
    """
    getGenericProduct — GET /rxcui/{rxcui}/generic.json

    Returns the unbranded (generic) concept for a branded RxCUI, or None.
    """
    data = _get(f"{RXNORM_BASE}/rxcui/{_q(rxcui)}/generic.json")
    try:
        groups = data["drugGroup"]["conceptGroup"] or []
        for g in groups:
            props = g.get("conceptProperties", []) or []
            if props:
                return props[0]
        return None
    except (KeyError, TypeError):
        return None


def get_multi_ingred_brands(rxcui_list: list[str]) -> list[dict]:
    """
    getMultiIngredBrand — GET /brands.json?ingredientids=…

    Given a list of ingredient RxCUIs, returns brand products containing
    all of those ingredients (combination product lookup).
    """
    ids  = "+".join(_q(r) for r in rxcui_list)
    data = _get(f"{RXNORM_BASE}/brands.json?ingredientids={ids}")
    try:
        return data["brandGroup"]["conceptProperties"] or []
    except (KeyError, TypeError):
        return []


def filter_by_property(rxcui: str, prop_name: str, prop_values: list[str]) -> Optional[str]:
    """
    filterByProperty — GET /rxcui/{rxcui}/filterConcept.json?…

    Returns the RxCUI if the concept matches the property filter, else None.
    """
    vals = "+".join(_q(v) for v in prop_values)
    data = _get(f"{RXNORM_BASE}/rxcui/{_q(rxcui)}/filterConcept.json"
                f"?propName={_q(prop_name)}&propValues={vals}")
    try:
        return data["rxcui"]
    except (KeyError, TypeError):
        return None


def get_reformulation_concepts(rxcui: str) -> list[dict]:
    """
    getReformulationConcepts — GET /reformulationConcepts.json?rxcui=…

    Returns concepts related by 'reformulation_of'.
    """
    data = _get(f"{RXNORM_BASE}/reformulationConcepts.json?rxcui={_q(rxcui)}")
    try:
        return data["reformulationGroup"]["reformulationConcept"] or []
    except (KeyError, TypeError):
        return []


# ═════════════════════════════════════════════════════════════════════════════
#  NDC / PRODUCT FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=512)
def get_ndcs(rxcui: str) -> list[str]:
    """
    getNDCs — GET /rxcui/{rxcui}/ndcs.json

    Returns all current NDC codes associated with this RxCUI.
    """
    data = _get(f"{RXNORM_BASE}/rxcui/{_q(rxcui)}/ndcs.json")
    try:
        return data["ndcGroup"]["ndcList"]["ndc"] or []
    except (KeyError, TypeError):
        return []


def get_ndc_properties(ndc: str) -> dict:
    """
    getNDCProperties — GET /ndcproperties.json?id=…

    Returns NDC detail dict including: ndc, ndcStatus, rxcui, splSetIdItem,
    packageList, ndcItem, startDate, endDate.
    """
    data = _get(f"{RXNORM_BASE}/ndcproperties.json?id={_q(ndc)}")
    try:
        return data["ndcPropertyList"]["ndcProperty"][0] or {}
    except (KeyError, IndexError, TypeError):
        return {}


def get_ndc_status(ndc: str) -> dict:
    """
    getNDCStatus — GET /ndcstatus.json?ndc=…

    Returns: {ndcStatus: 'ACTIVE'|'OBSOLETE'|…, rxcui, ndcHistory: […]}
    """
    data = _get(f"{RXNORM_BASE}/ndcstatus.json?ndc={_q(ndc)}")
    try:
        return data["ndcStatus"] or {}
    except (KeyError, TypeError):
        return {}


@lru_cache(maxsize=256)
def get_all_historical_ndcs(rxcui: str) -> list[str]:
    """
    getAllHistoricalNDCs — GET /rxcui/{rxcui}/allhistoricalndcs.json

    Returns ALL NDCs ever associated with this concept (active + historical).
    """
    data = _get(f"{RXNORM_BASE}/rxcui/{_q(rxcui)}/allhistoricalndcs.json")
    try:
        return data["historicalNdcConcept"]["historicalNdcList"]["ndc"] or []
    except (KeyError, TypeError):
        return []


def find_related_ndcs(ndc: Optional[str] = None, rxcui: Optional[str] = None) -> list[str]:
    """
    findRelatedNDCs — GET /relatedndcs.json?…

    Find NDCs related by NDC product, RxNorm concept, or drug product.
    Provide one of: ndc or rxcui.
    """
    if ndc:
        url = f"{RXNORM_BASE}/relatedndcs.json?ndc={_q(ndc)}"
    elif rxcui:
        url = f"{RXNORM_BASE}/relatedndcs.json?rxcui={_q(rxcui)}"
    else:
        return []
    data = _get(url)
    try:
        return data["relatedNDCsGroup"]["relatedNDCsList"]["ndc"] or []
    except (KeyError, TypeError):
        return []


def find_active_products(rxcui: str) -> list[dict]:
    """
    findActiveProducts — GET /rxcui/{rxcui}/active.json

    Returns currently active product concepts for a possibly obsolete RxCUI.
    """
    data = _get(f"{RXNORM_BASE}/rxcui/{_q(rxcui)}/active.json")
    try:
        groups   = data["activeRelatedDrugs"]["conceptGroup"] or []
        concepts: list[dict] = []
        for g in groups:
            concepts.extend(g.get("conceptProperties", []) or [])
        return concepts
    except (KeyError, TypeError):
        return []


# ═════════════════════════════════════════════════════════════════════════════
#  HISTORY / STATUS
# ═════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=512)
def get_rxcui_history_status(rxcui: str) -> dict:
    """
    getRxcuiHistoryStatus — GET /rxcui/{rxcui}/historystatus.json

    Returns full history dict:
      {rxcuiStatus, rxcuiChanged, minConcept, umlscui, attributeList, …}
    """
    data = _get(f"{RXNORM_BASE}/rxcui/{_q(rxcui)}/historystatus.json")
    try:
        return data["rxcuiStatusHistory"] or {}
    except (KeyError, TypeError):
        return {}


def get_all_concepts_by_status(status: str = "Active") -> list[dict]:
    """
    getAllConceptsByStatus — GET /allstatus.json?status=…

    status: 'Active' | 'Obsolete' | 'Remapped' | 'NotCurrentlyActive'
    Returns list of {rxcui, name, tty} dicts.  Can be very large — use sparingly.
    """
    data = _get(f"{RXNORM_BASE}/allstatus.json?status={_q(status)}")
    try:
        return data["minConceptGroup"]["minConcept"] or []
    except (KeyError, TypeError):
        return []


def get_all_concepts_by_tty(tty: str) -> list[dict]:
    """
    getAllConceptsByTTY — GET /allconcepts.json?tty=…

    Returns all active concepts of the specified term type.
    tty examples: 'SCD' 'SBD' 'IN' 'BN' 'PIN' 'MIN' 'SCDF' 'SBDF'
    """
    data = _get(f"{RXNORM_BASE}/allconcepts.json?tty={_q(tty)}")
    try:
        return data["minConceptGroup"]["minConcept"] or []
    except (KeyError, TypeError):
        return []


def get_all_ndcs_by_status(ndc_status: str = "Active") -> list[str]:
    """
    getAllNDCsByStatus — GET /allNDCstatus.json?ndcstatus=…

    ndc_status: 'Active' | 'Obsolete' | 'Never Active' | 'Unknown'
    """
    data = _get(f"{RXNORM_BASE}/allNDCstatus.json?ndcstatus={_q(ndc_status)}")
    try:
        return data["allNDCsByStatus"]["ndcList"]["ndc"] or []
    except (KeyError, TypeError):
        return []


# ═════════════════════════════════════════════════════════════════════════════
#  METADATA
# ═════════════════════════════════════════════════════════════════════════════

def get_rxnorm_version() -> dict:
    """getRxNormVersion — GET /version.json  → {version, apiVersion}"""
    data = _get(f"{RXNORM_BASE}/version.json")
    try:
        return data["rxNormData"] or {}
    except (KeyError, TypeError):
        return {}


@lru_cache(maxsize=1)
def get_term_types() -> list[str]:
    """getTermTypes — GET /termtypes.json"""
    data = _get(f"{RXNORM_BASE}/termtypes.json")
    try:
        return data["termTypeList"]["termType"] or []
    except (KeyError, TypeError):
        return []


@lru_cache(maxsize=1)
def get_id_types() -> list[str]:
    """getIdTypes — GET /idtypes.json"""
    data = _get(f"{RXNORM_BASE}/idtypes.json")
    try:
        return data["idTypeList"]["idType"] or []
    except (KeyError, TypeError):
        return []


@lru_cache(maxsize=1)
def get_source_types() -> list[str]:
    """getSourceTypes — GET /sourcetypes.json"""
    data = _get(f"{RXNORM_BASE}/sourcetypes.json")
    try:
        return data["sourceTypeList"]["sourceName"] or []
    except (KeyError, TypeError):
        return []


@lru_cache(maxsize=1)
def get_prop_categories() -> list[str]:
    """getPropCategories — GET /propCategories.json"""
    data = _get(f"{RXNORM_BASE}/propCategories.json")
    try:
        return data["propCategoryList"]["propCategory"] or []
    except (KeyError, TypeError):
        return []


@lru_cache(maxsize=1)
def get_prop_names() -> list[str]:
    """getPropNames — GET /propnames.json"""
    data = _get(f"{RXNORM_BASE}/propnames.json")
    try:
        return data["propNameList"]["propName"] or []
    except (KeyError, TypeError):
        return []


@lru_cache(maxsize=1)
def get_rela_types() -> list[str]:
    """getRelaTypes — GET /relatypes.json"""
    data = _get(f"{RXNORM_BASE}/relatypes.json")
    try:
        return data["relaTypeList"]["relaType"] or []
    except (KeyError, TypeError):
        return []


def get_rela_paths(from_tty: str, to_tty: str) -> list[dict]:
    """
    getRelaPaths — GET /relapaths.json?fromType=…&toType=…

    Returns the relationship paths between two term types.
    """
    data = _get(f"{RXNORM_BASE}/relapaths.json?fromType={_q(from_tty)}&toType={_q(to_tty)}")
    try:
        return data["relaPath"] or []
    except (KeyError, TypeError):
        return []


# ═════════════════════════════════════════════════════════════════════════════
#  DRUG CLASS  (RxClass API)
# ═════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=512)
def get_drug_classes(
    rxcui: str,
    rela_sources: tuple[str, ...] = ("VA", "ATC1-4", "MESH"),
) -> list[dict]:
    """
    RxClass: drug class(es) for a RxCUI across multiple classification systems.

    rela_sources options:
      'VA'       — VA Drug Classification   (e.g. "Biguanides")
      'ATC1-4'   — WHO ATC levels 1–4      (e.g. "ANTIDIABETICS, ORAL")
      'MESH'     — MeSH tree               (e.g. "Hypoglycemic Agents")
      'FDASPL'   — FDA SPL drug classes
      'DAILYMED' — DailyMed pharmacologic class
      'EPC'      — FDA Established Pharmacologic Class
      'MMSLt'    — Multum MedSource drug classes

    Returns deduplicated list of dicts:
      {classId, className, classType, relaSource}
    """
    results: list[dict] = []
    for src in rela_sources:
        data = _get(f"{RXCLASS_BASE}/class/byRxcui.json?rxcui={_q(rxcui)}&relaSource={_q(src)}")
        try:
            infos = data["rxclassDrugInfoList"]["rxclassDrugInfo"] or []
            for item in infos:
                concept = item.get("rxclassMinConceptItem", {})
                results.append({
                    "classId"   : concept.get("classId",   ""),
                    "className" : concept.get("className", ""),
                    "classType" : concept.get("classType", ""),
                    "relaSource": src,
                })
        except (KeyError, TypeError):
            continue

    # Deduplicate by classId
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in results:
        if r["classId"] not in seen:
            seen.add(r["classId"])
            deduped.append(r)
    return deduped


# ═════════════════════════════════════════════════════════════════════════════
#  SMART LOOKUP  — raw text → RxCUI with three-step fallback
# ═════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1024)
def resolve_rxcui(raw_text: str) -> Optional[str]:
    """
    Resolve any raw drug string to a RxCUI using a three-step strategy:

      1. Direct name lookup   (findRxcuiByString on original text, search=2)
      2. Cleaned name lookup  (strip dose/route/freq, retry step 1)
      3. Approximate match    (getApproximateMatch, highest-score candidate)

    Returns RxCUI string or None if all strategies fail.
    """
    # Step 1 — direct text
    rxcui = find_rxcui_by_string(raw_text)
    if rxcui:
        return rxcui

    # Step 2 — cleaned name
    cleaned = clean_med_name(raw_text)
    if cleaned and cleaned.lower() != raw_text.lower():
        rxcui = find_rxcui_by_string(cleaned)
        if rxcui:
            return rxcui

    # Step 3 — approximate on cleaned (or original if clean produced nothing)
    term       = cleaned or raw_text
    candidates = get_approximate_match(term, max_entries=3)
    if candidates:
        return candidates[0].get("rxcui")

    return None


# ═════════════════════════════════════════════════════════════════════════════
#  HIGH-LEVEL ENRICHMENT  (used by nlp_extraction_agent)
# ═════════════════════════════════════════════════════════════════════════════

def enrich_single(raw_text: str) -> dict:
    """
    Fully enrich one raw medication string with all available RxNorm data.

    Returned dict keys:
      original      — raw input text
      clean_name    — cleaned drug name used for lookup
      rxcui         — RxNorm CUI  (empty string if not found)
      name          — official RxNorm name
      tty           — term type  (IN, SCD, SBD, PIN, MIN, …)
      synonym       — prescribable synonym
      drug_class    — primary VA drug class name  (human-readable)
      drug_classes  — all classes from VA + ATC + MeSH  [{classId, className, …}]
      ndcs          — up to 5 NDC codes associated with this concept
      generic_rxcui — generic product RxCUI (set only for branded drugs)
      found         — bool: was a RxCUI matched?
    """
    clean  = clean_med_name(raw_text)
    result: dict[str, Any] = {
        "original"     : raw_text,
        "clean_name"   : clean,
        "rxcui"        : "",
        "name"         : "",
        "tty"          : "",
        "synonym"      : "",
        "drug_class"   : "",
        "drug_classes" : [],
        "ndcs"         : [],
        "generic_rxcui": "",
        "found"        : False,
    }

    rxcui = resolve_rxcui(raw_text)
    if not rxcui:
        return result

    # Core concept properties
    props = get_rxconcept_properties(rxcui)
    result.update({
        "rxcui"  : rxcui,
        "name"   : props.get("name",    ""),
        "tty"    : props.get("tty",     ""),
        "synonym": props.get("synonym", ""),
        "found"  : True,
    })

    # Drug classes (VA primary + ATC + MeSH)
    classes = get_drug_classes(rxcui)
    result["drug_classes"] = classes
    va_classes = [c for c in classes if c["relaSource"] == "VA"]
    primary    = va_classes or classes
    result["drug_class"] = primary[0]["className"] if primary else ""

    # NDCs (first 5 — enough for billing reference)
    result["ndcs"] = get_ndcs(rxcui)[:5]

    # Generic product CUI (only for branded term types)
    if props.get("tty") in ("SBD", "BPCK", "BN"):
        generic = get_generic_product(rxcui)
        if generic:
            result["generic_rxcui"] = generic.get("rxcui", "")

    time.sleep(_RATE_GAP)
    return result


def enrich_medications(med_texts: list[str]) -> list[dict]:
    """
    Batch-enrich a list of raw medication strings from NER extraction.

    Calls enrich_single() for each item.  Fully rate-limited and fault-tolerant.
    Any item that fails gets a minimal safe dict (found=False) instead of raising.

    Args:
        med_texts: raw strings e.g. ["metformin 500mg BID", "IV ceftriaxone 1g"]

    Returns:
        list[dict] — one dict per input, same order, same keys as enrich_single().
    """
    results: list[dict] = []
    for raw in med_texts:
        try:
            results.append(enrich_single(raw))
        except Exception:
            results.append({
                "original"     : raw,
                "clean_name"   : clean_med_name(raw),
                "rxcui"        : "",
                "name"         : "",
                "tty"          : "",
                "synonym"      : "",
                "drug_class"   : "",
                "drug_classes" : [],
                "ndcs"         : [],
                "generic_rxcui": "",
                "found"        : False,
            })
    return results


# ═════════════════════════════════════════════════════════════════════════════
#  CONNECTIVITY CHECK
# ═════════════════════════════════════════════════════════════════════════════

def is_rxnorm_available() -> bool:
    """
    Quick connectivity check.
    Returns True if RxNav REST API responds, False if offline or unreachable.
    Used by the pipeline to skip enrichment gracefully when the network is down.
    """
    return bool(_get(f"{RXNORM_BASE}/version.json"))
