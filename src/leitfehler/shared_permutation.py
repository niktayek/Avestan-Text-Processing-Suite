import pandas as pd
import xml.etree.ElementTree as ET
from collections import defaultdict
import re

# === CONFIG ===
TAGGED_FILE = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/5,6,8,15,40,400,60,83,88,510,410_tagged.csv"
STATIC_YASNA_FILE = "/home/nikta/Desktop/OCR/data/CAB/Yasna/static_yasna.xml"
RANKED_OUTPUT = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/shared_permutation_ranked_blocks.csv"
COMPARISON_OUTPUT = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/permutation_block_comparison.csv"

# === Load tagged OCR data ===
df = pd.read_csv(TAGGED_FILE)
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
df["manuscript_id"] = df["manuscript_id"].astype(str)

# Derive block_id if missing
if "block_id" not in df.columns:
    def extract_block_id(addr):
        if not isinstance(addr, str):
            return ""
        try:
            parsed = eval(addr)
            if isinstance(parsed, list) and isinstance(parsed[0], dict) and "id" in parsed[0]:
                raw_id = parsed[0]["id"]
            else:
                raw_id = addr
        except:
            raw_id = addr

        match = re.match(r"(Y\d+(?:\.\d+)?(?:[A-Za-z]+)?)", raw_id)
        return match.group(1).lower() if match else raw_id.lower()

    df["block_id"] = df["address"].apply(extract_block_id)

print(" Loaded tagged file with shape:", df.shape)
print("📌 Sample block IDs:", df["block_id"].unique()[:5])

# === Load static Yasna reference (no TEI namespace) ===
tree = ET.parse(STATIC_YASNA_FILE)
root = tree.getroot()

# Fix: define and pass the xml namespace
ns = {"xml": "http://www.w3.org/XML/1998/namespace"}

reference_map = {}
for elem in root.findall(".//ab[@xml:id]", ns):
    block_id = elem.attrib.get("{http://www.w3.org/XML/1998/namespace}id", "").lower()
    text = " ".join(elem.itertext())
    tokens = re.findall(r"\b\w+\b", text)
    reference_map[block_id] = tokens

print(f" Loaded reference XML with {len(reference_map)} blocks")
print("📌 Sample reference block IDs:", list(reference_map.keys())[:5])

# === Compare OCR stanza order with canonical reference ===
def normalize_token(token):
    return re.sub(r"[^\w]", "", token.lower())

permutations_by_block = defaultdict(list)
comparison_rows = []

groups = df.groupby(["manuscript_id", "block_id"])
skipped_blocks = 0
printed = 0

for (ms_id, block_id), group in groups:
    if block_id not in reference_map:
        skipped_blocks += 1
        if skipped_blocks <= 10:
            print(f" Skipping unknown block_id in XML: {block_id}")
        continue

    ocr_tokens = [normalize_token(t) for t in group["ocr_word"].dropna().astype(str)]
    ref_tokens = [normalize_token(t) for t in reference_map[block_id]]

    if not ocr_tokens or not ref_tokens:
        continue

    if set(ocr_tokens) == set(ref_tokens) and ocr_tokens != ref_tokens:
        permutations_by_block[block_id].append(ms_id)
        comparison_rows.append({
            "block_id": block_id,
            "manuscript_id": ms_id,
            "ocr_tokens": " ".join(ocr_tokens),
            "reference_tokens": " ".join(ref_tokens),
            "permutation_detected": True
        })

        if printed < 5:
            print(f"\n🔀 Permutation detected in block {block_id} / MS {ms_id}")
            print("OCR     :", ocr_tokens)
            print("Ref     :", ref_tokens)
            printed += 1

if not permutations_by_block:
    print(" No permutations detected after comparison.")

# === Rank permutation blocks ===
ranked_data = []
for block_id, mss in permutations_by_block.items():
    ranked_data.append({
        "block_id": block_id,
        "num_manuscripts": len(set(mss)),
        "manuscripts": ", ".join(sorted(set(mss)))
    })

ranked_df = pd.DataFrame(ranked_data)
if not ranked_df.empty:
    ranked_df = ranked_df.sort_values(by=["num_manuscripts", "block_id"], ascending=[False, True])
    ranked_df.to_csv(RANKED_OUTPUT, index=False)
    print(f"\n Permutation ranking saved to: {RANKED_OUTPUT}")
else:
    print("\n No permutation blocks detected — output file not written.")

# === Write detailed comparison table ===
comparison_df = pd.DataFrame(comparison_rows)
if not comparison_df.empty:
    comparison_df.to_csv(COMPARISON_OUTPUT, index=False)
    print(f"📋 Detailed comparisons saved to: {COMPARISON_OUTPUT}")
else:
    print(" No detailed comparisons found.")
