import re
import pandas as pd
from Levenshtein import distance as levenshtein_distance

# === CONFIG ===
canonical_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/Canonical_Yasna.txt"
variant_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/txt/0005.txt"
output_csv = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/0005_token_comparison_dp.csv"

DISTANCE_THRESHOLD = 3
MERGE_COST = 0.2

# === Abbreviation & Alias Map (Unified and Final Normal Forms) ===
ABBREVIATIONS = {
    "yas.": "yasnai",
    "y.": "yasnai",
    "yasnāica.": "yasnai",
    "v.": "vamjai",
    "vaɱāica.": "vamjai",
    "vahmāica.": "vamjai",
    "x.": "xšnaōϑrāica",
    "xšnaōϑrāica.": "xšnaōϑrāica",
    "f.": "frasastaiiai",
    "fr.": "frasastaiiai",
    "fra.": "frasastaiiai",
    "frasastaiiaēca.": "frasastaiiai",
    "frasastaiiai.": "frasastaiiai",
    "ńīuuaē.": "ńīuuaēδāiēmi",
    "ńiuuaē.": "ńīuuaēδāiēmi",
    "ńiuu.": "ńīuuaēδāiēmi",
    "niuu.": "ńīuuaēδāiēmi",
    "haṇ.": "haṇkāraiēmi",
    "āii.": "āiiese",
    "ā.": "āiiese",
    "ye.": "yešti",
    "yaz.": "yazamaide",
    "bars.": "barəsmanaēca",
    "āuu.": "āuuaēδaiiamahi",
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
        tokens = re.split(r'(?<=[.])\s*', text)
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
    if t in ABBREVIATIONS:
        return normalize(ABBREVIATIONS[t])
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
        dp[i][0] = (i, dp[i - 1][0][1] + [("omission", canon[i - 1], "")])
    for j in range(1, n + 1):
        dp[0][j] = (j, dp[0][j - 1][1] + [("addition", "", variant[j - 1])])

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            c_raw = canon[i - 1]
            v_raw = variant[j - 1]
            if tokens_equivalent(c_raw, v_raw):
                cost = 0
                label = "match"
            else:
                c_tok = normalize_token_for_alignment(c_raw)
                v_tok = normalize_token_for_alignment(v_raw)
                cost = levenshtein_distance(c_tok, v_tok)
                label = "substitution (?)" if cost <= DISTANCE_THRESHOLD else "substitution (×)"

            options = [
                (dp[i - 1][j - 1][0] + cost, dp[i - 1][j - 1][1] + [(label, c_raw, v_raw)]),
                (dp[i - 1][j][0] + 1, dp[i - 1][j][1] + [("omission", c_raw, "")]),
                (dp[i][j - 1][0] + 1, dp[i][j - 1][1] + [("addition", "", v_raw)])
            ]

            dp[i][j] = min(options, key=lambda x: x[0])

    return dp[m][n][1]

# === Load and Compare ===
canon_blocks = extract_blocks(canonical_path)
variant_blocks = extract_blocks(variant_path)

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
print(f"✅ Token alignment complete. Output saved to: {output_csv}")
