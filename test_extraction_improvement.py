#!/usr/bin/env python
"""
Quick test script to verify NLP extraction improvements
"""
import requests
import json
import time

API_URL = "http://localhost:5000/api/extract"

clinical_note = """
A 58-year-old male with a history of Type 2 Diabetes Mellitus and Hypertension 
presented with complaints of Shortness of Breath and fatigue. Laboratory findings 
showed elevated creatinine levels indicating Chronic Kidney Disease stage 3. 
ECG was performed and showed no acute ischemic changes. 
Blood cultures were obtained. Patient condition stabilized and was discharged 
with follow-up advice on diet and medications.
"""

payload = {
    "clinical_note": clinical_note,
}

print("Sending test clinical note to extraction pipeline...")
print("=" * 70)

try:
    response = requests.post(API_URL, json=payload, timeout=60)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        
        # Extract entities from result
        entities = result.get("entities", {})
        diagnoses = entities.get("diagnoses", [])
        procedures = entities.get("procedures", [])
        medications = entities.get("medications", [])
        
        print("\n✅ EXTRACTED ENTITIES:")
        print(f"\nDiagnoses ({len(diagnoses)}):")
        for d in diagnoses:
            conf = d.get("confidence", 0)
            print(f"  • {d.get('text', 'N/A'):40s} ({conf*100:.0f}%)")
        
        print(f"\nProcedures ({len(procedures)}):")
        for p in procedures:
            conf = p.get("confidence", 0)
            print(f"  • {p.get('text', 'N/A'):40s} ({conf*100:.0f}%)")
        
        print(f"\nMedications ({len(medications)}):")
        for m in medications:
            print(f"  • {m.get('text', 'N/A'):40s}")
        
        # Check for noise
        noise_words = ["elevated", "condition", "##", "laboratory findings", "performed"]
        noisy_items = []
        for p in procedures:
            text = p.get('text', '').lower()
            for nw in noise_words:
                if nw in text:
                    noisy_items.append(p.get('text'))
        
        if noisy_items:
            print(f"\n⚠️  NOISE DETECTED ({len(noisy_items)} items):")
            for item in noisy_items:
                print(f"  • {item}")
        else:
            print(f"\n✅ NO OBVIOUS NOISE DETECTED")
        
        # Show codes generated
        codes = result.get("codes", {})
        icd10 = codes.get("icd10_codes", [])
        cpt = codes.get("cpt_codes", [])
        hcpcs = codes.get("hcpcs_codes", [])
        
        print(f"\n✅ GENERATED CODES:")
        print(f"ICD-10 ({len(icd10)}): {', '.join([c.get('code') for c in icd10[:3]])} {'...' if len(icd10) > 3 else ''}")
        print(f"CPT ({len(cpt)}): {', '.join([c.get('code') for c in cpt[:3]])} {'...' if len(cpt) > 3 else ''}")
        print(f"HCPCS ({len(hcpcs)}): {', '.join([c.get('code') for c in hcpcs[:3]])} {'...' if len(hcpcs) > 3 else ''}")
        
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 70)
