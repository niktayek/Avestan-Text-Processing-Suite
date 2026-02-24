import pandas as pd

# === CONFIG ===
input_file = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/flexible_block_alignment.csv"
output_file = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/flexible_block_alignment_tagged.csv"

# === Load ===
df = pd.read_csv(input_file)

# === Classify Match Type ===
def classify(row):
    score = row["jaccard_overlap"]
    if pd.isna(score) or row["ocr_block_id"] is None or pd.isna(row["ocr_block_id"]):
        return "omission"
    elif score >= 0.90:
        return "match"
    elif score >= 0.50:
        return "weak_match"
    else:
        return "omission"

df["match_type"] = df.apply(classify, axis=1)

# === Save result ===
df.to_csv(output_file, index=False)
print(f" Tagged alignments saved to: {output_file}")
