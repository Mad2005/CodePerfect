"""
Dual Coding Agents (v5 — vector-first, rule-compliant, hybrid entities)
────────────────────────────────────────────────────────────────────────
Clinical Accuracy Agent  : codes from documentation + rules perspective
Revenue Optimization Agent: validates and supplements legitimate revenue
Both are grounded in ICD-10-CM / CPT / HCPCS data from ChromaDB and
must respect NCCI, MUE, LCD, and NCD rules. LLM is a fallback only.
"""

from core.llm import call_gemini_json
from core.models import PipelineState, AgentCodeSet, CodeEntry


# ─── Shared filter ────────────────────────────────────────────────────────────


def _filter(codes: list[dict]) -> list[dict]:
    """
    Keep only confident, non-zero codes and deduplicate.
    This also helps enforce deterministic behavior.
    """
    if not codes:
        return []

    seen = set()
    out: list[dict] = []
    for c in codes:
        try:
            conf = float(c.get("confidence", 0.0))
        except (TypeError, ValueError):
            conf = 0.0

        # Only keep codes that the model itself is at least moderately sure about.
        if conf < 0.8:
            continue

        key = (c.get("code"), c.get("code_type"))
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


# ─── Clinical Accuracy Agent ──────────────────────────────────────────────────


CLINICAL_SYSTEM = (
    "You are a senior certified inpatient/outpatient coder (CCS, CPC, RHIA) with "
    "deep knowledge of ICD-10-CM, CPT, HCPCS, NCCI PTP edits, MUE limits, LCD/NCD "
    "coverage, and denial-prevention best practices. "
    "You are conservative and audit-defensible: you only assign codes that are "
    "explicitly supported by documentation AND allowed by the rules. "
    "You never hallucinate codes or upcode. If no compliant code is supported, "
    "you return an empty list for that code set. "
    "You always prefer codes from the retrieved reference data over codes from memory. "
    "Return ONLY valid JSON — no prose, no markdown, no comments."
)

CLINICAL_PROMPT = """
Assign ICD-10-CM, CPT, and HCPCS codes for this clinical encounter.

CLINICAL NOTE:
{note}

EXTRACTED ENTITIES (hybrid: LLM primary, BioBERT secondary):
Diagnoses  :
{diagnoses}
Procedures :
{procedures}
Medications:
{medications}

RETRIEVED REFERENCE DATA FROM CHROMADB:
ICD-10 candidates (JSON-like records):
{icd_data}

CPT candidates (JSON-like records):
{cpt_data}

HCPCS candidates (JSON-like records):
{hcpcs_data}

NCCI PTP edits:
{ncci_ptp}

MUE tables:
{mue}

LCD/NCD coverage policies:
{lcd_ncd}

CODING RULES:
1. VECTOR-FIRST:
   - When assigning codes, you MUST first look at the retrieved ICD-10/CPT/HCPCS
     candidates and select the best matching code(s) from there.
   - Only if there is NO relevant candidate for a clearly documented service may
     you use your internal knowledge to suggest a code.
   - If you propose a code that is not in the candidates list, you must still
     follow all NCCI/MUE/LCD/NCD rules.

2. DOCUMENTATION-ONLY:
   - Assign codes ONLY for diagnoses, procedures, and medications that are
     explicitly documented in the clinical note.
   - Do NOT code suspected, probable, rule-out, or implied diagnoses unless
     the setting and specific guideline require it and the note states it clearly.
   - Do NOT create Z-codes, screening codes, or complication codes unless the
     note clearly documents them.

3. NCCI / MUE / LCD / NCD COMPLIANCE:
   - NEVER output a CPT/HCPCS combination that violates an NCCI PTP edit.
     If two codes conflict, keep the more comprehensive or appropriate code
     and drop the bundled/denied one.
   - NEVER assign more units than allowed by the MUE for a code.
   - NEVER assign a CPT/HCPCS code that fails LCD/NCD coverage for the
     documented diagnosis.
   - If a candidate code violates any of these rules, you MUST NOT include it.

4. ICD-10-CM PRINCIPLES:
   - Assign ONE principal diagnosis: the condition established after study as
     the main reason for the encounter/admission.
   - Secondary diagnoses ONLY if they are documented AND were evaluated, treated,
     monitored, or otherwise impacted the care or length of stay.
   - Use the highest specificity supported by the note. Do NOT guess missing
     details like laterality, trimester, or stage.

5. CPT / HCPCS PRINCIPLES:
   - Procedures must be explicitly documented as performed.
   - Do NOT unbundle components that are already included in a more
     comprehensive CPT code.
   - HCPCS J-codes only for drugs administered during the encounter, not
     for discharge prescriptions.
   - DME/supplies only if documented as dispensed.

6. RISK / CONFIDENCE:
   - If you are not sure that a code is fully supported and compliant,
     set its confidence below 0.8 so that the application can drop it.
   - It is better to return fewer codes than to over-code.

CONFIDENCE SCALE:
- 1.0 — direct match: explicit documentation + matching candidate + rule-compliant.
- 0.8 — strong support: explicit documentation + generally correct candidate, minor ambiguity.
- <=0. 6— do NOT include (the application will filter these out).

RETURN STRICT JSON:
{{
  "agent_name": "Clinical Accuracy Agent",
  "icd10_codes": [
    {{
      "code": "ICD-10-CM code",
      "description": "official description (use retrieved text when available)",
      "code_type": "ICD-10",
      "sequence_type": "principal|secondary|additional",
      "units": 1,
      "confidence": 0.0-1.0,
      "rationale": "short quote from the note + mention of the rule or table that supports this code"
    }}
  ],
  "cpt_codes": [
    {{
      "code": "CPT code",
      "description": "official description (use retrieved text when available)",
      "code_type": "CPT",
      "units": 1,
      "confidence": 0.0-1.0,
      "rationale": "short quote from the note + mention of NCCI/MUE/LCD/NCD where relevant"
    }}
  ],
  "hcpcs_codes": [
    {{
      "code": "HCPCS code",
      "description": "drug / supply description",
      "code_type": "HCPCS",
      "category": "drug|DME|supply|vaccine",
      "units": 1,
      "confidence": 0.0-1.0,
      "rationale": "drug name, dose, route from note + any coverage rule used"
    }}
  ],
  "missed_services": [],
  "agent_notes": "brief explanation of principal dx choice, bundling decisions, and any codes intentionally omitted for compliance."
}}
"""


def clinical_accuracy_agent(state: PipelineState) -> PipelineState:
    try:
        entities = state.mapped_entities or state.clinical_entities
        if not entities:
            state.clinical_agent_output = AgentCodeSet(agent_name="Clinical Accuracy Agent")
            state.accuracy_codes = {"icd10_codes": [], "coding_notes": "No entities available."}
            return state

        diag_text = "\n".join(
            f"  - {d.text} (SNOMED: {d.snomed_code or 'N/A'})"
            for d in entities.diagnoses
        ) or "None extracted"
        proc_text = "\n".join(f"  - {p.text}" for p in entities.procedures) or "None extracted"
        med_text = "\n".join(f"  - {m.text}" for m in entities.medications) or "None extracted"

        # Vector-based reference chunks (already prepared by knowledge_retrieval_agent)
        icd_data = state.vector_icd if hasattr(state, "vector_icd") else state.clinical_guidelines
        cpt_data = state.vector_cpt if hasattr(state, "vector_cpt") else state.revenue_guidelines
        hcpcs_data = state.vector_hcpcs if hasattr(state, "vector_hcpcs") else []
        ncci_ptp = state.vector_ncci_ptp if hasattr(state, "vector_ncci_ptp") else state.retrieved_rules
        mue = state.vector_mue if hasattr(state, "vector_mue") else []
        lcd_ncd = state.vector_lcd_ncd if hasattr(state, "vector_lcd_ncd") else []

        data = call_gemini_json(
            CLINICAL_PROMPT.format(
                note=state.cleaned_text[:3000],
                diagnoses=diag_text,
                procedures=proc_text,
                medications=med_text,
                icd_data=icd_data or "[]",
                cpt_data=cpt_data or "[]",
                hcpcs_data=hcpcs_data or "[]",
                ncci_ptp=ncci_ptp or "[]",
                mue=mue or "[]",
                lcd_ncd=lcd_ncd or "[]",
            ),
            CLINICAL_SYSTEM,
        )

        icd = _filter(data.get("icd10_codes", []))
        cpt = _filter(data.get("cpt_codes", []))
        hcpc = _filter(data.get("hcpcs_codes", []))

        state.clinical_agent_output = AgentCodeSet(
          agent_name="Clinical Accuracy Agent",
          icd10_codes=[CodeEntry(**({**c, "code_type": c.get("code_type") or "ICD-10"})) for c in icd],
          cpt_codes=[CodeEntry(**({**c, "code_type": c.get("code_type") or "CPT"})) for c in cpt],
          hcpcs_codes=[CodeEntry(**({**c, "code_type": c.get("code_type") or "HCPCS"})) for c in hcpc],
          missed_services=data.get("missed_services", []),
          agent_notes=data.get("agent_notes", ""),
        )
        state.accuracy_codes = {
            "icd10_codes": icd,
            "coding_notes": data.get("agent_notes", ""),
        }

    except Exception as exc:
        state.errors.append(f"ClinicalAccuracyAgent error: {exc}")
        state.clinical_agent_output = AgentCodeSet(agent_name="Clinical Accuracy Agent")
        state.accuracy_codes = {"icd10_codes": [], "coding_notes": str(exc)}
    return state


# ─── Revenue Optimization Agent (Independent Coding Mode) ─────────────────────

REVENUE_SYSTEM = (
    "You are a Revenue Cycle Management (RCM) specialist and certified professional "
    "coder (CPC). Your goal is to maximize compliant reimbursement by identifying "
    "ALL legitimate billable diagnoses, procedures, and supplies documented in the note. "
    "You work independently — you do NOT rely on another agent's code set, but instead "
    "analyze the clinical note, extracted entities, and reference data directly. "
    "You must respect NCCI PTP edits, MUE limits, LCD/NCD policies, and official "
    "ICD-10-CM/CPT/HCPCS guidelines. You never upcode or invent undocumented services. "
    "Return ONLY valid JSON — no prose, no markdown, no comments."
)

REVENUE_PROMPT = """
INDEPENDENT REVENUE CODING
──────────────────────────
Review the clinical note and reference data directly. Build a COMPLETE, COMPLIANT,
REVENUE-OPTIMIZED code set that captures EVERY billable service supported by documentation.

CLINICAL NOTE:
{note}

EXTRACTED ENTITIES (hybrid LLM + BioBERT):
Diagnoses  :
{diagnoses}
Procedures :
{procedures}
Medications:
{medications}

REFERENCE DATA FROM CHROMADB:
ICD-10-CM candidates:
{icd_data}

CPT candidates:
{cpt_data}

HCPCS candidates:
{hcpcs_data}

NCCI PTP edits:
{ncci_ptp}

MUE limits:
{mue}

LCD/NCD policies:
{lcd_ncd}

CODING STRATEGY:
1. INDEPENDENT, REVENUE-FOCUSED VIEW
   - Do NOT assume any prior codes are correct or complete.
   - Start from the note and entities: ask “What services and conditions can be billed?”
   - Build your own ICD-10, CPT, and HCPCS lists to maximize compliant revenue.

2. CAPTURE ALL BILLABLE ITEMS
   - Diagnoses: principal + ALL secondary diagnoses that required evaluation, treatment,
     monitoring, or extended length of stay.
   - Procedures: ALL surgeries, tests, imaging, EKGs, therapies, bedside procedures.
   - E&M: appropriate visit level or inpatient code, discharge day, observation, etc.
   - HCPCS: ALL administered drugs (J-codes), DME, supplies, vaccines.
   - Companion services: e.g., separately billable diagnostic tests, infusions, injections
     that often get missed.

3. VECTOR-FIRST BUT NOT VECTOR-ONLY
   - Prefer codes from ICD/CPT/HCPCS candidate lists.
   - If a documented service has no obvious candidate, you MAY use your coding knowledge
     to suggest a standard code, but ONLY if fully supported by the note and rules.
   - If you cannot find any compliant code for a documented service, do NOT guess a code;
     instead, describe it in agent_notes as “uncoded documented service”.

4. COMPLIANCE HARD LIMITS
   - NCCI: Never output code pairs that violate NCCI PTP edits.
     • If two codes conflict, keep the more comprehensive/reimbursable one and drop the other.
   - MUE: Never exceed the daily MUE limit for any code.
   - LCD/NCD: Never assign a code the policies say is not covered for the documented diagnoses
     unless you clearly indicate that an ABN is required (mention this in agent_notes).
   - If a candidate code is not compliant, you MUST NOT include it.

5. CONFIDENCE POLICY (KEEP CODES ≥ 0.6)
   - 1.0: Explicit documentation + candidate match + fully compliant.
   - 0.8: Strong support + minor ambiguity, still clearly billable and compliant.
   - 0.6: Documented service, billable and compliant, but:
          • wording not identical to candidate, or
          • some judgment required.
   - 0.0–0.59: Too uncertain — you MUST NOT include these codes.

   You should assign confidence between 0.6 and 1.0 for codes you include. Do not
   output codes with confidence < 0.6.

6. RATIONALE
   - For EVERY code, provide:
     • A short direct quote or summary from the note that supports it, AND
     • Mention of any relevant rule (NCCI/MUE/LCD/NCD) if it influenced your decision.

STRICT JSON OUTPUT:
{{
  "agent_name": "Revenue Optimization Agent",
  "icd10_codes": [
    {{
      "code": "ICD-10-CM code",
      "description": "official ICD-10-CM description",
      "code_type": "ICD-10",
      "sequence_type": "principal|secondary|additional",
      "units": 1,
      "confidence": 0.6-1.0,
      "rationale": "short quote from note + (optionally) rule reference"
    }}
  ],
  "cpt_codes": [
    {{
      "code": "CPT code",
      "description": "official CPT description",
      "code_type": "CPT",
      "units": 1,
      "confidence": 0.6-1.0,
      "rationale": "short quote from note + reason this service is billable"
    }}
  ],
  "hcpcs_codes": [
    {{
      "code": "HCPCS code",
      "description": "drug / supply / DME description",
      "code_type": "HCPCS",
      "category": "drug|DME|supply|vaccine",
      "units": 1,
      "confidence": 0.6-1.0,
      "rationale": "drug name, dose, route from the note, or supply/DME documentation"
    }}
  ],
  "missed_services": [
    "brief description of any clearly documented but uncoded service (if you could not find a compliant code)"
  ],
  "agent_notes": "summary of revenue opportunities found, E&M level reasoning, and any services intentionally left uncoded due to compliance."
}}
"""


def _filter_revenue(codes: list[dict]) -> list[dict]:
    """
    Revenue-specific filter:
    - Keep codes with confidence >= 0.6.
    - Deduplicate by (code, code_type).
    """
    if not codes:
        return []
    seen = set()
    out: list[dict] = []
    for c in codes:
        try:
            conf = float(c.get("confidence", 0.0))
        except (TypeError, ValueError):
            conf = 0.0
        if conf < 0.6:
            continue
        key = (c.get("code"), c.get("code_type"))
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def revenue_optimization_agent(state: PipelineState) -> PipelineState:
    try:
        entities = state.mapped_entities or state.clinical_entities

        # Prepare entity summaries for the prompt
        if entities:
            diag_text = "\n".join(f"  - {d.text}" for d in entities.diagnoses) or "None extracted"
            proc_text = "\n".join(f"  - {p.text}" for p in entities.procedures) or "None extracted"
            med_text  = "\n".join(f"  - {m.text}" for m in entities.medications) or "None extracted"
        else:
            diag_text = "None extracted"
            proc_text = "None extracted"
            med_text  = "None extracted"

        # Reference data from retrieval layer
        icd_data   = getattr(state, "vector_icd", [])   or state.clinical_guidelines
        cpt_data   = getattr(state, "vector_cpt", [])   or state.revenue_guidelines
        hcpcs_data = getattr(state, "vector_hcpcs", []) or []
        ncci_ptp   = getattr(state, "vector_ncci_ptp", []) or state.retrieved_rules
        mue        = getattr(state, "vector_mue", [])       or []
        lcd_ncd    = getattr(state, "vector_lcd_ncd", [])   or []

        data = call_gemini_json(
            REVENUE_PROMPT.format(
                note=state.cleaned_text[:3000],
                diagnoses=diag_text,
                procedures=proc_text,
                medications=med_text,
                icd_data=icd_data or "[]",
                cpt_data=cpt_data or "[]",
                hcpcs_data=hcpcs_data or "[]",
                ncci_ptp=ncci_ptp or "[]",
                mue=mue or "[]",
                lcd_ncd=lcd_ncd or "[]",
            ),
            REVENUE_SYSTEM,
        )

        icd  = _filter_revenue(data.get("icd10_codes", []))
        cpt  = _filter_revenue(data.get("cpt_codes", []))
        hcpc = _filter_revenue(data.get("hcpcs_codes", []))

        state.revenue_agent_output = AgentCodeSet(
            agent_name="Revenue Optimization Agent",
            icd10_codes=[
                CodeEntry(**({**c, "code_type": c.get("code_type") or "ICD-10"}))
                for c in icd
            ],
            cpt_codes=[
                CodeEntry(**({**c, "code_type": c.get("code_type") or "CPT"}))
                for c in cpt
            ],
            hcpcs_codes=[
                CodeEntry(**({**c, "code_type": c.get("code_type") or "HCPCS"}))
                for c in hcpc
            ],
            missed_services=data.get("missed_services", []),
            agent_notes=data.get("agent_notes", ""),
        )

        state.revenue_codes = {
            "icd10_codes": icd,
            "cpt_codes": cpt,
            "hcpcs_codes": hcpc,
            "missed_billable_services": data.get("missed_services", []),
            "revenue_notes": data.get("agent_notes", ""),
        }

    except Exception as exc:
        state.errors.append(f"RevenueOptimizationAgent error: {exc}")
        state.revenue_agent_output = AgentCodeSet(agent_name="Revenue Optimization Agent")
        state.revenue_codes = {
            "icd10_codes": [],
            "cpt_codes": [],
            "hcpcs_codes": [],
            "missed_billable_services": [],
            "revenue_notes": str(exc),
        }
    return state
