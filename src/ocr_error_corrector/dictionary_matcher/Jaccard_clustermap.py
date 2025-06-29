import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.metrics import jaccard_score
import numpy as np
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import squareform

# === CONFIG ===
MATRIX_PATH = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/yasna_addition_omission_matrix.csv"
JACCARD_OUT_CSV = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/yasna_jaccard_similarity.csv"
CLUSTERMAP_OUT = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/yasna_manuscript_clustermap.png"
TREE_OUTFILE = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/yasna_manuscript_tree.png"

# === Load matrix ===
df = pd.read_csv(MATRIX_PATH)
df_matrix = df.drop(columns=["block_id", "token"])
manuscripts = df_matrix.columns.tolist()

# === Compute Jaccard similarity matrix ===
jac_matrix = np.zeros((len(manuscripts), len(manuscripts)))
for i, m1 in enumerate(manuscripts):
    for j, m2 in enumerate(manuscripts):
        jac_matrix[i, j] = jaccard_score(df_matrix[m1], df_matrix[m2])

jac_df = pd.DataFrame(jac_matrix, index=manuscripts, columns=manuscripts)
jac_df.to_csv(JACCARD_OUT_CSV)
print(f"✅ Jaccard similarity matrix saved to: {JACCARD_OUT_CSV}")

# === Plot clustermap ===
sns.clustermap(jac_df, cmap="viridis", annot=True, linewidths=0.5)
plt.title("Manuscript Similarity (Jaccard Index)", pad=100)
plt.savefig(CLUSTERMAP_OUT, dpi=300)
plt.close()
print(f"📊 Clustermap saved to: {CLUSTERMAP_OUT}")

# === Generate independent manuscript tree ===
# Convert similarity to distance
distance_matrix = 1 - jac_df
condensed_dist = squareform(distance_matrix)

# Hierarchical clustering
linkage_matrix = linkage(condensed_dist, method="average")

# Plot dendrogram
plt.figure(figsize=(10, 6))
dendrogram(linkage_matrix, labels=manuscripts, leaf_rotation=90)
plt.title("Manuscript Relationship Tree (1 - Jaccard Distance)")
plt.ylabel("Distance")
plt.tight_layout()
plt.savefig(TREE_OUTFILE, dpi=300)
plt.close()
print(f"🌳 Tree saved to: {TREE_OUTFILE}")
