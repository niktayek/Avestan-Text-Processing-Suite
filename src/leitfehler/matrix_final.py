import os
import pandas as pd
from glob import glob

# === CONFIG ===
ALIGNMENT_DIR = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/Token_compare"
OUTPUT_MATRIX = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/yasna_addition_omission_matrix.csv"

# === Collect All Alignment Files ===
alignment_files = sorted(glob(os.path.join(ALIGNMENT_DIR, "*_token_comparison_dp.csv")))

# === Collect All Affected Tokens ===
token_records = set()  # (block_id, token)
data_per_manuscript = {}

for path in alignment_files:
    df = pd.read_csv(path)
    manuscript_id = os.path.basename(path).split("_")[0]
    affected = set()

    for _, row in df.iterrows():
        if row["status"] == "omission":
            token_records.add((row["block_id"], row["canonical_token"]))
            affected.add((row["block_id"], row["canonical_token"]))
        elif row["status"] == "addition":
            token_records.add((row["block_id"], row["variant_token"]))
            affected.add((row["block_id"], row["variant_token"]))

    data_per_manuscript[manuscript_id] = affected

# === Build Matrix ===
sorted_tokens = sorted(token_records)  # consistent row order
manuscripts = sorted(data_per_manuscript.keys())

matrix = []
for block_token in sorted_tokens:
    row = {
        "block_id": block_token[0],
        "token": block_token[1]
    }
    for mid in manuscripts:
        row[mid] = int(block_token in data_per_manuscript[mid])
    matrix.append(row)

df_matrix = pd.DataFrame(matrix)
df_matrix.to_csv(OUTPUT_MATRIX, index=False)
print(f" Matrix saved to: {OUTPUT_MATRIX}")
