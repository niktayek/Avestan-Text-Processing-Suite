import os
import xml.etree.ElementTree as ET
import pandas as pd
import re
import Levenshtein

# === CONFIGURATION ===
canonical_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/static_yasna.xml"
variant_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/raw_XMLs_fixed/0005.xml"  # <— single file
rule_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/final_cleaned_rules_ready.csv"
output_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/yasna_diff_report_0005.csv"
DISTANCE_THRESHOLD = 2

# === Load Substitution Rules ===
rules_df = pd.read_csv(rule_path)
rules_set = set((row['from'], row['to']) for _, row in rules_df.iterrows())

# === Normalizer (from matcher) ===
normalizer_memo = {}
def normalize(text):
    if text in normalizer_memo:
        return normalizer_memo[text]
    original_text = text
    uniform_list = [
        ('a', ['ą', 'ą̇', 'å', 'ā']),
        ('ae', ['aē']),
        ('o', ['ō']),
        ('e', ["i"]),
        ('i', ['\\.']),
        ('ao', ['aō']),
        ('uu', ['ū', 'ī', 'ii']),
        ('ŋ', ['ŋ́', 'ŋᵛ']),
        ('s', ['š', 'š́', 'ṣ', 'ṣ̌']),
        ('mh', ['m̨']),
        ('x', ['x́', 'xᵛ']),
        ('n', ['ń', 'ṇ']),
        ('ī', ['ū']),
        ('ϑ', ['t']),
        ('d', ['δ']),
    ]
    for replacement, variants in uniform_list:
        for char in variants:
            text = re.sub(char, replacement, text)
    normalizer_memo[original_text] = text
    return text

# === Tokenizer ===
def tokenize(text):
    parts = re.split(r"\.(?!\S)", text)
    return [p.strip() for p in parts if p.strip()]

# === Load Canonical Yasna XML ===
canonical_tree = ET.parse(canonical_path)
canonical_root = canonical_tree.getroot()

# XML namespaces
ns = {
    'tei': canonical_root.tag.split("}")[0].strip("{"),
    'xml': "http://www.w3.org/XML/1998/namespace"
}

# === Extract canonical blocks ===
canonical_blocks = {}
for ab in canonical_root.findall(".//tei:ab[@xml:id]", ns):
    xml_id = ab.attrib.get("{http://www.w3.org/XML/1998/namespace}id")
    text = ET.tostring(ab, encoding="unicode", method="text").strip()
    canonical_blocks[xml_id] = tokenize(text)

# === Compare with single manuscript file ===
results = []
fname = os.path.basename(variant_path)
tree = ET.parse(variant_path)
root = tree.getroot()

for ab in root.findall(".//ab[@xml:id]", ns):
    xml_id = ab.attrib.get("{http://www.w3.org/XML/1998/namespace}id")

    if xml_id not in canonical_blocks:
        print(f" Skipping: {xml_id} not in canonical (from {fname})")
        continue

    if not canonical_blocks[xml_id]:
        print(f" Skipping: {xml_id} has no tokens in canonical")
        continue

    variant_text = ET.tostring(ab, encoding="unicode", method="text").strip()
    variant_tokens = tokenize(variant_text)

    if not variant_tokens:
        print(f" Skipping: {xml_id} has no tokens in manuscript ({fname})")
        continue

    canonical_tokens = canonical_blocks[xml_id]

    print(f"\n📌 Comparing block: {xml_id} from {fname}")
    print(f"Canonical tokens: {canonical_tokens}")
    print(f"Variant tokens:   {variant_tokens}")

    for i, (canon_tok, var_tok) in enumerate(zip(canonical_tokens, variant_tokens)):
        norm_canon = normalize(canon_tok)
        norm_var = normalize(var_tok)
        edit_distance = Levenshtein.distance(norm_canon, norm_var)

        if edit_distance <= DISTANCE_THRESHOLD:
            continue
        elif (canon_tok, var_tok) in rules_set or (var_tok, canon_tok) in rules_set:
            continue
        else:
            results.append({
                "block_id": xml_id,
                "manuscript": fname,
                "type": "substitution",
                "canonical_token": canon_tok,
                "ocr_token": var_tok,
                "position": i
            })

    # Handle omissions/additions
    if len(canonical_tokens) > len(variant_tokens):
        for j in range(len(variant_tokens), len(canonical_tokens)):
            results.append({
                "block_id": xml_id,
                "manuscript": fname,
                "type": "omission",
                "canonical_token": canonical_tokens[j],
                "ocr_token": "",
                "position": j
            })
    elif len(variant_tokens) > len(canonical_tokens):
        for j in range(len(canonical_tokens), len(variant_tokens)):
            results.append({
                "block_id": xml_id,
                "manuscript": fname,
                "type": "addition",
                "canonical_token": "",
                "ocr_token": variant_tokens[j],
                "position": j
            })

# === Export
df = pd.DataFrame(results)
df.to_csv(output_path, index=False)
print(f"\n Total differences found: {len(results)}")
print(f"📄 Output written to: {output_path}")
