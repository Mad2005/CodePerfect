"""
Sample clinical notes for testing the Medical Coding AI pipeline.
"""

SAMPLE_NOTE_1_DIABETES_HYPERTENSION = """
DISCHARGE SUMMARY

Patient: John Doe | DOB: 1958-03-15 | MRN: 123456
Admission Date: 2024-01-10 | Discharge Date: 2024-01-14
Attending Physician: Dr. Sarah Johnson, MD

PRINCIPAL DIAGNOSIS:
Type 2 Diabetes Mellitus with diabetic nephropathy, stage 3 chronic kidney disease.

SECONDARY DIAGNOSES:
1. Essential Hypertension, poorly controlled
2. Hyperlipidaemia
3. Obstructive Sleep Apnoea – on home CPAP therapy
4. Obesity, BMI 34.2

HISTORY OF PRESENT ILLNESS:
62-year-old male with long-standing Hx of DM Type 2 (diagnosed 2008), HTN, and CKD stage 3 
presented to ED with 3-day Hx of worsening pedal oedema, fatigue, and increased urinary frequency. 
HbA1c on admission 9.8% indicating poor glycaemic control. Serum creatinine 2.1 mg/dL (baseline 1.8).
BUN 38 mg/dL. eGFR 28 mL/min/1.73m2.

PHYSICAL EXAMINATION:
BP 168/94 mmHg, HR 88 bpm, RR 16, Temp 98.6°F, SpO2 96% on room air.
2+ pitting oedema bilateral lower extremities.
No acute distress.

DIAGNOSTIC WORKUP:
- CBC: WBC 8.2, Hgb 11.4, Plt 210 (mild anaemia noted)
- CMP: Sodium 138, Potassium 4.8, HCO3 21 (mild metabolic acidosis)
- HbA1c: 9.8%
- Urinalysis: 3+ protein, no nitrites, no leucocyte esterase
- Renal ultrasound: Bilateral small kidneys consistent with CKD
- ECG: Normal sinus rhythm, no acute changes
- Chest X-ray 2 views: Mild pulmonary vascular congestion, no consolidation

MEDICATIONS ON ADMISSION:
1. Metformin 1000 mg BID (held given CKD)
2. Lisinopril 10 mg daily
3. Amlodipine 5 mg daily
4. Atorvastatin 40 mg QHS
5. Insulin glargine 20 units subcutaneous at bedtime

HOSPITAL COURSE:
Patient was admitted for management of uncontrolled diabetes with nephropathy flare.
Metformin was held given eGFR < 30. Insulin regimen was adjusted: Glargine increased to 30 units 
at bedtime plus sliding scale regular insulin. Blood glucose logs showed improved fasting glucose 
110-140 range by discharge. 
Lisinopril dose increased to 20 mg daily for renoprotection and blood pressure control.
Amlodipine continued. BP improved to 140/82 at discharge.
Patient educated on diabetic diet, fluid restriction, and importance of medication compliance.
CPAP compliance reviewed – patient reports using CPAP nightly with good adherence.
Nephrology consulted – will follow outpatient for CKD management.

PROCEDURES PERFORMED:
1. Routine venipuncture for lab draws (x3 over hospital stay)
2. 12-lead ECG performed
3. Chest X-ray 2 views
4. Renal ultrasound
5. Subsequent hospital care (daily physician visits x4 days)

DISCHARGE PLAN:
- Follow up with primary care in 1 week
- Nephrology follow-up in 2 weeks
- Endocrinology referral placed
- Continue Lisinopril 20 mg, Amlodipine 5 mg, Atorvastatin 40 mg, Insulin glargine 30 units QHS
- Blood glucose monitoring twice daily
- Low-sodium, diabetic diet
- Fluid restriction 1.5L daily

Electronically signed: Dr. Sarah Johnson, MD
Date: 2024-01-14
"""

SAMPLE_NOTE_2_APPENDECTOMY = """
OPERATIVE AND DISCHARGE NOTE

Patient: Jane Smith | DOB: 1995-07-22 | MRN: 789012
Admission Date: 2024-02-05 | Discharge Date: 2024-02-07
Surgeon: Dr. Michael Chen, MD, FACS

PRINCIPAL DIAGNOSIS:
Acute appendicitis without abscess or perforation.

SECONDARY DIAGNOSIS:
Nausea and vomiting (resolved post-operatively)

HISTORY OF PRESENT ILLNESS:
28-year-old female presented to Emergency Department with 18-hour Hx of right lower quadrant (RLQ) 
abdominal pain, nausea, vomiting, and low-grade fever (38.1°C). Pain started periumbilically 
and migrated to RLQ. No prior episodes. Last bowel movement normal.

PHYSICAL EXAM:
Temp 38.2°C, BP 118/72, HR 96 (tachycardia), RR 14, SpO2 99%.
McBurney's point tenderness +++. Rebound tenderness positive. Rovsing sign positive.
Psoas sign positive.

DIAGNOSTIC WORKUP:
- CBC: WBC 14,800 with left shift (neutrophilia), Hgb 13.2
- CRP: 48 mg/L (elevated)
- Urinalysis: Normal, pregnancy test negative
- CT abdomen/pelvis with contrast: Dilated appendix 9mm, periappendiceal fat stranding. 
  No perforation, no abscess, no free air.

OPERATIVE REPORT:
Procedure: Laparoscopic appendectomy
Anaesthesia: General endotracheal
The patient was taken to the operating room. Three trocars placed. Appendix identified – 
markedly inflamed, oedematous, without perforation or gangrenous changes. 
Mesoappendix divided using LigaSure. Appendix base stapled and divided. 
Specimen sent to pathology. Irrigated. No active bleeding. Fascial closure of trocar sites. 
Skin closed with absorbable sutures. Estimated blood loss: < 20 mL. Duration: 42 minutes.

PATHOLOGY:
Acute appendicitis confirmed. No carcinoid or malignancy identified.

POST-OPERATIVE COURSE:
Uneventful. Patient tolerating clear liquids POD1, advanced to regular diet POD2.
Pain controlled with oral acetaminophen and ibuprofen. Ambulating independently.
No fever post-operatively. Wound sites clean and dry.

IV MEDICATIONS DURING ADMISSION:
- Cefazolin 2g IV pre-operatively (prophylactic)
- Morphine 2mg IV PRN (x2 doses post-op)
- Ondansetron 4mg IV PRN (x1 dose)
- IV Normal Saline maintenance overnight

DISCHARGE MEDICATIONS:
1. Acetaminophen 650 mg every 6 hours PRN pain
2. Ibuprofen 400 mg every 8 hours PRN pain with food
3. No antibiotics required (uncomplicated appendicitis)

Electronically signed: Dr. Michael Chen, MD
Date: 2024-02-07
"""

SAMPLE_NOTE_3_CARDIAC = """
CARDIOLOGY CONSULTATION NOTE

Patient: Robert Williams | DOB: 1952-11-08 | MRN: 345678
Date of Consultation: 2024-03-12
Requesting Service: Internal Medicine
Consulting Cardiologist: Dr. Lisa Park, MD, FACC

REASON FOR CONSULTATION:
Chest pain evaluation, rule out acute coronary syndrome.

DIAGNOSES:
1. Acute ST-elevation myocardial infarction (STEMI) – inferolateral
2. Coronary artery disease – three-vessel disease
3. Hypertension
4. Type 2 Diabetes Mellitus
5. Hyperlipidaemia
6. Current tobacco smoker (1 PPD x 30 years)

HISTORY:
71-year-old male with Hx of HTN, DM type 2, hyperlipidaemia and heavy tobacco use 
presented with acute onset crushing substernal chest pain radiating to left arm and jaw, 
associated with diaphoresis and SOB for 2 hours prior to arrival.

ECG on arrival: ST elevations in leads II, III, aVF, V5-V6. Reciprocal changes in aVL.
First troponin I: 2.4 ng/mL (elevated; normal < 0.04).
Second troponin I (3 hours later): 18.6 ng/mL (significantly elevated).

PROCEDURE:
Emergency cardiac catheterisation performed via right radial approach.
Findings: 95% stenosis of right coronary artery (RCA) – culprit lesion. 
70% stenosis of left anterior descending (LAD). 60% stenosis of circumflex (LCx).
Decision made for emergent PCI to RCA with drug-eluting stent placement.
TIMI-3 flow restored post-PCI. No complications.

Given three-vessel disease, cardiac surgery consulted for CABG planning.
Patient agreed to CABG. Scheduled for coronary artery bypass graft surgery.

MEDICATIONS:
- Aspirin 325 mg load then 81 mg daily
- Ticagrelor 180 mg load then 90 mg BID
- Atorvastatin 80 mg QHS
- Metoprolol succinate 25 mg daily
- Lisinopril 5 mg daily
- Heparin infusion – completed

LABS:
Peak troponin I: 48.2 ng/mL
BNP: 620 pg/mL (elevated, suggests LV dysfunction)
Echo: EF 40% (moderately reduced), inferior wall hypokinesis.

Electronically signed: Dr. Lisa Park, MD
Date: 2024-03-12
"""


# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE NOTE 4 — Simple Pneumonia Discharge  (designed for learning)
#
# Purpose: minimal, unambiguous note with exactly 3 expected codes so every
#          part of the output (ICD-10, CPT, HCPCS, debate, comparison) is
#          easy to understand without domain expertise.
#
# Expected codes (what a correct coder should produce):
#   ICD-10  J18.9   – Pneumonia, unspecified organism  (principal)
#   CPT     99221   – Initial hospital care, low complexity  (clinical agent)
#           99223   – Initial hospital care, high complexity (revenue agent will challenge)
#   HCPCS   J0690   – Ceftriaxone 750mg injection
#
# Built-in conflict: Clinical agent codes 99221, Revenue agent challenges to 99223
# → Debate Agent must resolve which E&M level the documentation supports.
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_NOTE_4_SIMPLE_PNEUMONIA = """
DISCHARGE SUMMARY

Patient  : Mary Johnson  |  DOB: 1945-06-12  |  MRN: 000001
Admission: 2024-05-01    |  Discharge: 2024-05-04
Attending: Dr. Alan Park, MD

─────────────────────────────
PRINCIPAL DIAGNOSIS
─────────────────────────────
Community-acquired pneumonia (right lower lobe).

─────────────────────────────
HISTORY OF PRESENT ILLNESS
─────────────────────────────
79-year-old female with no significant past medical history presented with
3-day history of productive cough with yellow sputum, fever up to 38.9°C,
and shortness of breath on exertion. No chest pain. No recent travel or sick contacts.

─────────────────────────────
PHYSICAL EXAMINATION
─────────────────────────────
Vitals: Temp 38.7°C, BP 138/82 mmHg, HR 102 bpm (tachycardia), RR 22, SpO2 92% on room air.
General: Elderly female in mild respiratory distress.
Chest: Decreased breath sounds and dullness to percussion at right lower lobe.
       Crackles present at right base.

─────────────────────────────
DIAGNOSTICS
─────────────────────────────
Chest X-ray (2 views): Right lower lobe infiltrate consistent with pneumonia. No effusion.
CBC: WBC 14,200 (leukocytosis), Hgb 12.1, Plt 280.
BMP: Within normal limits. Creatinine 0.9.
Blood cultures x2: No growth at 48 hours.
Sputum culture: Pending at discharge.

─────────────────────────────
TREATMENT
─────────────────────────────
Admitted for IV antibiotic therapy and supportive care.
Ceftriaxone 1g IV once daily administered for 3 days (total 3 doses).
Supplemental oxygen via nasal cannula 2L/min — SpO2 improved to 97%.
Adequate oral hydration. Encouraged ambulation from Day 2.
Fever resolved by Day 2. Patient tolerating oral intake well by Day 3.

─────────────────────────────
HOSPITAL COURSE
─────────────────────────────
Day 1: Admitted. IV ceftriaxone started. Oxygen supplementation.
       Physician reviewed all labs, imaging, and clinical findings.
       Multiple data points reviewed — leukocytosis, hypoxia, tachycardia, infiltrate.
       Medical decision making: Moderate complexity (new problem requiring workup,
       review of chest X-ray, CBC, BMP, blood cultures; prescription drug management).
Day 2: Fever resolved. SpO2 97% on 2L O2. WBC trending down.
Day 3: Afebrile x 24 hours. SpO2 96% on room air. Ready for discharge.

─────────────────────────────
DISCHARGE MEDICATIONS
─────────────────────────────
1. Amoxicillin-clavulanate 875mg/125mg orally twice daily x 5 days (step-down from IV).

─────────────────────────────
DISCHARGE INSTRUCTIONS
─────────────────────────────
- Follow up with primary care physician in 7 days.
- Repeat chest X-ray in 6 weeks to confirm resolution.
- Return to ED if fever recurs, worsening shortness of breath, or SpO2 drops below 93%.

Electronically signed: Dr. Alan Park, MD
Date: 2024-05-04
"""
