# import pandas as pd
# import re
# import json
# import os

# # INPUT (your chunk folder)
# input_dir = r"D:\AI\medical_coding_ai_v18\medical_coding_ai\data\chunks\lcd"

# # OUTPUT
# output_file = r"D:\AI\medical_coding_ai_v18\medical_coding_ai\data\processed\lcd_structured.json"
# os.makedirs(os.path.dirname(output_file), exist_ok=True)


# # ── RULE EXTRACTION ─────────────────────────
# def extract_rules(text):
#     sentences = re.split(r'[.;]\s+', text)

#     rules = []
#     for s in sentences:
#         s = s.strip()

#         if any(word in s.lower() for word in [
#             "must", "should", "necessary", "required",
#             "not considered", "considered medically"
#         ]):
#             if len(s) > 40:
#                 rules.append(s)

#     return list(set(rules))[:15]


# # ── SECTION EXTRACTION (NEW 🔥) ─────────────
# def extract_sections(text):
#     sections = {}

#     matches = re.split(r'(Section [IVX]+:)', text)

#     for i in range(1, len(matches), 2):
#         title = matches[i].strip()
#         content = matches[i+1].strip() if i+1 < len(matches) else ""
#         sections[title] = content[:500]  # limit size

#     return sections


# # ── ICD EXTRACTION ─────────────────────────
# def extract_icd(text):
#     return list(set(re.findall(r'\b[A-Z][0-9]{2}(?:\.[0-9A-Z]{1,4})?\b', text)))


# # ── MAIN PROCESS ───────────────────────────
# final_data = []

# for file in os.listdir(input_dir):
#     if not file.endswith(".csv"):
#         continue

#     path = os.path.join(input_dir, file)
#     print(f"Processing {file}")

#     df = pd.read_csv(path, dtype=str, encoding="utf-8", on_bad_lines="skip")

#     for _, row in df.iterrows():
#         lcd_id = row.get("lcd_id", "")
#         text = row.get("text", "")

#         if len(text) < 50:
#             continue

#         structured = {
#             "lcd_id": lcd_id,
#             "rules": extract_rules(text),
#             "sections": extract_sections(text),
#             "icd_codes": extract_icd(text)
#         }

#         final_data.append(structured)


# # SAVE
# with open(output_file, "w", encoding="utf-8") as f:
#     json.dump(final_data, f, indent=2)

# print("✅ Structured LCD created!")

import json
import pandas as pd

input_file = r"D:\AI\\medical_coding_ai_v18\\medical_coding_ai\data\\real\\lcd.json"
output_file = r"D:\AI\\medical_coding_ai_v18\\medical_coding_ai\data\\real\\lcd_rules.csv"

with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

df = pd.DataFrame(data)

# 🔥 IMPORTANT: rename columns to match ingestion
df = df.rename(columns={
    "cd_id": "lcd_id",
    "text": "description"
})

df.to_csv(output_file, index=False)

print("✅ JSON converted to CSV")