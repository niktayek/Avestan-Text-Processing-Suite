import pandas as pd
import re

# === CONFIG ===
# ✅ Simply change the rule version here:
RULE_VERSION = 1  # ← ← ← change this number for v1, v2, ..., v6

# File paths
FILLED_CHANGES_FILE = "/home/nikta/Desktop/OCR/data/CAB/Yasna/yasna matches filled changes - 5,6,8,15,40,400,60_filled_changes_hybrid.csv"
SUBSTITUTION_RULES_FILE = f"/home/nikta/Desktop/OCR/data/CAB/Yasna/substitution_rules_v{RULE_VERSION}.csv"
TAGGED_OUTPUT_FILE = f"/home/nikta/Desktop/OCR/data/CAB/Yasna/yasna_tagged_optionC_v{RULE_VERSION}.csv"

# === Load data ===
df = pd.read_csv(FILLED_CHANGES_FILE)
rules_df = pd.read_csv(SUBSTITUTION_RULES_FILE)

# === Build rule sets ===
trivial_rules = set(
    rules_df.query("type == '1'").apply(lambda row: f"{row['to']} for {row['from']}".strip(), axis=1)
)
r_b_rules = set(
    rules_df.query("type == 'r-b'").apply(lambda row: f"{row['to']} for {row['from']}".strip(), axis=1)
)

# === Uncertain patterns ===
uncertain_patterns = [
    r"ou", r"ōu", r"aōu", r"aou", r"ϑr.*str"
]

# === Classification function ===
def classify_subchange(subchange):
    subchange = subchange.strip()
    if "inserted" in subchange:
        return "insertion"
    elif "deleted" in subchange:
        return "deletion"
    elif "for" in subchange:
        if subchange in trivial_rules:
            return "1"
        if subchange in r_b_rules:
            return "r-b"
        for pattern in uncertain_patterns:
            if re.search(pattern, subchange):
                return "?"
        return "?"
    else:
        return "?"

# === Apply classification row-wise ===
def tag_row(change_str):
    if pd.isna(change_str) or change_str.strip() == "":
        return "="
    subchanges = [ch.strip() for ch in change_str.split(",")]
    tags = [classify_subchange(sub) for sub in subchanges]
    return ",".join(tags)

df["Leitfehler_tag"] = df["the change"].apply(tag_row)

# === Quick diagnostic output ===
total_rows = len(df)
uncertain_rows = sum(df["Leitfehler_tag"].str.contains(r"\?"))
print(f"✅ Tagging complete for rule set v{RULE_VERSION}.")
print(f"Total rows processed: {total_rows}")
print(f"Total rows containing '?': {uncertain_rows}")

# === Save output ===
df.to_csv(TAGGED_OUTPUT_FILE, index=False)
print(f"✅ Output saved to: {TAGGED_OUTPUT_FILE}")
