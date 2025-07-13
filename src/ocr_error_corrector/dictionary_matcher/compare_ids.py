import re
import pandas as pd
from Levenshtein import ratio as levenshtein_ratio

# === CONFIG ===
canonical_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/Canonical_Yasna.txt"
variant_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/txt/0005.txt"
substitution_file = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/final_cleaned_rules_ready.csv"
output_csv = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/0005_token_comparison_shared_only.csv"

# === Substitution + Abbreviation Rules ===
def load_substitutions(path):
    df = pd.read_csv(path)
    subs = {(str(row.iloc[0]).strip(), str(row.iloc[1]).strip())
            for _, row in df.iterrows() if row.iloc[0] and row.iloc[1]}
    abbr_rules = {
        "yasnāica.": {"y.", "yas."},
        "vaɱāica.": {"v."},
        "xšnaōϑrāica.": {"x."},
        "frasastaiiaēca.": {"fra.", "f."}
    }
    for full, variants in abbr_rules.items():
        for abbr in variants:
            subs.add((full, abbr))
    return subs

substitutions = load_substitutions(substitution_file)

# === Tokenizer: dot-based word detection
def dot_based_tokenize(text):
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\[[^\]]*\]', '', text)
    text = re.sub(r'[=#≈].*', '', text)
    text = re.sub(r'\s+', '', text)
    return re.findall(r'.+?\.', text)

# === Extract canonical/variant blocks
def extract_blocks(path):
    blocks = {}
    current_id = None
    current_lines = []

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            match = re.search(r'\b(Y\d+(?:\.Ext\d+|\.\d+[a-z]?))\b', line)
            if match:
                if current_id:
                    blocks[current_id] = "".join(current_lines)
                current_id = match.group(1)
                content = line.split(current_id, 1)[1]
                current_lines = [content]
            elif current_id:
                current_lines.append(line)

    if current_id:
        blocks[current_id] = "".join(current_lines)

    return blocks

# === Load block content (as raw strings first)
canon_raw = extract_blocks(canonical_path)
variant_raw = extract_blocks(variant_path)

# Tokenize after loading raw block text
canon_blocks = {bid: dot_based_tokenize(text) for bid, text in canon_raw.items()}
variant_blocks = {bid: dot_based_tokenize(text) for bid, text in variant_raw.items()}

shared_ids = sorted(set(canon_blocks.keys()) & set(variant_blocks.keys()))
print(f"✅ Shared block IDs: {len(shared_ids)}")

records = []
skipped_blocks = 0

for bid in shared_ids:
    canon_tokens = canon_blocks.get(bid, [])
    variant_tokens = variant_blocks.get(bid, [])

    if not canon_tokens or not variant_tokens:
        skipped_blocks += 1
        print(f"⚠️ Skipping {bid}:")
        if not canon_tokens:
            print(f"   🟥 Canonical side is empty")
            print(f"   Raw text: {repr(canon_raw.get(bid, '')[:120])}...")
        if not variant_tokens:
            print(f"   🟦 Variant side is empty")
            print(f"   Raw text: {repr(variant_raw.get(bid, '')[:120])}...")
        continue

    max_len = min(len(canon_tokens), len(variant_tokens))

    for i in range(max_len):
        ctok = canon_tokens[i]
        vtok = variant_tokens[i]

        if ctok == vtok:
            status = "match"
        elif (ctok, vtok) in substitutions:
            status = "substitution (✓)"
        else:
            ratio = levenshtein_ratio(ctok, vtok)
            status = "substitution (?)" if ratio >= 0.75 else "addition/omission"

        records.append({
            "block_id": bid,
            "position": i,
            "canonical_token": ctok,
            "variant_token": vtok,
            "status": status
        })

# === Save result
df = pd.DataFrame(records)
df.to_csv(output_csv, index=False)

# === Summary
print(f"📄 Token comparison complete. Output saved to: {output_csv}")
print(f"🧭 Compared {len(shared_ids) - skipped_blocks} block(s)")
print(f"⚠️ Skipped {skipped_blocks} block(s) due to missing tokens")
