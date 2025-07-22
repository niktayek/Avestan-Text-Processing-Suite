import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from collections import defaultdict
from .utils import memoize
from .config import OUTPUT_DIR

# INPUT
FEATURE_CATALOG_CSV = os.path.join(OUTPUT_DIR, "feature_catalog_quantitative.csv")
MANUSCRIPT_FEATURES_PATH = {
    manuscript_id: os.path.join(OUTPUT_DIR, f"{manuscript_id}_features.csv")
    for manuscript_id in [
        "0005",
        "0006",
        "0040",
        "0015",
        "0060",
        "0083",
        "0088",
        "0400",
        "0410",
        "0510",
    ]
}

# OUTPUT
SCRIBAL_SCHOOL_PREDICTION_MATRIX_CSV = os.path.join(OUTPUT_DIR, "scribal_school_prediction_matrix.csv")
SCRIBAL_SCHOOL_PREDICTION_HEATMAP_PNG = os.path.join(OUTPUT_DIR, "scribal_school_prediction_heatmap.png")

def main():
    feature_catalog = pd.read_csv(FEATURE_CATALOG_CSV, index_col='scribal_school', dtype={'scribal_school': str})
    prediction_matrix = create_prediction_matrix(feature_catalog)
    prediction_matrix = prediction_matrix.round(3)
    prediction_matrix.to_csv(SCRIBAL_SCHOOL_PREDICTION_MATRIX_CSV, index_label='manuscript')
    visualize_predictions(prediction_matrix)

def create_prediction_matrix(feature_catalog: pd.DataFrame) -> pd.DataFrame:
    prediction_matrix = pd.DataFrame(
        index=feature_catalog.index,
        columns=pd.Index(MANUSCRIPT_FEATURES_PATH.keys(), name='manuscript', dtype=str),
        dtype=float
    )
    prediction_matrix.fillna(0, inplace=True)

    for scribal_school, features in feature_catalog.iterrows():
        for manuscript, path in MANUSCRIPT_FEATURES_PATH.items():
            manuscript_df = pd.read_csv(path)
            manuscript_feature_profile = create_feature_profile(manuscript_df)

            prediction_matrix.at[scribal_school, manuscript] = calculate_similarity(manuscript_feature_profile, features)
    return prediction_matrix

def visualize_predictions(prediction_matrix: pd.DataFrame):
    for index in prediction_matrix.index:
        if len(index) > 20:
            prediction_matrix.rename(index={index: f"{index[:20]} ..."}, inplace=True)

    sns.heatmap(prediction_matrix, cmap="viridis", annot=True, linewidths=0.5, cbar_kws={"shrink": .8})
    plt.title("Scribal School Prediction Matrix")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(SCRIBAL_SCHOOL_PREDICTION_HEATMAP_PNG, dpi=300)
    plt.close()

def create_feature_profile(manuscript_df: pd.DataFrame) -> pd.Series:
    features_profile = defaultdict(int)
    for _, row in manuscript_df.iterrows():
        if pd.isna(row['features']):
            continue
        features = eval(row['features'])
        for feature in features:
            features_profile[feature['str']] += 1
    features = pd.Series(features_profile)
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
