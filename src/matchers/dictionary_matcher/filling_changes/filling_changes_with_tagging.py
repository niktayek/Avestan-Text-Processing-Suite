import pandas as pd
import difflib
import re
import unicodedata
from pathlib import Path

# === Configuration ===
INPUT_CSV = "/Users/niktayekrangsafakar/Documents/OCR/data/CAB/Yasna/res/yasna matches filled changes - 5,6,15,40,400,60,83,88,510,410.csv"
# OUTPUT_CSV = "/home/nikta/Desktop/OCR/data/CAB/Yasna/yasna_matches_filled_features_410.csv"
OUTPUT_CSV = "/Users/niktayekrangsafakar/Documents/OCR/data/CAB/Yasna/res/5,6,15,40,400,60,83,88,510,410_tagged-soroush.csv"

ocr_col = "ocr_word"
manual_col = "manual_word"
change_col = "the change"
tag_col = "feature_tag"
flag_col = "undocumented_flag"

# === Load input
df = pd.read_csv(INPUT_CSV)
df[change_col] = df.get(change_col, "").fillna("")

# === Grapheme tokenization
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

# === Directional substitution
def normalize_substitution(ocr_part, manual_part):
    return f"{ocr_part} for {manual_part}"

# === Grapheme-level alignment
# def align_graphemes(manual_tokens, ocr_tokens, depth=0, max_depth=10):
#     if depth > max_depth:
#         return [normalize_substitution(''.join(ocr_tokens), ''.join(manual_tokens))]

#     sm = difflib.SequenceMatcher(None, manual_tokens, ocr_tokens)
#     changes = []

#     for tag, i1, i2, j1, j2 in sm.get_opcodes():
#         manual_part = manual_tokens[i1:i2]
#         ocr_part = ocr_tokens[j1:j2]

#         if tag == "equal":
#             continue

#         if tag == "replace" and (len(manual_part) == len(ocr_part)):
#             for m_tok, o_tok in zip(manual_part, ocr_part):
#                 if m_tok != o_tok:
#                     changes.append(normalize_substitution(o_tok, m_tok))
#             continue

#         if tag == "replace":
#             sub_changes = align_graphemes(manual_part, ocr_part, depth+1, max_depth)
#             changes.extend(sub_changes)
#             continue

#         if tag == "delete":
#             for m_tok in manual_part:
#                 changes.append(f"{m_tok} deleted")
#         if tag == "insert":
#             for o_tok in ocr_part:
#                 changes.append(f"{o_tok} inserted")

#     return changes

def dp_differ(manual_tokens: list[str], ocr_tokens: list[str]) -> list[tuple[str, str]]:
    # DP table for minimal edit distance
    m, n = len(manual_tokens), len(ocr_tokens)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if manual_tokens[i - 1] == ocr_tokens[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j],    # delete
                                   dp[i][j - 1],    # insert
                                   dp[i - 1][j - 1]) # substitute

    # Backtrack to get the diff
    i, j = m, n
    diff = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and manual_tokens[i - 1] == ocr_tokens[j - 1]:
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or dp[i][j] == dp[i - 1][j] + 1):
            diff.append(("delete", manual_tokens[i - 1]))
            i -= 1
        elif j > 0 and (i == 0 or dp[i][j] == dp[i][j - 1] + 1):
            diff.append(("insert", ocr_tokens[j - 1]))
            j -= 1
        else:
            # Replace: show both manual and ocr token
            diff.append(("replace", manual_tokens[i - 1], ocr_tokens[j - 1]))
            i -= 1
            j -= 1
    diff.reverse()

    diff = [
        f"{token_diff[1]} inserted" if token_diff[0] == 'insert' else
        f"{token_diff[1]} deleted" if token_diff[0] == 'delete' else
        normalize_substitution(token_diff[2], token_diff[1]) if token_diff[0] == 'replace' else None
        for token_diff in diff
    ]

    return diff


# === Fill missing change column
for idx, row in df[df[change_col] == ""].iterrows():
    ocr = str(row[ocr_col])
    manual = str(row[manual_col])
    if pd.isna(ocr) or pd.isna(manual):
        continue
    manual_tokens = tokenize_graphemes(unicodedata.normalize("NFC", manual))
    ocr_tokens = tokenize_graphemes(unicodedata.normalize("NFC", ocr))
    changes = dp_differ(manual_tokens, ocr_tokens)
    df.at[idx, change_col] = ", ".join(changes)

# === Tagging map from explanation
FEATURE_POSTPROCESS_MAP = {
    r"e for aē": "Monophthongization of aē to e, frequent in Indian manuscripts.",
    r"š for ṣ̌": "Loss of palatal distinction: š replaces ṣ̌, common in Indian copies.",
    r"x́ for xᵛ": "Velar fricative confusion: x́ replaces xᵛ, especially in Indian manuscripts.",
    r"hm for ɱ": "hm used instead of ɱ, typical in Iranian and Indian liturgical copies.",
    r"ŋ for ŋ́": "Palatal nasal ŋ́ replaced by ŋ, often in Indian manuscripts.",
    r"ṣ̌ for š": "Palatal ṣ̌ appears for š, notable in Old Exegetical Indian copies.",
    r"ō inserted": "ō appears by monophthongization of aō, seen in recent Iranian manuscripts.",
    r"n for ń": "Palatal ń replaced by n, especially in Indian traditions.",
    r"u for ū": "Short u replaces ū, due to vowel merging in late tradition.",
    r"š for ī": "[UNSUPPORTED] Consonant for vowel: not documented.",
    r"o for š": "[UNSUPPORTED] Vowel for consonant: not valid.",
    r"uu deleted": "[UNSUPPORTED] Not known as general rule.",
    r"oi for aōi": "oi replaces diphthong aōi, especially in Indian manuscripts.",
    r"miiaz inserted": "[UNSUPPORTED] Possibly word-specific, not rule-based.",
    r"δ for d": "Fricativization of d to δ, common initially in Indian manuscripts.",
    r"āi for ā": "[UNSUPPORTED] Undocumented substitution.",
    r"ē inserted": "[UNSUPPORTED] Not attested as a systematic insertion.",
    r"ə for i": "ə used for i, especially in Iranian manuscripts.",
    r"ŋ for ŋᵛ": "Labialized nasal ŋᵛ becomes ŋ or ŋh in both traditions.",
    r"ō for o": "Lengthened ō for o, minor orthographic variation.",
    r"a for ī": "[UNSUPPORTED] Not documented as general rule.",
    r"ii for aii": "ii replaces aii by vowel syncope, especially in Indian tradition.",
    r"ca for cit̰": "Cluster shift: t̰c becomes dac or tac, due to anaptyxis.",
    r"ā for ą": "[ORAL] Long ā replaces nasal ą, seen in recitation, not manuscripts.",
    r"u for uu": "Short u replaces uu or ū, common in Indian manuscripts.",
    r"uu for u": "uu replaces short u, lengthening effect common in Indian copies.",
    r"ah for ai": "[UNSUPPORTED] Not attested as general feature.",
    r"š for s": "š replaces s in clusters, widespread in Indian manuscripts.",
    r"word inserted": "Anaptyxis: vowel inserted in clusters or word-finally.",
    r"t inserted": "[UNSUPPORTED] Not a standalone pattern.",
    r"n for r": "[UNSUPPORTED] Not documented.",
    r"ṇ inserted": "ṇ inserted in place of ą or before consonants, esp. Iranian tradition.",
    r"o for uu": "[UNSUPPORTED] Seen in Persian transcriptions, not in Avestan.",
    r"n inserted, u for uu": "Combination: n inserted and u used instead of uu.",
    r"n inserted, ə inserted": "Combination of n and ə insertion in clusters.",
    r"ṇ for niš": "[UNSUPPORTED] Not documented.",
    r"ṇ inserted, ą̇ for ą": "Indian ą̇ combined with Iranian ṇ insertion.",
    r"ṣ̌ for š, ao for aō": "Combination: ṣ̌→š and shortened diphthong ao for aō.",
    r"ẏ for d": "[UNSUPPORTED] Not documented: likely OCR error or misreading.",
    r"ẏ for y": "Orthographic variation: ẏ used for y in Indian tradition.",
    r"ẏ for y, ae for aē, š for š́": "Common Indian variants: ae for aē, ẏ for y, š for š́.",
    r"ae for aē": "Shortened diphthong ae for aē, frequent in Indian copies.",
    r"š for š́": "š used for š́, both often confused in manuscript spelling.",
    r"ẏ for y, auuV for uu(V)": "Indian orthographic variants: ẏ/y and auu for ū.",
    r"auuV for uu(V)": "auu replaces ū, common Indian variant spelling.",
    r"ẏ for y, hm for ɱ": "Combination: ẏ for y and hm for ɱ.",
    r"ẏ for y, ą̇ for ą": "Indian features: ą̇ for ą and ẏ for y.",
    r"ōu for ou, x́ for xᵛ, ṇ for n, ą̇ for ą": "Combined features from both traditions.",
    r"ōu for ou": "ōu used instead of ou in both Iranian and Indian manuscripts.",
    r"ṇ for n": "[REVERSED] Actual common pattern is n for ṇ, not this.",
    r"ą̇ for ą": "ą̇ is standard in Indian manuscripts, ą in Iranian ones.",
    r"ao for aō": "Shortened diphthong ao for aō, frequent in Indian manuscripts.",
    r"š for ṣ̌": "š used for ṣ̌ (written ṣ̌), common simplification.",
    r"š for ṣ̌, x́ for xᵛ": "Combined simplifications: ṣ̌→š, xᵛ→x́.",
    r"š for ṣ̌, ą̇ for ą": "Combination of Indian orthographic traits.",
    r"š́ for š": "š́ appears where š expected, variant spelling.",
    r"š́ for ṣ̌": "š́ used for ṣ̌ (via ṣ̌), though not standard.",
    r"š́ for ṣ̌, ą̇ for ą": "Combination: ą̇ and š́ for ṣ̌, both Indian features.",
    r"ū for o": "[UNSUPPORTED] Not documented.",
    r"ə deleted": "Vowel syncope: loss of short ə, especially before semivowels.",
    r"ə for a": "[UNSUPPORTED] Not documented.",
    r"ə for i, ao for aō": "Combined substitution patterns.",
    r"ə for ą": "[UNSUPPORTED] Not documented.",
    r"r for n": "[UNSUPPORTED] Not documented.",
    r"r inserted": "[UNSUPPORTED] Not documented as general insertion pattern.",
    r"t for ϑ": "Fricative ϑ replaced by t, common in Persian transcriptions.",
    r"t inserted, n for r": "[UNSUPPORTED] Not attested.",
    r"u for aō, aii for ii": "Combined substitutions: monophthongization and vowel syncopation.",
    r"u for aō": "aō replaced by u, seen in oral-influenced Indian manuscripts.",
    r"aii for ii": "aii replaces ii; variant spelling common in Indian tradition.",
    r"u inserted": "u inserted epenthetically, e.g., ŋuh for ŋᵛh.",
    r"n inserted": "Insertion of n in nasal forms like ąn before consonants.",
    r"b deleted": "[UNSUPPORTED] Not documented.",
    r"dd for đ": "[UNSUPPORTED] Not documented.",
    r"dd deleted": "[UNSUPPORTED] Not documented.",
    r"ă inserted": "[UNSUPPORTED] Not documented.",
    r"ei for u": "[UNSUPPORTED] Not documented.",
    r"en replaced by o": "[UNSUPPORTED] Not documented.",
    r"x inserted": "[UNSUPPORTED] Not documented.",
    r"š inserted": "[UNSUPPORTED] Not documented.",
    r"ṛ for n": "[UNSUPPORTED] Not documented.",
    r"ɔ replaced by u": "[UNSUPPORTED] Not documented.",
}

# === Tag and flag
def postprocess_feature_label(change_str):
    matched_tags = set()
    for pattern, tag in FEATURE_POSTPROCESS_MAP.items():
        if re.search(pattern, change_str):
            matched_tags.add(tag)
    return ", ".join(sorted(matched_tags)) if matched_tags else ""

def flag_undocumented(change_str):
    for pattern in FEATURE_POSTPROCESS_MAP:
        if re.search(pattern, change_str):
            return False
    return bool(change_str.strip())  # True if there's content but no match

df[tag_col] = df[change_col].apply(postprocess_feature_label)
df[flag_col] = df[change_col].apply(flag_undocumented)

# === Export final
df.to_csv(OUTPUT_CSV, index=False)
print(f" Exported tagged file: {OUTPUT_CSV}")
