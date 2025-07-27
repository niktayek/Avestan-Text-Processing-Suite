import pandas as pd
import os
from collections import defaultdict
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import squareform
from .utils import calculate_similarity
from .config import OUTPUT_DIR

# INPUT
FREQUENCY_MATRIX_CSV = os.path.join(OUTPUT_DIR, "frequency_matrix.csv")
SCRIBAL_SCHOOL_ASSIGNMENT_CSV = "data/CAB/Yasna/scribal-school-assignment.csv"

# OUTPUT
QUANTITATIVE_FEATURE_CATALOG_CSV = os.path.join(OUTPUT_DIR, "feature_catalog_quantitative.csv")
QUALITATIVE_FEATURE_CATALOG_CSV = os.path.join(OUTPUT_DIR, "feature_catalog_qualitative.csv")
SCRIBAL_SCHOOL_SIMILARITY_MATRIX_CSV = os.path.join(OUTPUT_DIR, "scribal_school_similarity_matrix.csv")
SCRIBAL_SCHOOL_CLUSTERMAP_PNG = os.path.join(OUTPUT_DIR, "scribal_school_clustermap.png")
SCRIBAL_SCHOOL_TREE_PNG = os.path.join(OUTPUT_DIR, "scribal_school_tree.png")

def main():
    frequency_matrix = pd.read_csv(FREQUENCY_MATRIX_CSV, index_col='manuscript', dtype={'manuscript': str})
    scribal_school_assignment = read_scribal_school_assignment(SCRIBAL_SCHOOL_ASSIGNMENT_CSV)

    quantitative_feature_catalog = create_quantitative_feature_catalog(scribal_school_assignment, frequency_matrix)
    quantitative_feature_catalog.to_csv(QUANTITATIVE_FEATURE_CATALOG_CSV)

    scribal_school_similarity_matrix = produce_similarity_matrix(quantitative_feature_catalog)
    scribal_school_similarity_matrix.to_csv(SCRIBAL_SCHOOL_SIMILARITY_MATRIX_CSV)
    visualize_similarity_matrix(scribal_school_similarity_matrix)

    qualitative_feature_catalog = create_qualitative_feature_catalog(create_quantitative_feature_catalog(scribal_school_assignment, frequency_matrix, False))
    qualitative_feature_catalog.to_csv(QUALITATIVE_FEATURE_CATALOG_CSV)

def create_quantitative_feature_catalog(scribal_school_assignment: dict[str, list[str]], frequency_matrix: pd.DataFrame, normalized: bool = True) -> pd.DataFrame:
    schools = set()
    for manuscript, schools_list in scribal_school_assignment.items():
        schools.update(schools_list)

    if normalized:
        frequency_matrix = frequency_matrix.div(frequency_matrix.sum(axis=1), axis=0)

    feature_catalog = pd.DataFrame(
        index=pd.Index(schools, name='scribal_school', dtype=str),
        columns=frequency_matrix.columns,
        dtype=float,
    )
    feature_catalog = feature_catalog.fillna(0)

    for manuscript, scribal_schools in scribal_school_assignment.items():
        for school in scribal_schools:
            feature_catalog.loc[school] += frequency_matrix.loc[manuscript]
    feature_catalog = feature_catalog.fillna(0)

    if normalized:
        feature_catalog = feature_catalog.div(feature_catalog.sum(axis=1), axis=0)

    return feature_catalog

def produce_similarity_matrix(quantitative_feature_catalog: pd.DataFrame) -> pd.DataFrame:
    similarity_matrix = pd.DataFrame(
        index=quantitative_feature_catalog.index,
        columns=quantitative_feature_catalog.index,
        dtype=float
    )
    for school1 in quantitative_feature_catalog.index:
        for school2 in quantitative_feature_catalog.index:
            if school1 == school2:
                similarity_matrix.at[school1, school2] = 1.0
            else:
                similarity_matrix.at[school1, school2] = calculate_similarity(
                    quantitative_feature_catalog.loc[school1],
                    quantitative_feature_catalog.loc[school2]
                )
    return similarity_matrix

def create_qualitative_feature_catalog(quantitative_feature_catalog) -> pd.DataFrame:
    feature_catalog = pd.DataFrame(
        index=quantitative_feature_catalog.index,
        columns=quantitative_feature_catalog.columns,
        dtype=str,
    )

    def calculate_qualitative(row: pd.Series):
        new_row = {}

        non_rares = row[row > 5].to_dict()
        sorted_row = sorted((prob, feature) for feature, prob in non_rares.items())
        
        ranks = {}
        current_rank = 0
        prev_prob = None
        
        for i, (prob, feature) in enumerate(sorted_row):
            if prob != prev_prob:
                current_rank = i
            ranks[feature] = current_rank
            prev_prob = prob
        
        non_zero_count = len(non_rares)
        sorted_row = pd.Series(ranks).map(
            lambda rank:
                "rare" if rank < non_zero_count * 0.1 else
                "common" if rank < non_zero_count * 0.7 else
                "frequent" if rank < non_zero_count * 0.95 else
                "very frequent"
        ).to_dict()
        new_row.update(sorted_row)

        rares = row[row <= 5].to_dict()
        new_row.update({
            feature: "rare"
            for feature in rares.keys()
        })

        zeros = row[row == 0].to_dict()
        new_row.update({
            feature: "absent"
            for feature in zeros.keys()
        })

        return pd.Series(new_row)

    feature_catalog = quantitative_feature_catalog.apply(calculate_qualitative, axis=1)

    return feature_catalog

def read_scribal_school_assignment(file_path) -> dict[str, list[str]]:
    scribal_school_assignment = pd.read_csv(SCRIBAL_SCHOOL_ASSIGNMENT_CSV, dtype=str)
    assignment = defaultdict(list)
    for _, row in scribal_school_assignment.iterrows():
        manuscript = row['manuscript']
        schools = row['scribal_school'].split(',')
        for school in schools:
            assignment[manuscript].append(school.strip())
    return assignment


def visualize_similarity_matrix(similarity_matrix: pd.DataFrame):
    for index in similarity_matrix.index:
        if len(index) > 20:
            similarity_matrix.rename(index={index: f"{index[:20]} ..."}, inplace=True)
    for column in similarity_matrix.columns:
        if len(column) > 20:
            similarity_matrix.rename(columns={column: f"{column[:20]} ..."}, inplace=True)
    
    generate_clustermap(similarity_matrix)
    generate_hierarchical_tree(similarity_matrix)

def generate_clustermap(similarity_matrix: pd.DataFrame):
    sns.clustermap(similarity_matrix, cmap="viridis", annot=True, linewidths=0.5, cbar_kws={"shrink": .8})
    plt.title("Scribal School Similarity Matrix")
    plt.tight_layout()
    plt.savefig(SCRIBAL_SCHOOL_CLUSTERMAP_PNG, dpi=300)
    plt.close()

def generate_hierarchical_tree(similarity_matrix: pd.DataFrame):
    distance_matrix = 1 - similarity_matrix.values
    condensed_dist = squareform(distance_matrix)
    linkage_matrix = linkage(condensed_dist, method="average")

    # Plot dendrogram
    plt.figure(figsize=(10, 6))
    dendrogram(linkage_matrix, labels=similarity_matrix.columns, leaf_rotation=90)
    plt.title("Scribal School Relationship Tree")
    plt.ylabel("Distance")
    plt.tight_layout()
    plt.savefig(SCRIBAL_SCHOOL_TREE_PNG, dpi=300)
    plt.close()

if __name__ == "__main__":
    main()
