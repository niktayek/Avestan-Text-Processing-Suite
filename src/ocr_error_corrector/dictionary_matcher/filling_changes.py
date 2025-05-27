import pandas as pd
import difflib
import re
from pathlib import Path

# === Configuration ===
INPUT_CSV = "/home/nikta/Desktop/OCR/data/CAB/Yasna/yasna matches-0008_matched.csv"
RULES_CSV = "/home/nikta/Desktop/OCR/data/CAB/Yasna/substitution_rules.csv"
OUTPUT_CSV = "/home/nikta/Desktop/OCR/data/CAB/Yasna/0008_filled_changes_hybrid.csv"
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
df = pd.read_csv(INPUT_CSV)  # default assumes comma-separated
rules_df = pd.read_csv(RULES_CSV)

# ⬅️ Keep rules as manual → OCR (do NOT reverse)
change_rules = {(row["from"], row["to"]): row["description"] for _, row in rules_df.iterrows()}

print("🧾 Columns in input file:", df.columns.tolist())

# === Ensure the change column exists or create it ===
if change_col not in df.columns:
    print(f"⚠️ Column '{change_col}' does not exist. Creating it with empty strings...")
    df.insert(len(df.columns), change_col, pd.Series([""] * len(df), dtype="string"))
else:
    df[change_col] = df[change_col].astype("string")

# === Define graphemes ===
SPECIAL_GRAPHEMES = [
        'ŋ́', 'ŋᵛ', 'm̨', 'š́', 'ṣ̌', 'ṣ̌', 'ϑ̣',
    'ā̊', 'ą̇', 'x́', 'xᵛ', 'ə̄', 't̰', 'n', 'ń', 'ą', 'γ', 'δ', 'ẏ', 'ṇ'
]
SPECIAL_GRAPHEMES.sort(key=len, reverse=True)
SPECIAL_GRAPHEME_RE = re.compile('|'.join(map(re.escape, SPECIAL_GRAPHEMES)))

def tokenize_graphemes(s):
    tokens = []
    i = 0
    while i < len(s):
        match = SPECIAL_GRAPHEME_RE.match(s, i)
        if match:
            tokens.append(match.group())
            i = match.end()
        else:
            tokens.append(s[i])
            i += 1
    return tokens

# === Grapheme-aware change matcher ===
new_candidates = set()

def find_changes(manual, ocr):
    manual_tokens = tokenize_graphemes(manual)
    ocr_tokens = tokenize_graphemes(ocr)
    sm = difflib.SequenceMatcher(None, manual_tokens, ocr_tokens)
    ops = sm.get_opcodes()

    changes = []

    for tag, i1, i2, j1, j2 in ops:
        wrongs = manual_tokens[i1:i2]  # from manual
        rights = ocr_tokens[j1:j2]     # to OCR

        if tag == "replace":
            max_len = max(len(wrongs), len(rights))
            for i in range(max_len):
                wrong = wrongs[i] if i < len(wrongs) else ""
                right = rights[i] if i < len(rights) else ""

                if wrong == right or (wrong == "" and right == ""):
                    continue

                if (wrong, right) in change_rules:
                    changes.append(change_rules[(wrong, right)])
                else:
                    changes.append(f"{wrong} for {right}")
                    new_candidates.add((wrong, right))

        elif tag == "delete":
            for wrong in wrongs:
                if wrong == "":
                    continue
                changes.append(f"{wrong} deleted")
                new_candidates.add((wrong, ""))

        elif tag == "insert":
            for right in rights:
                if right == "":
                    continue
                changes.append(f"{right} inserted")
                new_candidates.add(("", right))

    return ", ".join(changes) if changes else ""

# === Apply changes ===
for idx, row in df[df[change_col].isna() | (df[change_col] == "")].iterrows():
    ocr = row[ocr_col]
    manual = row[manual_col]

    if pd.isna(ocr) or pd.isna(manual):
        continue

    # 🔁 Compare: manual (correct) → ocr (observed)
    df.at[idx, change_col] = find_changes(str(manual), str(ocr))

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
