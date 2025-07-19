import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import squareform
from .config import OUTPUT_DIR

SIMILARITY_MATRIX_PATH = os.path.join(OUTPUT_DIR, "similarity_matrix.csv")
CLUSTERMAP_OUT = os.path.join(OUTPUT_DIR, "clustermap.png")
TREE_OUT = os.path.join(OUTPUT_DIR, "manuscript_tree.png")

def main():
    similarity_matrix = pd.read_csv(SIMILARITY_MATRIX_PATH, index_col='manuscript', dtype={'manuscript': str})

    generate_clustermap(similarity_matrix)
    generate_hierarchical_tree(similarity_matrix)

def generate_clustermap(similarity_matrix: pd.DataFrame):
    sns.clustermap(similarity_matrix, cmap="viridis", annot=True, linewidths=1)
    plt.title("Manuscript Similarity", pad=100)
    plt.savefig(CLUSTERMAP_OUT, dpi=300)
    plt.close()

def generate_hierarchical_tree(similarity_matrix: pd.DataFrame):
    distance_matrix = 1 - similarity_matrix.values
    condensed_dist = squareform(distance_matrix)
    linkage_matrix = linkage(condensed_dist, method="average")

    # Plot dendrogram
    plt.figure(figsize=(10, 6))
    dendrogram(linkage_matrix, labels=similarity_matrix.columns, leaf_rotation=90)
    plt.title("Manuscript Relationship Tree")
    plt.ylabel("Distance")
    plt.tight_layout()
    plt.savefig(TREE_OUT, dpi=300)
    plt.close()

if __name__ == "__main__":
    main()
