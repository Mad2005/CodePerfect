"""
Shared Pydantic models and LangGraph state for the Medical Coding AI pipeline.
"""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


# ─── Clinical Entity Models ───────────────────────────────────────────────────

class Diagnosis(BaseModel):
    text: str
    snomed_code: Optional[str] = None
    snomed_description: Optional[str] = None
    confidence: float = 0.0

class Procedure(BaseModel):
    text: str
    snomed_code: Optional[str] = None
    confidence: float = 0.0

class Medication(BaseModel):
    text: str
    normalized_name: Optional[str] = None
    rxnorm_rxcui: Optional[str] = None
    rxnorm_name: Optional[str] = None
    rxnorm_class: Optional[str] = None

class ClinicalEntities(BaseModel):
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    procedures: list[Procedure] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    other_entities: list[str] = Field(default_factory=list)


# ─── Per-Agent Code Set ───────────────────────────────────────────────────────

class CodeEntry(BaseModel):
    """A single code assigned by either coding agent."""
    code: str
    description: str
    code_type: str            # "ICD-10" | "CPT" | "HCPCS"
    units: int = 1
    confidence: float = 0.0
    rationale: str = ""
    sequence_type: str = ""   # "principal" | "secondary" | "additional" (ICD-10 only)
    category: str = ""        # drug | DME | supply (HCPCS only)

class AgentCodeSet(BaseModel):
    """Full set of codes proposed by one coding agent."""
    agent_name: str
    icd10_codes: list[CodeEntry] = Field(default_factory=list)
    cpt_codes: list[CodeEntry]   = Field(default_factory=list)
    hcpcs_codes: list[CodeEntry] = Field(default_factory=list)
    missed_services: list[str]   = Field(default_factory=list)
    agent_notes: str = ""


# ─── Debate / Resolution Models ───────────────────────────────────────────────

class DebatePoint(BaseModel):
    """One code-level conflict between Clinical and Revenue agents."""
    code: str
    code_type: str
    clinical_position: str      # what clinical agent said
    revenue_position: str       # what revenue agent said
    conflict_type: str          # "different_code" | "different_level" | "one_sided" | "units_differ"
    resolution: str             # final verdict
    winning_agent: str          # "clinical" | "revenue" | "both" | "neither"
    final_code: str
    final_description: str
    final_units: int = 1
    final_confidence: float = 0.0
    reasoning: str              # why this resolution was chosen

class DebateResult(BaseModel):
    """Full output from the Debate Agent."""
    debate_points: list[DebatePoint] = Field(default_factory=list)
    final_icd10_codes: list[dict[str, Any]] = Field(default_factory=list)
    final_cpt_codes: list[dict[str, Any]]   = Field(default_factory=list)
    final_hcpcs_codes: list[dict[str, Any]] = Field(default_factory=list)
    clinical_wins: int = 0
    revenue_wins: int = 0
    consensus_codes: int = 0
    debate_summary: str = ""


# ─── Human Code Input Models ──────────────────────────────────────────────────

class HumanCode(BaseModel):
    code: str
    description: str = ""
    code_type: str = ""
    units: int = 1

class HumanCodeInput(BaseModel):
    icd10_codes: list[HumanCode] = Field(default_factory=list)
    cpt_codes: list[HumanCode]   = Field(default_factory=list)
    hcpcs_codes: list[HumanCode] = Field(default_factory=list)
    coder_name: str = "Human Coder"
    notes: str = ""


# ─── AI vs Human Comparison Models ───────────────────────────────────────────

class CodeMatch(BaseModel):
    code: str
    code_type: str
    description: str
    ai_confidence: float = 0.0

class CodeDiscrepancy(BaseModel):
    code: str
    code_type: str
    discrepancy_type: str       # "ai_only" | "human_only" | "units_mismatch"
    ai_code: Optional[str] = None
    ai_description: str = ""
    human_code: Optional[str] = None
    human_description: str = ""
    ai_units: int = 1
    human_units: int = 1
    severity: str = "medium"
    clinical_impact: str = ""

class ComparisonSummary(BaseModel):
    total_ai_codes: int = 0
    total_human_codes: int = 0
    exact_matches: int = 0
    ai_only_codes: int = 0
    human_only_codes: int = 0
    discrepancies: int = 0
    icd10_match_rate: float = 0.0
    cpt_match_rate: float = 0.0
    hcpcs_match_rate: float = 0.0
    overall_match_rate: float = 0.0
    ai_accuracy_vs_human: float = 0.0
    human_accuracy_vs_ai: float = 0.0

class ComparisonResult(BaseModel):
    matched_codes: list[CodeMatch] = Field(default_factory=list)
    discrepancies: list[CodeDiscrepancy] = Field(default_factory=list)
    summary: ComparisonSummary = Field(default_factory=ComparisonSummary)
    has_human_input: bool = False


# ─── Compliance Models ────────────────────────────────────────────────────────

class NCCIEdit(BaseModel):
    column1_code: str
    column2_code: str
    modifier_allowed: bool
    description: str

class MUELimit(BaseModel):
    cpt_code: str
    max_units: int
    billed_units: int
    violation: bool
    reason: str

class LCDRule(BaseModel):
    rule_id: str
    description: str
    covered: bool
    applicable_codes: list[str] = Field(default_factory=list)

class NCDRule(BaseModel):
    rule_id: str
    description: str
    covered: bool
    applicable_codes: list[str] = Field(default_factory=list)

class ComplianceResult(BaseModel):
    ncci_violations: list[NCCIEdit] = Field(default_factory=list)
    mue_violations: list[MUELimit]  = Field(default_factory=list)
    lcd_issues: list[LCDRule]       = Field(default_factory=list)
    ncd_issues: list[NCDRule]       = Field(default_factory=list)
    missed_codes: list[str]         = Field(default_factory=list)
    is_compliant: bool = True
    summary: str = ""  # Human-readable compliance summary


# ─── Audit & Scoring Models ───────────────────────────────────────────────────

class AuditFinding(BaseModel):
    finding_type: str
    code: str
    description: str
    severity: str
    recommendation: str

class CodeJustification(BaseModel):
    code: str
    code_type: str
    clinical_evidence: str
    guideline_reference: str
    explanation: str
    human_code: Optional[str] = None
    comparison_verdict: str = "no_comparison"
    comparison_reasoning: str = ""

class ConfidenceScore(BaseModel):
    overall_coding_confidence: float
    icd10_confidence: float
    cpt_confidence: float
    hcpcs_confidence: float
    compliance_risk_score: float
    risk_level: str
    comparison_confidence: float = 0.0
    human_agreement_rate: float = 0.0
    comparison_available: bool = False
    # Debate metrics
    clinical_vs_revenue_agreement: float = 0.0
    debate_resolution_rate: float = 0.0


# ─── Final Report ─────────────────────────────────────────────────────────────

class FinalCodingReport(BaseModel):
    patient_note_excerpt: str
    # Per-agent code sets
    clinical_agent_codes: Optional[AgentCodeSet] = None
    revenue_agent_codes: Optional[AgentCodeSet]  = None
    # Debate resolution
    debate_result: Optional[DebateResult] = None
    # Final agreed codes (post-debate)
    icd10_codes: list[dict[str, Any]] = Field(default_factory=list)
    cpt_codes: list[dict[str, Any]]   = Field(default_factory=list)
    hcpcs_codes: list[dict[str, Any]] = Field(default_factory=list)
    # Human comparison
    human_code_input: Optional[HumanCodeInput] = None
    comparison_result: Optional[ComparisonResult] = None
    # Quality layers
    compliance_result: Optional[ComplianceResult] = None
    audit_findings: list[AuditFinding]       = Field(default_factory=list)
    justifications: list[CodeJustification]  = Field(default_factory=list)
    confidence_scores: Optional[ConfidenceScore] = None
    audit_summary: str = ""
    recommendations: list[str] = Field(default_factory=list)


# ─── LangGraph Pipeline State ─────────────────────────────────────────────────

class PipelineState(BaseModel):
    """Mutable state flowing through every LangGraph node."""
    raw_clinical_text: str = ""
    human_code_input: Optional[HumanCodeInput] = None
    cleaned_text: str = ""
    clinical_entities: Optional[ClinicalEntities] = None
    mapped_entities: Optional[ClinicalEntities]   = None

    # Per-agent knowledge (split by knowledge_retrieval_agent)
    clinical_guidelines: list[str] = Field(default_factory=list)   # ICD-10 + SNOMED
    revenue_guidelines: list[str]  = Field(default_factory=list)   # CPT + HCPCS + billing
    retrieved_rules: list[str]     = Field(default_factory=list)   # compliance rules
    retrieved_guidelines: list[str] = Field(default_factory=list)  # shared (for justification)

    # Per-agent code outputs
    clinical_agent_output: Optional[AgentCodeSet] = None
    revenue_agent_output: Optional[AgentCodeSet]  = None

    # Post-debate final codes (fed into all downstream agents)
    debate_result: Optional[DebateResult] = None
    accuracy_codes: dict[str, Any] = Field(default_factory=dict)   # final ICD-10
    revenue_codes: dict[str, Any]  = Field(default_factory=dict)   # final CPT+HCPCS

    # Comparison, compliance, audit
    comparison_result: Optional[ComparisonResult] = None
    compliance_result: Optional[ComplianceResult] = None
    audit_findings: list[AuditFinding]      = Field(default_factory=list)
    justifications: list[CodeJustification] = Field(default_factory=list)
    confidence_scores: Optional[ConfidenceScore] = None
    final_report: Optional[FinalCodingReport] = None
    errors: list[str] = Field(default_factory=list)
