import pandas as pd
import re
from matcher import match_sequences

# === CONFIG ===
canon_txt = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/static_yasna.txt"
ocr_txt = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/0005.txt"
output_file = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/blockwise_match_output.csv"

# === HELPERS ===
def tokenize(text):
    text = text.strip().replace("⸳", ".").replace("⁛", "")
    text = re.sub(r"[.\s]+", " ", text)
    return text.split()

def load_txt_blocks(path):
    blocks = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if "\t" not in line:
                continue
            block_id, text = line.strip().split("\t", 1)
            blocks[block_id] = {
                "text": text,
                "tokens": tokenize(text)
            }
    return blocks

# === MAIN ===
canon_blocks = load_txt_blocks(canon_txt)
ocr_blocks = load_txt_blocks(ocr_txt)

results = []
ocr_matched = set()

for cid, cdata in canon_blocks.items():
    best_score = 0
    best_match_id = None
    best_match_result = []

    for vid, vdata in ocr_blocks.items():
        if vid in ocr_matched:
            continue
        pairs = match_sequences(cdata["tokens"], vdata["tokens"], threshold=0.85)
        score = len(pairs) / max(len(cdata["tokens"]), 1)
        if score > best_score:
            best_score = score
            best_match_id = vid
            best_match_result = pairs

    if best_score >= 0.9:
        ocr_matched.add(best_match_id)
        results.append({
            "block_id": cid,
            "match_type": "match",
            "score": round(best_score, 3),
            "canon_text": canon_blocks[cid]["text"],
            "ocr_text": ocr_blocks[best_match_id]["text"]
        })
    elif best_score >= 0.5:
        ocr_matched.add(best_match_id)
        results.append({
            "block_id": cid,
            "match_type": "weak_match",
            "score": round(best_score, 3),
            "canon_text": canon_blocks[cid]["text"],
            "ocr_text": ocr_blocks[best_match_id]["text"]
        })
    else:
        results.append({
            "block_id": cid,
            "match_type": "omission",
            "score": round(best_score, 3),
            "canon_text": canon_blocks[cid]["text"],
            "ocr_text": ""
        })

# Unmatched OCR blocks → additions
for vid, vdata in ocr_blocks.items():
    if vid not in ocr_matched:
        results.append({
            "block_id": vid,
            "match_type": "addition",
            "score": 0.0,
            "canon_text": "",
            "ocr_text": vdata["text"]
        })

# === SAVE ===
df = pd.DataFrame(results)
df.to_csv(output_file, index=False)
print(f" Done. Output saved to: {output_file}")
