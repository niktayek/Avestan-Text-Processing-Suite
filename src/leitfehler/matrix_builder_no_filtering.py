import pandas as pd
import os
import matplotlib.pyplot as plt
import scipy.cluster.hierarchy as sch
from scipy.spatial.distance import pdist, squareform
from sklearn.preprocessing import MultiLabelBinarizer

# === Input files ===
variation_files = [
    "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/shared_omission_ranked_blocks.csv",
    "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/shared_addition_ranked_blocks.csv",
    "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/shared_block_substitution_stanza_level_ranked.csv",
    "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/shared_permutation_ranked_blocks.csv"
]
output_dir = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/tree_matrix_output"
os.makedirs(output_dir, exist_ok=True)

# === Clean manuscript lists ===
def clean_manuscript_list(cell):
    if pd.isna(cell):
        return []
    return [m.strip() for m in str(cell).split(',') if m.strip() and m.strip().lower() not in {"nan", "none"}]

# === Merge blocks from all files ===
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

merged_df = pd.DataFrame(all_blocks)

# === Binary matrix: manuscripts × block_ids ===
mlb = MultiLabelBinarizer()
binary_matrix = pd.DataFrame(
    mlb.fit_transform(merged_df['manuscripts']),
    columns=mlb.classes_,
    index=merged_df['block_id']
).T

binary_matrix_path = os.path.join(output_dir, "manuscript_block_matrix.csv")
binary_matrix.to_csv(binary_matrix_path)
print(f"✅ Merged binary matrix saved to: {binary_matrix_path}")

# === Jaccard distance matrix ===
jaccard_distances = pdist(binary_matrix.values, metric='jaccard')
distance_matrix = pd.DataFrame(
    squareform(jaccard_distances),
    index=binary_matrix.index,
    columns=binary_matrix.index
)

jaccard_path = os.path.join(output_dir, "jaccard_distance_matrix.csv")
distance_matrix.to_csv(jaccard_path)
print(f"📏 Jaccard distance matrix saved to: {jaccard_path}")

# === Dendrogram (Left-to-Right with Proper Axes) ===
plt.figure(figsize=(10, 6))
linkage = sch.linkage(jaccard_distances, method='average')
sch.dendrogram(
    linkage,
    labels=binary_matrix.index.tolist(),
    orientation='left',
    leaf_font_size=10
)

plt.gca().yaxis.tick_left()       # manuscript labels on left
plt.gca().invert_xaxis()          # Jaccard axis grows left-to-right ✅

plt.title("Manuscript Similarity Based on All Leitfehler Types")
plt.xlabel("Jaccard Distance")
plt.ylabel("Manuscripts")
plt.tight_layout()

dendrogram_path = os.path.join(output_dir, "manuscript_dendrogram_no_filtering.png")
plt.savefig(dendrogram_path)
plt.close()

print(f"🌳 Dendrogram saved to: {dendrogram_path}")
