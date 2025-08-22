import pandas as pd
from collections import defaultdict, Counter
from pathlib import Path

# === Configuration ===
INPUT_FILE = "/home/nikta/Desktop/OCR/data/CAB/Yasna/yasna matches - 0008_filled_changes_hybrid.csv"  # or "matches.tsv"
IS_TSV = INPUT_FILE.endswith(".tsv")
CHANGE_COL = "the change"
MANUSCRIPT_COL = "manuscript"
OUTPUT_CSV = "/home/nikta/Desktop/OCR/data/CAB/Yasna/yasna_matches-0008_calculated.csv"

# === Load data ===
sep = "\t" if IS_TSV else ","
df = pd.read_csv(INPUT_FILE, sep=sep)

if CHANGE_COL not in df.columns or MANUSCRIPT_COL not in df.columns:
    raise ValueError(f"Your file must contain both '{CHANGE_COL}' and '{MANUSCRIPT_COL}' columns.")

# === Group changes by manuscript ===
manuscript_changes = defaultdict(list)

for _, row in df.iterrows():
    ms = str(row[MANUSCRIPT_COL]).strip()
    changes = str(row[CHANGE_COL]) if pd.notna(row[CHANGE_COL]) else ""
    for ch in changes.split(","):
        ch = ch.strip()
        if ch:
            manuscript_changes[ms].append(ch)

# === Build change-by-manuscript count and percent table ===
all_changes = set()
for ch_list in manuscript_changes.values():
    all_changes.update(ch_list)

table = []
for ch in sorted(all_changes):
    row = {"Change": ch}
    for ms, changes in manuscript_changes.items():
        count = changes.count(ch)
        total = len(changes)
        pct = (count / total * 100) if total > 0 else 0
        row[f"{ms}_count"] = count
        row[f"{ms}_%"] = round(pct, 2)
    table.append(row)

# === Convert to DataFrame and export ===
result_df = pd.DataFrame(table)
result_df = result_df.set_index("Change")
result_df = result_df.sort_index()
result_df.to_csv(OUTPUT_CSV)

print(f"✅ Per-manuscript change distribution (with counts and percentages) saved to:\n{Path(OUTPUT_CSV).resolve()}")
