#!/usr/bin/env python
"""Direct pipeline test to verify extraction improvements"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from core.pipeline import run_pipeline
from core.vector_db import VectorKnowledgeBase
from rich.console import Console

console = Console()

clinical_note = """
A 58-year-old male with a history of Type 2 Diabetes Mellitus and Hypertension 
presented with complaints of Shortness of Breath and fatigue. Laboratory findings 
showed elevated creatinine levels indicating Chronic Kidney Disease stage 3. 
ECG was performed and showed no acute ischemic changes. 
Blood cultures were obtained. Patient condition stabilized and was discharged 
with follow-up advice on diet and medications.
"""

print("Testing NLP extraction improvements...")
print("=" * 70)

vdb = VectorKnowledgeBase()
state = run_pipeline(clinical_note, vdb, human_codes=None)

# Check entities
entities = state.clinical_entities
if entities:
    print(f"\n✅ EXTRACTED ENTITIES:")
    print(f"  Diagnoses:  {len(entities.diagnoses)}")
    for d in entities.diagnoses:
        print(f"    • {d.text:40s} ({d.confidence*100:.0f}%)")
    
    print(f"\n  Procedures: {len(entities.procedures)}")
    for p in entities.procedures:
        print(f"    • {p.text:40s} ({p.confidence*100:.0f}%)")
    
    print(f"\n  Medications: {len(entities.medications)}")
    for m in entities.medications:
        print(f"    • {m.text:40s}")
    
    # Check for noise
    noise_indicators = ["elevated", "condition", "##", "laboratory findings", "performed", "stage"]
    noisy_items = []
    for p in entities.procedures:
        text = p.text.lower()
        if any(ni in text for ni in noise_indicators):
            noisy_items.append(p.text)
    
    if noisy_items:
        print(f"\n⚠️  NOISE STILL PRESENT ({len(noisy_items)} items):")
        for item in noisy_items:
            print(f"  • {item}")
    else:
        print(f"\n✅ No obvious noise detected!")
else:
    print("❌ No entities extracted!")

print("\n" + "=" * 70)
