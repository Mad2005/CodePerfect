export interface MedicalCode {
  code: string;
  description: string;
  type: 'ICD-10' | 'CPT' | 'HCPCS';
  confidence: number;
}

export interface Diagnosis {
  term: string;
  evidence: string;
}

export interface ValidationResult {
  rule: string;
  status: 'passed' | 'warning' | 'error';
  message: string;
}

export interface MedicalReport {
  id: string;
  title: string;
  timestamp: string;
  clinicalSummary: string;
  diagnoses: Diagnosis[];
  codes: MedicalCode[];
  validationResults: ValidationResult[];
  errors: string[];
  mode: 'Auto' | 'Assisted';
}

export interface HistoryItem {
  id: string;
  title: string;
  timestamp: string;
  mode: 'Auto' | 'Assisted';
  patientId: string;
}

export interface ProcessingStep {
  id: number;
  label: string;
  status: 'pending' | 'processing' | 'completed';
}
