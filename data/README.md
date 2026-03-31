# Real Medical Coding Data Directory

Place your CSV/TXT files here before running the ingestion script.

## Expected file names and formats

### ICD-10-CM (diagnosis codes)
File: icd10_codes.csv
Columns (any order): code, description
Example:
  code,description
  E11.9,Type 2 diabetes mellitus without complications
  I10,Essential (primary) hypertension

### CPT (procedure codes)
File: cpt_codes.csv
Columns: code, description  (optional: category)
Example:
  code,description,category
  99213,Office visit established patient low complexity,E&M
  71046,Chest X-ray 2 views,Radiology

### HCPCS Level II
File: hcpcs_codes.csv
Columns: code, description  (optional: category)
Example:
  code,description,category
  J0696,Ceftriaxone sodium per 250mg,drug
  E0601,CPAP device,DME

### NCCI PTP Edits (procedure-to-procedure)
File: ncci_ptp.csv
Columns: column1_code, column2_code, modifier_indicator, effective_date, deletion_date
(Standard CMS NCCI format — download from CMS website)
Example:
  column1_code,column2_code,modifier_indicator,effective_date,deletion_date
  00100,01996,0,19960101,
  00100,0213T,0,20110101,

### MUE (Medically Unlikely Edits)
File: mue_limits.csv
Columns: code, mue_value, mue_adjudication_indicator
(Standard CMS MUE format)
Example:
  code,mue_value,mue_adjudication_indicator
  99213,1,3
  71046,1,3

### LCD (Local Coverage Determinations)
File: lcd_rules.csv
Columns: lcd_id, title, description  (optional: applicable_codes)
Example:
  lcd_id,title,description
  L33718,CPAP/BiPAP,Covered when AHI >= 15 or AHI >= 5 with documented symptoms

### NCD (National Coverage Determinations)
File: ncd_rules.csv
Columns: ncd_id, title, description
Example:
  ncd_id,title,description
  20.7,CABG,Covered for significant left main coronary stenosis

## Download sources
- ICD-10-CM: https://www.cms.gov/medicare/coding-billing/icd-10-codes
- CPT: AMA CPT book (licensed) or open access subsets
- HCPCS: https://www.cms.gov/medicare/coding/hcpcsreleasecodesets
- NCCI: https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-edits
- MUE: https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-edits/medicaid-ncci-edit-files
- LCD/NCD: https://www.cms.gov/medicare-coverage-database
