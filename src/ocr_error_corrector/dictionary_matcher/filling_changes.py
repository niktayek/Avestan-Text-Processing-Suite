import pandas as pd
import difflib
import re
from pathlib import Path

# === Configuration ===
INPUT_CSV = "/home/nikta/Desktop/OCR/src/ocr_error_corrector/dictionary_matcher/res/matches.csv"
RULES_CSV = "/home/nikta/Desktop/OCR/data/CAB/Yasna/substitution_rules.csv"
OUTPUT_CSV = "/home/nikta/Desktop/OCR/data/CAB/Yasna/0006_filled_changes_hybrid.csv"
NEW_RULE_LOG = "/home/nikta/Desktop/OCR/data/CAB/Yasna/new_rule_candidates.txt"

ocr_col = "ocr_word"
manual_col = "manual_word"
change_col = "the change"

# === Check file paths ===
print("📄 Checking input file at:", Path(INPUT_CSV).resolve())
if not Path(INPUT_CSV).exists():
    raise FileNotFoundError(f"❌ File not found: {Path(INPUT_CSV).resolve()}")

print("📄 Checking rules file at:", Path(RULES_CSV).resolve())
if not Path(RULES_CSV).exists():
    raise FileNotFoundError(f"❌ Rules file not found: {Path(RULES_CSV).resolve()}")

# === Load input and rules ===
df = pd.read_csv(INPUT_CSV, sep="\t")  # important: using tab separator
rules_df = pd.read_csv(RULES_CSV)
change_rules = {(row["from"], row["to"]): row["description"] for _, row in rules_df.iterrows()}

# Show available columns
print("🧾 Columns in input file:", df.columns.tolist())

# === Ensure the change column exists or create it ===
if change_col not in df.columns:
    print(f"⚠️ Column '{change_col}' does not exist. Creating it with empty strings...")
    df.insert(len(df.columns), change_col, pd.Series([""] * len(df), dtype="string"))
else:
    df[change_col] = df[change_col].astype("string")

# === Function to find character-level changes ===
def find_changes(orig, corr):
    sm = difflib.SequenceMatcher(None, orig, corr)
    ops = sm.get_opcodes()
    changes = []
    for tag, i1, i2, j1, j2 in ops:
        if tag == "replace":
            wrong = orig[i1:i2]
            right = corr[j1:j2]
            if (right, wrong) in change_rules:
                changes.append(change_rules[(right, wrong)])
            else:
                changes.append(f"{wrong} for {right}")
                new_candidates.add((wrong, right))
        elif tag == "delete":
            wrong = orig[i1:i2]
            changes.append(f"{wrong} deleted")
            new_candidates.add((wrong, ""))
        elif tag == "insert":
            right = corr[j1:j2]
            changes.append(f"{right} inserted")
            new_candidates.add(("", right))
    return ", ".join(changes) if changes else ""

# === Apply hybrid rule detection ===
new_candidates = set()

for idx, row in df[df[change_col].isna() | (df[change_col] == "")].iterrows():
    ocr = row[ocr_col]
    manual = row[manual_col]

    if pd.isna(ocr) or pd.isna(manual):
        continue

    df.at[idx, change_col] = find_changes(str(ocr), str(manual))

# === Save output CSV ===
df.to_csv(OUTPUT_CSV, index=False)
print(f"\n✅ Updated file saved to: {Path(OUTPUT_CSV).resolve()}")

# === Save new rule candidates ===
if new_candidates:
    with open(NEW_RULE_LOG, "w", encoding="utf-8") as f:
        for wrong, right in sorted(new_candidates):
            if wrong and right:
                f.write(f"{wrong} for {right}\n")
            elif wrong:
                f.write(f"{wrong} deleted\n")
            elif right:
                f.write(f"{right} inserted\n")
    print(f"📝 New rule candidates saved to: {Path(NEW_RULE_LOG).resolve()}")
else:
    print("✅ No new rule candidates found.")
