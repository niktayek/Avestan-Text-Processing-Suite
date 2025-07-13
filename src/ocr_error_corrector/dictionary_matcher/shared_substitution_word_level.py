import pandas as pd
from collections import defaultdict
import re

# === CONFIG ===
TAGGED_FILE = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/5,6,8,15,40,400,60,83,88,510,410_tagged.csv"
RANKED_OUTPUT = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/shared_substitution_word_level_ranked_blocks.csv"
COMPARISON_OUTPUT = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/substitution_block_comparison.csv"

# === Step 1: Load tagged substitution data ===
df = pd.read_csv(TAGGED_FILE)
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
df["manuscript_id"] = df["manuscript_id"].astype(str)

# === Step 2: Normalize stanza ID if block_id is missing ===
if "block_id" not in df.columns:
    print("⚠️ 'block_id' column missing — deriving from 'address' or 'address_id'")


    def extract_block_id(addr):
        if not isinstance(addr, str):
            return ""
        match = re.match(r"(Y\d+(?:\.\d+)?(?:[A-Za-z]+)?)", addr)
        return match.group(1).lower() if match else addr.lower()


    if "address_id" in df.columns:
        df["block_id"] = df["address_id"].apply(extract_block_id)
    elif "address" in df.columns:
        df["block_id"] = df["address"].apply(lambda x: eval(x)[0]["id"] if pd.notnull(x) else "")
        df["block_id"] = df["block_id"].apply(extract_block_id)
    else:
        raise ValueError("Cannot derive block_id — neither 'block_id', 'address_id' nor 'address' found.")

# === Step 3: Filter for actual substitutions (non-empty changes) ===
substitutions_df = df[df["the_change"].notna() & (df["the_change"].str.strip() != "")]

# === Step 4: Group by (block_id, the_change) → list of manuscripts ===
substitution_blocks = defaultdict(list)
comparison_rows = []

for _, row in substitutions_df.iterrows():
    block_id = row["block_id"]
    ms_id = row["manuscript_id"]
    change = row["the_change"].strip()

    key = (block_id, change)
    substitution_blocks[key].append(ms_id)

    comparison_rows.append({
        "block_id": block_id,
        "manuscript_id": ms_id,
        "ocr_word": row["ocr_word"],
        "manual_word": row["manual_word"],
        "the_change": change,
        "tag": row.get("tag", "")
    })

# === Step 5: Save ranked shared substitutions ===
ranked_data = [{
    "block_id": block_id,
    "substitution": change,
    "num_manuscripts": len(set(mss)),
    "manuscripts": ", ".join(sorted(set(mss)))
} for (block_id, change), mss in substitution_blocks.items()]

ranked_df = pd.DataFrame(ranked_data)
ranked_df = ranked_df.sort_values(by=["num_manuscripts", "block_id"], ascending=[False, True])
ranked_df.to_csv(RANKED_OUTPUT, index=False)

# === Step 6: Save full comparison table ===
comparison_df = pd.DataFrame(comparison_rows)
comparison_df.to_csv(COMPARISON_OUTPUT, index=False)

print(f"✅ Substitution ranking saved to: {RANKED_OUTPUT}")
print(f"📋 Substitution comparison saved to: {COMPARISON_OUTPUT}")