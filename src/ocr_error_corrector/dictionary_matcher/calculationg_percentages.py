import pandas as pd
from collections import defaultdict
from pathlib import Path
import re

# === Configuration ===
INPUT_FILE = "/home/nikta/Desktop/OCR/data/CAB/Yasna/yasna-matches-0008_calculated.csv"
IS_TSV = INPUT_FILE.endswith(".tsv")
CHANGE_COL = "the change"
MANUSCRIPT_COL = "manuscript"
SOURCE_LETTER = "a"  # the actual (possibly wrong) letter used in manuscripts
TARGET_LETTER = "i"  # the letter that should have been there
OUTPUT_CSV = "/home/nikta/Desktop/OCR/data/CAB/Yasna/yasna_matches-0008_a_instead_of_i.csv"

# === Load data ===
sep = "\t" if IS_TSV else ","
df = pd.read_csv(INPUT_FILE, sep=sep)

if CHANGE_COL not in df.columns or MANUSCRIPT_COL not in df.columns:
    raise ValueError(f"Your file must contain both '{CHANGE_COL}' and '{MANUSCRIPT_COL}' columns.")

# === Collect relevant changes per manuscript ===
wrong_use_counts = defaultdict(int)  # e.g., "a for i"
all_use_counts = defaultdict(int)    # e.g., all "a for x"

for _, row in df.iterrows():
    ms = str(row[MANUSCRIPT_COL]).strip()
    changes = str(row[CHANGE_COL]) if pd.notna(row[CHANGE_COL]) else ""
    for ch in changes.split(","):
        ch = ch.strip()
        match = re.match(r"(.+?)\s+for\s+(.+)", ch)
        if match:
            actual, expected = match.groups()
            if actual == SOURCE_LETTER:
                all_use_counts[ms] += 1
                if expected == TARGET_LETTER:
                    wrong_use_counts[ms] += 1

# === Build result table ===
rows = []
for ms in sorted(all_use_counts.keys()):
    wrong = wrong_use_counts.get(ms, 0)
    total = all_use_counts[ms]
    pct = (wrong / total * 100) if total > 0 else 0
    rows.append({
        "manuscript": ms,
        f'"{SOURCE_LETTER} for {TARGET_LETTER}" count': wrong,
        f'"{SOURCE_LETTER} for *" total': total,
        "percentage": round(pct, 2)
    })

# === Save to CSV ===
result_df = pd.DataFrame(rows)
result_df.to_csv(OUTPUT_CSV, index=False)

print(f"✅ Percentages of '{SOURCE_LETTER}' used instead of '{TARGET_LETTER}' saved to:\n{Path(OUTPUT_CSV).resolve()}")
