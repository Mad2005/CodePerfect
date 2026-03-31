import pandas as pd
import os

file_path = r"D:\AI\medical_coding_ai_v18\medical_coding_ai\data\real\snomed.csv"

output_dir = r"D:\AI\medical_coding_ai_v18\medical_coding_ai\data\chunks\snomed"
os.makedirs(output_dir, exist_ok=True)

chunk_size = 50000

for i, chunk in enumerate(pd.read_csv(
        file_path,
        dtype=str,
        chunksize=chunk_size,
        encoding="utf-8",
        on_bad_lines="skip"
    )):

    print(f"Processing chunk {i+1}")

    # ✅ Keep required columns safely
    cols_needed = ['conceptId', 'term', 'typeId']
    existing_cols = [c for c in cols_needed if c in chunk.columns]
    chunk = chunk[existing_cols].copy()

    # ✅ Clean text
    if 'term' in chunk.columns:
        chunk['term'] = chunk['term'].str.replace(r'\s+', ' ', regex=True)

    # ✅ Remove duplicates
    chunk = chunk.drop_duplicates()

    # SAVE
    output_file = os.path.join(output_dir, f"snomed_chunk_{i+1}.csv")
    chunk.to_csv(output_file, index=False)

    print(f"Saved: {output_file}")

print("✅ SNOMED chunking completed!")