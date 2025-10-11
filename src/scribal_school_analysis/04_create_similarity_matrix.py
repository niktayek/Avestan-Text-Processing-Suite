import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import squareform
from .config import OUTPUT_DIR
from .utils import calculate_similarity_tvd

# INPUT
FREQUENCY_MATRIX_CSV = os.path.join(OUTPUT_DIR, "frequency_matrix.csv")

# OUTPUT
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "manuscript_similarity_matrix.csv")
CLUSTERMAP_OUT = os.path.join(OUTPUT_DIR, "manuscript_clustermap.png")
TREE_OUT = os.path.join(OUTPUT_DIR, "manuscript_tree.png")

def main():
    frequency_matrix = pd.read_csv(FREQUENCY_MATRIX_CSV, index_col='manuscript', dtype={'manuscript': str})

    similarity_matrix = calculate_similarity_matrix(frequency_matrix)
    similarity_matrix.to_csv(OUTPUT_CSV, index_label='manuscript')

    generate_clustermap(similarity_matrix)
    generate_hierarchical_tree(similarity_matrix)

def calculate_similarity_matrix(frequency_matrix: pd.DataFrame) -> pd.DataFrame:
    manuscripts = frequency_matrix.index.tolist()
    similarity_matrix = pd.DataFrame(
        index=pd.Index(manuscripts, name="manuscript"),
        columns=manuscripts,
        dtype=float,
    )
    similarity_matrix.index = similarity_matrix.index.astype(str)
    for manuscript_1 in manuscripts:
        for manuscript_2 in manuscripts:
            similarity_matrix.at[manuscript_1, manuscript_2] = (
                1.0 if manuscript_1 == manuscript_2 else
                calculate_similarity_tvd(frequency_matrix.loc[manuscript_1], frequency_matrix.loc[manuscript_2])
            )
    return similarity_matrix

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
