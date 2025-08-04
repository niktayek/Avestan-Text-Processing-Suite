import pandas as pd
import os
import matplotlib.pyplot as plt
import scipy.cluster.hierarchy as sch
from scipy.spatial.distance import pdist, squareform
from sklearn.preprocessing import MultiLabelBinarizer
import unicodedata
import re

# === File paths ===
base_dir = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res"
output_dir = f"{base_dir}/tree_matrix_output"
os.makedirs(output_dir, exist_ok=True)

variation_files = [
    f"{base_dir}/shared_omission_ranked_blocks.csv",
    f"{base_dir}/shared_addition_ranked_blocks.csv",
    f"{base_dir}/shared_block_substitution_stanza_level_ranked.csv",
    f"{base_dir}/shared_permutation_ranked_blocks.csv"
]

comparison_files = {
    "omission": f"{base_dir}/omission_block_comparison.csv",
    "addition": f"{base_dir}/addition_block_comparison.csv",
    "substitution": f"{base_dir}/block_level_substitution_stanza_level_comparison.csv",
    "permutation": f"{base_dir}/permutation_block_comparison.csv",
}

# === Helpers ===
def normalize(text):
    return unicodedata.normalize("NFC", str(text).strip().lower())

def normalize_address_id(addr):
    if not isinstance(addr, str):
        return ""
    match = re.match(r"(y\d+(?:\.\d+)?(?:[a-z]+)?)", addr.lower())
    return match.group(1) if match else addr.lower()

def clean_manuscript_list(cell):
    if pd.isna(cell):
        return []
    return [m.strip() for m in str(cell).split(',') if m.strip() and m.strip().lower() not in {"nan", "none"}]

# === Load variation blocks ===
all_blocks = []
for path in variation_files:
    if not os.path.exists(path):
        print(f"⚠️ File not found, skipping: {path}")
        continue
    df = pd.read_csv(path)
    if 'block_id' not in df.columns or 'manuscripts' not in df.columns:
        print(f"⚠️ Invalid file skipped: {path}")
        continue
    df['manuscripts'] = df['manuscripts'].apply(clean_manuscript_list)
    for _, row in df.iterrows():
        all_blocks.append({'block_id': row['block_id'], 'manuscripts': row['manuscripts']})

# === Filter Leitfehler shared by 2–10 manuscripts ===
filtered_blocks = [block for block in all_blocks if 2 <= len(block['manuscripts']) <= 10]
merged_df = pd.DataFrame(filtered_blocks)

# === Binary matrix: manuscripts × block_ids ===
mlb = MultiLabelBinarizer()
binary_matrix = pd.DataFrame(
    mlb.fit_transform(merged_df['manuscripts']),
    columns=mlb.classes_,
    index=merged_df['block_id']
).T

binary_matrix_path = os.path.join(output_dir, "manuscript_block_matrix_filtered.csv")
binary_matrix.to_csv(binary_matrix_path)
print(f"✅ Filtered binary matrix saved to: {binary_matrix_path}")

# === Jaccard distance matrix ===
jaccard_distances = pdist(binary_matrix.values, metric='jaccard')
distance_matrix = pd.DataFrame(
    squareform(jaccard_distances),
    index=binary_matrix.index,
    columns=binary_matrix.index
)

jaccard_path = os.path.join(output_dir, "jaccard_distance_matrix_filtered.csv")
distance_matrix.to_csv(jaccard_path)
print(f"📏 Jaccard distance matrix saved to: {jaccard_path}")

# === Dendrogram ===
plt.figure(figsize=(10, 6))
linkage = sch.linkage(jaccard_distances, method='average')
sch.dendrogram(
    linkage,
    labels=binary_matrix.index.tolist(),
    orientation='left',
    leaf_font_size=10
)
plt.gca().yaxis.tick_left()
plt.gca().invert_xaxis()
plt.title("Manuscript Clustering Based on Shared Leitfehler (2–10 Manuscripts)")
plt.xlabel("Jaccard Distance")
plt.ylabel("Manuscripts")
plt.tight_layout()

dendrogram_path = os.path.join(output_dir, "manuscript_dendrogram_filtered.png")
plt.savefig(dendrogram_path)
plt.close()
print(f"🌳 Dendrogram saved to: {dendrogram_path}")

# === Build type and description lookup ===
def build_type_lookup():
    lookup = {}
    for type_name, path in comparison_files.items():
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            block_id = normalize(row.get("block_id", ""))
            if type_name == "substitution":
                desc = f"{normalize(row.get('ocr_text', ''))} → {normalize(row.get('canonical_text', ''))}"
            elif type_name == "addition":
                desc = normalize(row.get("added_words", ""))
            elif type_name == "omission":
                desc = f"MISSING: {normalize(row.get('omitted_words', ''))}"
            elif type_name == "permutation":
                desc = normalize(row.get("permuted", "true"))
            else:
                desc = ""

            full_id = f"{block_id} | {desc}"
            lookup[full_id] = {
                "type": type_name,
                "block_id": block_id,
                "description": desc
            }
            lookup[block_id] = lookup[full_id]  # fallback match by bare ID
    return lookup

type_lookup = build_type_lookup()

# === Long-form table from binary matrix ===
presence_table = (
    binary_matrix
    .stack()
    .reset_index()
    .rename(columns={binary_matrix.index.name or "level_0": "manuscript_id", binary_matrix.columns.name or "level_1": "leitfehler_id", 0: "present"})
)
presence_table = presence_table[presence_table["present"] == 1].drop(columns=["present"])

# === Enrich with metadata ===
def resolve_field(lf_id, field):
    lf_id = normalize(lf_id)
    if lf_id in type_lookup:
        return type_lookup[lf_id].get(field, "❌ ERROR")
    parent = normalize_address_id(lf_id)
    if parent in type_lookup:
        return type_lookup[parent].get(field, "❔ APPROX")
    return "❌ ERROR"

presence_table["type"] = presence_table["leitfehler_id"].apply(lambda x: resolve_field(x, "type"))
presence_table["description"] = presence_table["leitfehler_id"].apply(lambda x: resolve_field(x, "description"))
presence_table["block_id"] = presence_table["leitfehler_id"].apply(lambda x: resolve_field(x, "block_id"))

# === Group and save ===
leitfehler_groups = presence_table.groupby("leitfehler_id")["manuscript_id"].apply(list).reset_index()
leitfehler_groups["num_mss"] = leitfehler_groups["manuscript_id"].apply(len)
leitfehler_groups["block_id"] = leitfehler_groups["leitfehler_id"].apply(lambda x: resolve_field(x, "block_id"))
leitfehler_groups["description"] = leitfehler_groups["leitfehler_id"].apply(lambda x: resolve_field(x, "description"))
leitfehler_groups["type"] = leitfehler_groups["leitfehler_id"].apply(lambda x: resolve_field(x, "type"))

errors = leitfehler_groups[leitfehler_groups["type"] == "❌ ERROR"]
if not errors.empty:
    print("❗ WARNING: Unresolved Leitfehler IDs found!")
    print(errors.head())
    raise ValueError("❌ Some Leitfehler IDs could not be resolved.")

leitfehler_groups = leitfehler_groups[["leitfehler_id", "block_id", "description", "type", "manuscript_id", "num_mss"]]
leitfehler_groups = leitfehler_groups.sort_values(by="num_mss", ascending=False)
leitfehler_path = os.path.join(output_dir, "leitfehler_enriched.csv")
leitfehler_groups.to_csv(leitfehler_path, index=False)
print(f"📦 Leitfehler metadata saved to: {leitfehler_path}")
