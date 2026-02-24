import pandas as pd
from collections import defaultdict
import xml.etree.ElementTree as ET
import re
from difflib import SequenceMatcher

# === CONFIG ===
TAGGED_FILE = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/5,6,8,15,40,400,60,83,88,510,410_tagged.csv"
STATIC_YASNA_PATH = "/home/nikta/Desktop/OCR/data/CAB/Yasna/static_yasna.xml"
BLOCK_OUTPUT = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/block_level_substitution_stanza_level.csv"
RANKED_OUTPUT = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/shared_block_substitution_stanza_level_ranked.csv"
COMPARISON_OUTPUT = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/block_level_substitution_stanza_level_comparison.csv"

# === Step 1: Load tagged file ===
df = pd.read_csv(TAGGED_FILE)
df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
df["manuscript_id"] = df["manuscript_id"].astype(str)

# === Step 2: Extract and normalize stanza ID from address ===
df["address_id"] = df["address"].apply(lambda x: eval(x)[0]["id"] if pd.notnull(x) else None)

def normalize_address_id(addr):
    if not isinstance(addr, str):
        return ""
    match = re.match(r"(Y\d+(?:\.\d+)?(?:[A-Za-z]+)?)", addr)
    return match.group(1).lower() if match else addr.lower()

df["normalized_id"] = df["address_id"].apply(normalize_address_id)

# === Step 3: Extract reference stanzas from canonical XML ===
def extract_canonical_blocks(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    reference_map = {}
    for elem in root.iter():
        xml_id = elem.attrib.get("{http://www.w3.org/XML/1998/namespace}id") or elem.attrib.get("xml:id")
        if xml_id:
            text = " ".join(elem.itertext()).strip()
            clean_text = re.sub(r"\s+", " ", text)
            norm_id = normalize_address_id(xml_id)
            reference_map[norm_id] = clean_text
    return reference_map

canonical_text_by_block = extract_canonical_blocks(STATIC_YASNA_PATH)
print(f" Loaded {len(canonical_text_by_block)} normalized reference blocks")

# === Step 4: Filter to only blocks present in the reference ===
df = df[df["normalized_id"].isin(canonical_text_by_block)]
print(f" {len(df)} rows remain after filtering for available reference stanzas")

# === Step 5: Compare manual vs canonical — Loose substitution detection ===
block_rows = []
comparison_rows = []
substitution_index = defaultdict(list)

for (norm_id, ms_id), group in df.groupby(["normalized_id", "manuscript_id"]):
    manual_words = group["manual_word"].dropna().astype(str).tolist()
    canonical_text = canonical_text_by_block.get(norm_id, "").strip()

    if not manual_words or not canonical_text:
        continue

    manual_tokens = re.sub(r"\s+", " ", " ".join(manual_words).strip()).split()
    canonical_tokens = re.sub(r"\s+", " ", canonical_text.strip()).split()

    if manual_tokens == canonical_tokens:
        continue  # No change

    sm = SequenceMatcher(None, manual_tokens, canonical_tokens)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "replace":
            from_seq = manual_tokens[i1:i2]
            to_seq = canonical_tokens[j1:j2]

            block_rows.append({
                "block_id": norm_id,
                "manuscript_id": ms_id,
                "manual_segment": " ".join(from_seq),
                "canonical_segment": " ".join(to_seq),
                "substitution_type": "loose substitution"
            })

            comparison_rows.append({
                "block_id": norm_id,
                "manuscript_id": ms_id,
                "manual_full": " ".join(manual_tokens),
                "canonical_full": " ".join(canonical_tokens),
                "manual_segment": " ".join(from_seq),
                "canonical_segment": " ".join(to_seq)
            })

            substitution_index[(norm_id, "loose substitution")].append(ms_id)

# === Step 6: Save outputs ===
block_df = pd.DataFrame(block_rows)
block_df.to_csv(BLOCK_OUTPUT, index=False)
print(f" Substitution stanza-level results saved to:\n  {BLOCK_OUTPUT}")

comparison_df = pd.DataFrame(comparison_rows)
comparison_df.to_csv(COMPARISON_OUTPUT, index=False)
print(f"📄 Comparison table saved to:\n  {COMPARISON_OUTPUT}")

summary_rows = []
for (block_id, sub_type), mss in substitution_index.items():
    summary_rows.append({
        "block_id": block_id,
        "substitution_summary": sub_type,
        "num_manuscripts": len(set(mss)),
        "manuscripts": ", ".join(sorted(set(mss)))
    })

summary_df = pd.DataFrame(summary_rows)
if not summary_df.empty:
    summary_df = summary_df.sort_values(by=["num_manuscripts", "block_id"], ascending=[False, True])
    summary_df.to_csv(RANKED_OUTPUT, index=False)
    print(f" Ranked summary saved to:\n  {RANKED_OUTPUT}")
else:
    print(" No loose substitutions detected — ranked summary not created.")
