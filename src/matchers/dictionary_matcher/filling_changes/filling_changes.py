import pandas as pd
import difflib
import re
import unicodedata
from pathlib import Path

# === Configuration ===
INPUT_CSV = "/home/nikta/Desktop/OCR/data/CAB/Yasna/yasna_matches_filled_changes-5,6,8,15,40,400,60,83,88,510,410.csv"
RULES_CSV = "/home/nikta/Desktop/OCR/data/CAB/Yasna/substitution_rules.csv"
OUTPUT_CSV = "/home/nikta/Desktop/OCR/data/CAB/Yasna/yasna_matches_filled_changes-5,6,8,15,40,400,60,83,88,510,410_filled.csv"
NEW_RULE_LOG = "/home/nikta/Desktop/OCR/data/CAB/Yasna/new_rule_candidates.txt"

ocr_col = "ocr_word"
manual_col = "manual_word"
change_col = "the change"

# === Load input and rules ===
df = pd.read_csv(INPUT_CSV)
rules_df = pd.read_csv(RULES_CSV)
change_rules = {(row["from"], row["to"]): row["description"] for _, row in rules_df.iterrows()}

if change_col not in df.columns:
    df.insert(len(df.columns), change_col, pd.Series([""] * len(df), dtype="string"))
else:
    df[change_col] = df[change_col].astype("string")

# === Normalize function ===
def normalize(text):
    return unicodedata.normalize("NFC", text)

# === Define graphemes ===
SPECIAL_GRAPHEMES = [
    'ə̄u', 'aō', 'aē', 'āu', 'āi', 'ōi', 'ou', 'ai', 'au',
    'ā̊', 'ą̇', 'ə̄', 't̰', 'x́', 'xᵛ', 'ŋ́', 'ŋᵛ', 'š́', 'ṣ̌', 'ṇ', 'ń', 'ɱ', 'ġ', 'γ', 'δ', 'ẏ', 'č', 'ž', 'β',
    'ā', 'ą', 'ō', 'ē', 'ū', 'ī',
    'a', 'o', 'ə', 'e', 'u', 'i',
    'k', 'x', 'g', 'c', 'j', 't', 'ϑ', 'd', 'p', 'b', 'ŋ', 'n', 'm',
    'y', 'v', 'r', 'l', 's', 'z', 'š', 'h', 'uu', 'ii'
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

# === Bidirectional normalization map ===
equivalence_map = {
    ('ii', 'ai'): 'aii for ii',
    ('ai', 'ii'): 'aii for ii',
    ('ii', 'aii'): 'aii for ii',
    ('aii', 'ii'): 'aii for ii',
    ('auu', 'uu'): 'auu(V) for uuV',
    ('uu', 'auu'): 'auu(V) for uuV',
    ('i', 'ə̄'): 'i for ə',
    ('ə̄', 'i'): 'ə for i',
    ('ī', 'ə̄'): 'ī for i',
    ('ə̄', 'ī'): 'i for ī'
}

# === Normalization function ===
def normalize_substitution(ocr_part, manual_part):
    if (ocr_part, manual_part) in equivalence_map:
        return equivalence_map[(ocr_part, manual_part)]
    if (manual_part, ocr_part) in equivalence_map:
        return equivalence_map[(manual_part, ocr_part)]
    return f"{ocr_part} for {manual_part}"

# === Recursive grapheme-level matcher with recursion protection ===
new_candidates = set()

def align_graphemes(manual_tokens, ocr_tokens, depth=0, max_depth=10):
    if depth > max_depth:
        changes = []
        changes.append(normalize_substitution(''.join(ocr_tokens), ''.join(manual_tokens)))
        new_candidates.add((''.join(manual_tokens), ''.join(ocr_tokens)))
        return changes

    sm = difflib.SequenceMatcher(None, manual_tokens, ocr_tokens)
    changes = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        manual_part = manual_tokens[i1:i2]
        ocr_part = ocr_tokens[j1:j2]

        if tag == "equal":
            continue

        if tag == "replace" and (len(manual_part) == len(ocr_part)):
            for m_tok, o_tok in zip(manual_part, ocr_part):
                if m_tok != o_tok:
                    changes.append(normalize_substitution(o_tok, m_tok))
                    new_candidates.add((m_tok, o_tok))
            continue

        if tag == "replace":
            if len(manual_part) == 0 or len(ocr_part) == 0 or abs(len(manual_part)-len(ocr_part)) > 5:
                changes.append(normalize_substitution(''.join(ocr_part), ''.join(manual_part)))
                new_candidates.add((''.join(manual_part), ''.join(ocr_part)))
                continue

            sub_changes = align_graphemes(manual_part, ocr_part, depth+1, max_depth)
            changes.extend(sub_changes)
            continue

        if tag == "delete":
            for m_tok in manual_part:
                changes.append(f"{m_tok} deleted")
                new_candidates.add((m_tok, ""))

        if tag == "insert":
            for o_tok in ocr_part:
                changes.append(f"{o_tok} inserted")
                new_candidates.add(("", o_tok))

    return changes

# === Apply changes ===
for idx, row in df[df[change_col].isna() | (df[change_col] == "")].iterrows():
    ocr = row[ocr_col]
    manual = row[manual_col]

    if pd.isna(ocr) or pd.isna(manual):
        continue

    manual_tokens = tokenize_graphemes(normalize(manual))
    ocr_tokens = tokenize_graphemes(normalize(ocr))
    changes = align_graphemes(manual_tokens, ocr_tokens)
    df.at[idx, change_col] = ", ".join(changes)

# === Save output CSV ===
df.to_csv(OUTPUT_CSV, index=False)
print(f"\n Updated file saved to: {Path(OUTPUT_CSV).resolve()}")

# === Save new rule candidates ===
if new_candidates:
    with open(NEW_RULE_LOG, "w", encoding="utf-8") as f:
        for manual, ocr in sorted(new_candidates):
            if manual and ocr:
                f.write(f"{ocr} for {manual}\n")
            elif manual:
                f.write(f"{manual} deleted\n")
            elif ocr:
                f.write(f"{ocr} inserted\n")
    print(f"📝 New rule candidates saved to: {Path(NEW_RULE_LOG).resolve()}")
else:
    print(" No new rule candidates found.")