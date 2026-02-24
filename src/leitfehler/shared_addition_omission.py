import pandas as pd
from collections import defaultdict
import xml.etree.ElementTree as ET
import re

# === CONFIG ===
file_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/5,6,8,15,40,400,60,83,88,510,410_tagged.csv"
yasna_reference_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/static_yasna.xml"

# Output files
omission_ranked = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/Updated_for_the_word_order/shared_omission_ranked_blocks.csv"
omission_comparison = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/Updated_for_the_word_order/omission_block_comparison.csv"
addition_ranked = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/Updated_for_the_word_order/shared_addition_ranked_blocks.csv"
addition_comparison = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/Updated_for_the_word_order/addition_block_comparison.csv"
long_format_output = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/Updated_for_the_word_order/word_level_comparison_long_format.csv"

# === Step 1: Load and clean OCR data ===
df = pd.read_csv(file_path)
df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
df["manuscript_id"] = df["manuscript_id"].astype(str)

# === Step 2: Normalize address IDs ===
df["address_id"] = df["address"].apply(lambda x: eval(x)[0]["id"] if pd.notnull(x) else None)

def normalize_address_id(addr):
    if not isinstance(addr, str):
        return ""
    match = re.match(r"(Y\d+(?:\.\d+)?(?:[A-Za-z]+)?)", addr)
    return match.group(1).lower() if match else addr.lower()

df["normalized_id"] = df["address_id"].apply(normalize_address_id)

# === Step 3: Word normalization ===
def normalize_word(word):
    substitutions = {
        "ϑ": "t", "š́": "š", "ā̊": "ā", "xᵛ": "x",
        "δ": "d", "ŋᵛ": "ŋ", "ə̄": "ē", "ą̊": "ą"
    }
    for old, new in substitutions.items():
        word = word.replace(old, new)
    return word

# === Step 4: Extract reference map from XML ===
def extract_reference_map(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    ref_map = {}
    for elem in root.iter():
        xml_id = elem.attrib.get("{http://www.w3.org/XML/1998/namespace}id") or elem.attrib.get("xml:id")
        if xml_id:
            text = " ".join(elem.itertext()).strip()
            clean_text = re.sub(r"[.,;:!?()\[\]{}<>]", "", text)
            ref_map[xml_id.lower()] = [normalize_word(w) for w in clean_text.split()]
    return ref_map

reference_map = extract_reference_map(yasna_reference_path)
print(f" Parsed {len(reference_map)} reference stanzas from XML.")

# === Step 5: Filter to blocks with reference ===
df = df[df["normalized_id"].isin(reference_map)]
print(f" Filtered to {len(df)} rows with reference matches.")

# === Step 6: Group OCR words by stanza and manuscript using index ===
ocr_map = defaultdict(lambda: defaultdict(list))
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
        ocr_map[norm_id][ms_id].append((int(index), normalize_word(word)))

# === Step 7: Compare OCR with reference (detect both omissions and additions) ===
omission_blocks, addition_blocks = {}, {}
omission_rows, addition_rows = [], []
long_format_rows = []

for norm_id, ms_dict in ocr_map.items():
    ref_words = reference_map.get(norm_id, [])
    ref_set = set(ref_words)

    for ms_id, word_pairs in ms_dict.items():
        sorted_words = sorted(word_pairs, key=lambda x: x[0])
        ocr_words = [w for _, w in sorted_words]
        ocr_set = set(ocr_words)

        omissions = list(ref_set - ocr_set)
        additions = list(ocr_set - ref_set)

        if omissions:
            key = (norm_id, tuple(sorted(omissions)))
            omission_blocks.setdefault(key, []).append(ms_id)
            omission_rows.append({
                "block_id": norm_id,
                "manuscript_id": ms_id,
                "omitted_words": " ".join(omissions),
                "reference_words": " ".join(ref_words),
                "ocr_words": " ".join(ocr_words)
            })
            for word in omissions:
                idx = ref_words.index(word) if word in ref_words else None
                context = " ".join(ref_words[max(0, idx-2):idx+3]) if idx is not None else ""
                long_format_rows.append({
                    "block_id": norm_id,
                    "manuscript_id": ms_id,
                    "word_type": "omission",
                    "word": word,
                    "position": idx,
                    "reference_context": context,
                    "ocr_context": ""
                })

        if additions:
            key = (norm_id, tuple(sorted(additions)))
            addition_blocks.setdefault(key, []).append(ms_id)
            addition_rows.append({
                "block_id": norm_id,
                "manuscript_id": ms_id,
                "added_words": " ".join(additions),
                "reference_words": " ".join(ref_words),
                "ocr_words": " ".join(ocr_words)
            })
            for word in additions:
                idx = ocr_words.index(word) if word in ocr_words else None
                context = " ".join(ocr_words[max(0, idx-2):idx+3]) if idx is not None else ""
                long_format_rows.append({
                    "block_id": norm_id,
                    "manuscript_id": ms_id,
                    "word_type": "addition",
                    "word": word,
                    "position": idx,
                    "ocr_context": context,
                    "reference_context": ""
                })

# === Step 8: Save omission and addition outputs ===
pd.DataFrame([{
    "block_id": block_id,
    "omitted_words": " ".join(words),
    "num_manuscripts": len(mss),
    "manuscripts": ", ".join(sorted(mss))
} for (block_id, words), mss in omission_blocks.items()]).sort_values(by="num_manuscripts", ascending=False).to_csv(omission_ranked, index=False)
pd.DataFrame(omission_rows).to_csv(omission_comparison, index=False)

pd.DataFrame([{
    "block_id": block_id,
    "added_words": " ".join(words),
    "num_manuscripts": len(mss),
    "manuscripts": ", ".join(sorted(mss))
} for (block_id, words), mss in addition_blocks.items()]).sort_values(by="num_manuscripts", ascending=False).to_csv(addition_ranked, index=False)
pd.DataFrame(addition_rows).to_csv(addition_comparison, index=False)

# === Step 9: Save long-format output ===
pd.DataFrame(long_format_rows).to_csv(long_format_output, index=False)
print(f"📦 Omission saved to: {omission_ranked}")
print(f"📦 Addition saved to: {addition_ranked}")
print(f" Long-format saved to: {long_format_output}")
