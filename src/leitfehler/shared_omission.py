import pandas as pd
from collections import defaultdict
import xml.etree.ElementTree as ET
import re
import ast

# === CONFIG ===
file_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/5,6,8,15,40,400,60,83,88,510,410_tagged.csv"
yasna_reference_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/static_yasna.xml"
ranked_output = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/Updated_for_the_word_order/shared_omission_ranked_blocks.csv"
comparison_output = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/Updated_for_the_word_order/omission_block_comparison.csv"

# === Step 1: Load OCR Data ===
df = pd.read_csv(file_path)
df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
df["manuscript_id"] = df["manuscript_id"].astype(str)

# === Step 2: Extract normalized stanza ID from address ===
df["address_id"] = df["address"].apply(lambda x: eval(x)[0]["id"] if pd.notnull(x) else None)

def normalize_address_id(addr):
    if not isinstance(addr, str):
        return ""
    match = re.match(r"(Y\d+(?:\.\d+)?(?:[A-Za-z]+)?)", addr)
    return match.group(1).lower() if match else addr.lower()

df["normalized_id"] = df["address_id"].apply(normalize_address_id)

# === Step 3: Extract reference blocks from XML ===
def extract_canonical_ids_from_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    reference_map = {}
    for elem in root.iter():
        xml_id = elem.attrib.get("{http://www.w3.org/XML/1998/namespace}id") or elem.attrib.get("xml:id")
        if xml_id:
            text = " ".join(elem.itertext()).strip()
            clean_text = re.sub(r"[.,;:!?()\[\]{}<>]", "", text)
            reference_map[xml_id.lower()] = set(clean_text.split())
    return reference_map

reference_map = extract_canonical_ids_from_xml(yasna_reference_path)
print(f"✅ Parsed {len(reference_map)} reference stanzas from XML.")

# === Step 4: Filter to rows with matching stanza ID ===
df = df[df["normalized_id"].isin(reference_map)]
print(f"✅ Remaining rows with reference: {len(df)}")

# === Step 5: Group OCR words by stanza and manuscript using index from address
ocr_map = defaultdict(lambda: defaultdict(list))  # normalized_id → manuscript_id → list of (index, word)

for _, row in df.iterrows():
    norm_id = row["normalized_id"]
    ms_id = row["manuscript_id"]
    word = str(row["ocr_word"]).strip()

    try:
        address_entry = eval(row["address"])[0]
        index = address_entry.get("index", None)
    except:
        index = None

    if norm_id and word and pd.notna(index):
        ocr_map[norm_id][ms_id].append((int(index), word))

# === Step 6: Detect omissions using word indices
omission_blocks = {}
comparison_rows = []

for norm_id, ms_dict in ocr_map.items():
    reference_words = reference_map.get(norm_id, set())
    for ms_id, words in ms_dict.items():
        ocr_words_sorted = sorted(words, key=lambda x: x[0])  # sort by index
        ocr_word_list = [w for _, w in ocr_words_sorted]
        ocr_word_set = set(ocr_word_list)
        omissions = list(reference_words - ocr_word_set)

        if omissions:
            key = (norm_id, tuple(omissions))
            omission_blocks.setdefault(key, []).append(ms_id)
            comparison_rows.append({
                "block_id": norm_id,
                "manuscript_id": ms_id,
                "omitted_words": " ".join(omissions),
                "reference_words": " ".join(reference_words),
                "ocr_words": " ".join(ocr_word_list)
            })

# === Step 7: Rank and Save Results ===
ranked_omissions = [{
    "block_id": block_id,
    "omitted_words": " ".join(words),
    "num_manuscripts": len(mss),
    "manuscripts": ", ".join(sorted(mss))
} for (block_id, words), mss in omission_blocks.items()]

ranked_df = pd.DataFrame(ranked_omissions)
ranked_df = ranked_df.sort_values(by="num_manuscripts", ascending=False)
ranked_df.to_csv(ranked_output, index=False)

comparison_df = pd.DataFrame(comparison_rows)
comparison_df.to_csv(comparison_output, index=False)

print(f"📦 Omission ranking saved to: {ranked_output}")
print(f"📊 Comparison details saved to: {comparison_output}")
