import pandas as pd

# === CONFIG ===
ALIGNED_FILE = "/home/nikta/Desktop/OCR/data/CAB/Yasna/yasna_matches_filled_changes-5,6,8,15,40,400,60,83,88,510,410_filled.csv"  # your OCR-manual alignment file
SUBSTITUTION_RULES_FILE = "/home/nikta/Desktop/OCR/data/CAB/Yasna/substitution_rules_v6.csv"  # latest substitution rules
OUTPUT_FILE = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/5,6,8,15,40,400,60,83,88,510,410_tagged.csv"

# === Load input files ===
df = pd.read_csv(ALIGNED_FILE)
rules_df = pd.read_csv(SUBSTITUTION_RULES_FILE)

rules_df['from'] = rules_df['from'].astype(str).str.strip().str.lower()
rules_df['to'] = rules_df['to'].astype(str).str.strip().str.lower()
rules_df['type'] = rules_df['type'].astype(str).str.strip()


def classify_change(change_str):
    # No change provided → return empty string (no category needed)
    if pd.isna(change_str) or change_str.strip() == "":
        return ""

    change_str = change_str.lower()
    matched_1 = []
    matched_rb = []

    for _, row in rules_df.iterrows():
        pattern = f"{row['from']} for {row['to']}"
        tag = row['type']
        if pattern in change_str:
            if tag == '1':
                matched_1.append(pattern)
            elif tag == 'r-b':
                matched_rb.append(pattern)

    if matched_1 and not matched_rb and len(matched_1) == 1:
        return '1'
    elif matched_rb and not matched_1:
        return 'r-b'
    elif (len(matched_1) + len(matched_rb)) > 1:
        return '2'
    elif not matched_1 and not matched_rb:
        return '?'
    else:
        return '?'


# === Apply classification ===
df['category'] = df['the change'].apply(classify_change)

# === Save result ===
df.to_csv(OUTPUT_FILE, index=False)
print(f"Tagged output saved to: {OUTPUT_FILE}")
