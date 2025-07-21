import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from collections import defaultdict
from .utils import memoize
from .config import OUTPUT_DIR

FEATURE_CATALOG_CSV = os.path.join(OUTPUT_DIR, "quantitative_feature_catalog.csv")
MANUSCRIPT_PATHS = {
    "0005": os.path.join(OUTPUT_DIR, "0005_matches_with_changes.csv"),
    "0006": os.path.join(OUTPUT_DIR, "0006_matches_with_changes.csv"),
    "0040": os.path.join(OUTPUT_DIR, "0040_matches_with_changes.csv"),
    "0015": os.path.join(OUTPUT_DIR, "0015_matches_with_changes.csv"),
    "0060": os.path.join(OUTPUT_DIR, "0060_matches_with_changes.csv"),
    "0083": os.path.join(OUTPUT_DIR, "0083_matches_with_changes.csv"),
    "0088": os.path.join(OUTPUT_DIR, "0088_matches_with_changes.csv"),
    "0400": os.path.join(OUTPUT_DIR, "0400_matches_with_changes.csv"),
    "0410": os.path.join(OUTPUT_DIR, "0410_matches_with_changes.csv"),
    "0510": os.path.join(OUTPUT_DIR, "0510_matches_with_changes.csv"),
}

def main():
    feature_catalog = pd.read_csv(FEATURE_CATALOG_CSV, index_col='scribal_school', dtype={'scribal_school': str})
    prediction_matrix = create_prediction_matrix(feature_catalog)
    prediction_matrix = prediction_matrix.round(3)
    prediction_matrix.to_csv(os.path.join(OUTPUT_DIR, "scribal_school_prediction_matrix.csv"), index_label='manuscript')
    visualize_predictions(prediction_matrix)

def create_prediction_matrix(feature_catalog: pd.DataFrame) -> pd.DataFrame:
    prediction_matrix = pd.DataFrame(
        index=feature_catalog.index,
        columns=pd.Index(MANUSCRIPT_PATHS.keys(), name='manuscript', dtype=str),
        dtype=float
    )
    prediction_matrix.fillna(0, inplace=True)

    for scribal_school, features in feature_catalog.iterrows():
        scribal_school_feature_profile = features.to_dict()
        for manuscript, path in MANUSCRIPT_PATHS.items():
            manuscript_df = pd.read_csv(path)
            manuscript_feature_profile = create_feature_profile(manuscript_df)

            prediction_matrix.at[scribal_school, manuscript] = calculate_similarity(manuscript_feature_profile, scribal_school_feature_profile)
    return prediction_matrix

def visualize_predictions(prediction_matrix: pd.DataFrame):
    for index in prediction_matrix.index:
        if len(index) > 20:
            prediction_matrix.rename(index={index: f"{index[:20]} ..."}, inplace=True)

    sns.heatmap(prediction_matrix, cmap="viridis", annot=True, linewidths=0.5, cbar_kws={"shrink": .8})
    plt.title("Scribal School Prediction Matrix")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "scribal_school_prediction_heatmap.png"), dpi=300)
    plt.close()

def create_feature_profile(manuscript_df: pd.DataFrame) -> dict[str, int]:
    features = defaultdict(int)
    for _, row in manuscript_df.iterrows():
        if pd.isna(row['changes']):
            continue
        changes = eval(row['changes'])
        for change in changes:
            features[change['str']] += 1
    return features

def calculate_similarity(manuscript_feature_profile: dict[str, int], scribal_school_feature_profile: dict[str, int]) -> float:
    freq_1 = pd.Series(manuscript_feature_profile)
    freq_2 = pd.Series(scribal_school_feature_profile)

    prob_1 = freq_1 / freq_1.sum()
    prob_2 = freq_2 / freq_2.sum()

    tvd = (prob_1 - prob_2).abs().sum() / 2
    return 1 - tvd

if __name__ == "__main__":
    main()
