import pandas as pd
from collections import defaultdict
from pathlib import Path
import re

# === Configuration ===
INPUT_FILE = "/home/nikta/Desktop/OCR/data/CAB/Yasna/yasna-matches-0008_calculated.csv"
IS_TSV = INPUT_FILE.endswith(".tsv")
CHANGE_COL = "the change"
MANUSCRIPT_COL = "manuscript"
OUTPUT_CSV = "/home/nikta/Desktop/OCR/data/CAB/Yasna/yasna_matches-0040_all_substitution_percentages.csv"

# === Load data ===
sep = "\t" if IS_TSV else ","
df = pd.read_csv(INPUT_FILE, sep=sep)

if CHANGE_COL not in df.columns or MANUSCRIPT_COL not in df.columns:
    raise ValueError(f"Your file must contain both '{CHANGE_COL}' and '{MANUSCRIPT_COL}' columns.")

# === Collect substitution statistics ===
# For each manuscript:
#   - store count of each "x for y"
#   - store total uses of "x for *"
substitution_counts = defaultdict(lambda: defaultdict(int))  # (manuscript -> "x for y" -> count)
source_totals = defaultdict(lambda: defaultdict(int))        # (manuscript -> x -> total x-for-*)

for _, row in df.iterrows():
    ms = str(row[MANUSCRIPT_COL]).strip()
    changes = str(row[CHANGE_COL]) if pd.notna(row[CHANGE_COL]) else ""
    for ch in changes.split(","):
        ch = ch.strip()
        match = re.match(r"(.+?)\s+for\s+(.+)", ch)
        if match:
            actual, expected = match.groups()
            substitution_counts[ms][f"{actual} for {expected}"] += 1
            source_totals[ms][actual] += 1

# === Build result table ===
rows = []
for ms in sorted(substitution_counts.keys()):
    for change, count in substitution_counts[ms].items():
        actual, expected = change.split(" for ")
        total = source_totals[ms][actual]
        pct = (count / total * 100) if total > 0 else 0
        rows.append({
            "manuscript": ms,
            "change": change,
            f'"{actual} for {expected}" count': count,
            f'"{actual} for *" total': total,
            "percentage": round(pct, 2)
        })

# === Save to CSV ===
result_df = pd.DataFrame(rows)
result_df = result_df.sort_values(by=["manuscript", "change"])
result_df.to_csv(OUTPUT_CSV, index=False)

print(f"✅ All 'x for y' substitution statistics saved to:\n{Path(OUTPUT_CSV).resolve()}")
