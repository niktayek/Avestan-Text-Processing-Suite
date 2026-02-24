import re
import pandas as pd
from Levenshtein import distance as levenshtein_distance

# === CONFIG ===
canonical_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/Canonical_Yasna.txt"
variant_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/txt/0510.txt"
output_csv = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/Token_compare/0510_token_comparison_dp.csv"

DISTANCE_THRESHOLD = [(7, 2), (20, 3), (1000, 4)]
def distance_threshold(length):
    for max_len, threshold in DISTANCE_THRESHOLD:
        if length <= max_len:
            return threshold
MERGE_THRESHOLD = 5
MERGE_COST = 1

# === Abbreviation & Alias Map (Unified and Final Normal Forms) ===
ABBREVIATIONS = {
    "yas.": "yasnai.",
    "y.": "yasnai.",
    "yasnāica.": "yasnai.",
    "v.": "vamjai.",
    "vaɱāica.": "vamjai.",
    "vahmāica.": "vamjai.",
    "x.": "xšnaōϑrāica.",
    "xšnaōϑrāica.": "xšnaōϑrāica.",
    "f.": "frasastaiiai.",
    "fr.": "frasastaiiai.",
    "fra.": "frasastaiiai.",
    "frasastaiiaēca.": "frasastaiiai.",
    "frasastaiiai.": "frasastaiiai.",
    "ńīuuaē.": "ńīuuaēδāiēmi.",
    "ńiuuaē.": "ńīuuaēδāiēmi.",
    "ńiuu.": "ńīuuaēδāiēmi.",
    "niuu.": "ńīuuaēδāiēmi.",
    "haṇ.": "haṇkāraiēmi.",
    "āii.": "āiiese.",
    "ā.": "āiiese.",
    "ye.": "yešti.",
    "yaz.": "yazamaide.",
    "bars.": "barəsmanaēca.",
    "āuu.": "āuuaēδaiiamahi.",
    "aō.": "aōjasca.",
    "z.": "zauuarəca."
}

# === Substitution Equivalence Pairs ===
SUBSTITUTION_EQUIVS = {
    ("vaɱāica.", "vahmāica."),
    ("vahmāica.", "vaɱāica."),
}

# === Block Extractor ===
def extract_blocks(path):
    blocks = {}
    current_id = None
    id_pattern = re.compile(r'^(Y\d+\.\w+)\b')

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            match = id_pattern.match(line)
            if match:
                current_id = match.group(1)
                blocks[current_id] = []
                text = line[match.end():].strip()
            elif current_id:
                text = line
            else:
                continue

            text = re.sub(r'\([^)]*\)', '', text)
            text = re.sub(r'\[[^\]]*\]', '', text)
            text = re.sub(r'=.*', '', text)
            text = re.sub(r'[≈#].*', '', text)

            if text.strip():
                blocks[current_id].append(text.strip())

    for k in blocks:
        text = " ".join(blocks[k])
        tokens = re.split(r'(?<=[. ])\s*', text)
        tokens = [t.strip() for t in tokens if t.strip()]
        blocks[k] = tokens
    return blocks

# === Normalization Logic ===
EQUIVALENCE_CLASSES = [
    {"a", "ą", "ą̇", "å", "ā", "ə", "ai"},
    {"ae", "aē"},
    {"aē", "ī"},
    {"ə̄e", "ī"},
    {"o", "ō", "u"},
    {"ar", "r", "arə"},
    {"ə", "i", "ī", "e", "ē"},
    {"ī", "i", "ə̄"},
    {"ii", "ī"},
    {"ao", "aō"},
    {"uu", "ū", "ī", "v"},
    {"ŋ", "ŋ́", "ŋᵛ"},
    {"s", "š", "š́", "ṣ", "ṣ̌"},
    {"mh", "m̨"},
    {"x", "x́", "xᵛ"},
    {"n", "ń", "ṇ"},
    {"ū", "ī", "ī"},
    {"ϑ", "t"},
    {"d", "δ"},
    {"ɱ", "hm"},
]

REPLACEMENT_MAP = {}
for group in EQUIVALENCE_CLASSES:
    rep = sorted(group, key=len)[0]  # use shortest by default
    for variant in group:
        REPLACEMENT_MAP[variant] = rep

normalizer_memo = {}

def normalize(text):
    if text in normalizer_memo:
        return normalizer_memo[text]
    original_text = text
    text = text.replace("aitē.", "īti.")
    text = text.replace("ā̊", "ā").replace("š́", "š").replace("ẏ", "y")
    text = text.replace(".", "").replace(" ", "")
    for variant, rep in REPLACEMENT_MAP.items():
        text = re.sub(variant, rep, text)
    text = text.lower()
    normalizer_memo[original_text] = text
    return text

# === Token Normalizer (Abbreviation-aware) ===
def normalize_token_for_alignment(t):
    t = t.strip()
    t_for_abbreviation = re.sub(r'\s', '', t)
    if t_for_abbreviation in ABBREVIATIONS:
        return normalize(ABBREVIATIONS[t_for_abbreviation])
    return normalize(t)

# === Token Equivalence Check ===
def tokens_equivalent(t1, t2):
    norm1 = normalize_token_for_alignment(t1)
    norm2 = normalize_token_for_alignment(t2)
    return (
        norm1 == norm2 or
        (t1, t2) in SUBSTITUTION_EQUIVS or
        (t2, t1) in SUBSTITUTION_EQUIVS
    )

# === Alignment Logic ===
def align_tokens(canon, variant):
    m, n = len(canon), len(variant)
    dp = [[(0, []) for _ in range(n + 1)] for _ in range(m + 1)]

    for i in range(1, m + 1):
        dp[i][0] = (dp[i-1][0][0] + len(normalize_token_for_alignment(canon[i-1])), dp[i - 1][0][1] + [("omission", canon[i - 1], "")])
    for j in range(1, n + 1):
        dp[0][j] = (dp[0][j-1][0] + len(normalize_token_for_alignment(variant[j-1])), dp[0][j - 1][1] + [("addition", "", variant[j - 1])])

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            options = []

            c_raw = canon[i - 1]
            v_raw = variant[j - 1]
            c_tok = normalize_token_for_alignment(c_raw)
            v_tok = normalize_token_for_alignment(v_raw)

            # === Option 1: Direct Match/Substitution
            if tokens_equivalent(c_raw, v_raw):
                options.append((dp[i - 1][j - 1][0], dp[i - 1][j - 1][1] + [("match", c_raw, v_raw)]))
            else:
                cost = levenshtein_distance(c_tok, v_tok)
                if cost <= distance_threshold(len(c_tok)):
                    label = "substitution (?)"
                    options.append((dp[i - 1][j - 1][0] + cost, dp[i - 1][j - 1][1] + [(label, c_raw, v_raw)]))

            # === Option 2: Omission
            options.append((dp[i - 1][j][0] + len(c_tok), dp[i - 1][j][1] + [("omission", canon[i - 1], "")]))

            # === Option 3: Addition
            options.append((dp[i][j - 1][0] + len(v_tok), dp[i][j - 1][1] + [("addition", "", variant[j - 1])]))

            # === Option 4: Duplication
            if j - 1 > 0:
                prev_v_tok = normalize_token_for_alignment(variant[j - 2])
                if levenshtein_distance(v_tok, prev_v_tok) < distance_threshold(len(v_tok)):
                    options.append((
                        dp[i][j - 1][0] + len(v_tok) / 2,
                        dp[i][j - 1][1] + [("repeated", "", v_raw)]
                    ))

            # === Option 5: Merge Tokens
            for k_c in range(1, MERGE_THRESHOLD + 1):
                if i - k_c < 0:
                    continue
                for k_v in range(1, MERGE_THRESHOLD + 1):
                    if j - k_v < 0:
                        continue
                    if k_c == 1 and k_v == 1:
                        continue
                    merged_c_raw = " + ".join(canon[i - k_c:i])
                    merged_c_tok = normalize_token_for_alignment("".join(canon[i - k_c:i]))
                    merged_v_raw = " + ".join(variant[j - k_v:j])
                    merged_v_tok = normalize_token_for_alignment("".join(variant[j - k_v:j]))
                    cost = levenshtein_distance(merged_c_tok, merged_v_tok)
                    if cost <= distance_threshold(len(merged_c_tok)):
                        label = "merge substitution (?)" if cost > 0 else "merge match"
                        options.append(
                            (dp[i - k_c][j - k_v][0] + cost + MERGE_COST,
                             dp[i - k_c][j - k_v][1] + [(label, merged_c_raw, merged_v_raw)])
                        )

            dp[i][j] = min(options, key=lambda x: x[0])

    return dp[m][n][1]

# === Load and Compare ===
canon_blocks = extract_blocks(canonical_path)
variant_blocks = extract_blocks(variant_path)

a='māzdaiiasninąm.'
b='mazdiiasnanąm.'
print(a, normalize_token_for_alignment(a))
print(b, normalize_token_for_alignment(b))
print(levenshtein_distance(normalize_token_for_alignment(a), normalize_token_for_alignment(b)))

shared_ids = sorted(set(canon_blocks.keys()) & set(variant_blocks.keys()))
records = []
for bid in shared_ids:
    canon_tokens = canon_blocks[bid]
    variant_tokens = variant_blocks[bid]
    aligned = align_tokens(canon_tokens, variant_tokens)

    for i, (status, ctok, vtok) in enumerate(aligned):
        records.append({
            "block_id": bid,
            "position": i,
            "canonical_token": ctok,
            "variant_token": vtok,
            "status": status
        })

# === Export
df = pd.DataFrame(records)
df.to_csv(output_csv, index=False)
print(f" Token alignment complete. Output saved to: {output_csv}")