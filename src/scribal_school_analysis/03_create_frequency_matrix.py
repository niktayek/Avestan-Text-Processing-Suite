import os
from collections import defaultdict
import pandas as pd
from .config import OUTPUT_DIR

# INPUT
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
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "frequency_matrix.csv")

# Configuration
DROP_DOCUMENTED_FEATURES = False

def main():
    feature_frequencies = {}
    for manuscript_name, file_path in MANUSCRIPT_FEATURES_PATH.items():
        feature_frequencies[manuscript_name] = calculate_feature_frequencies(file_path)

    all_features = set()
    for freq in feature_frequencies.values():
        all_features.update(freq.keys())
    all_features = sorted(all_features)
    
    frequency_matrix = pd.DataFrame(
        {feature: [freq.get(feature, 0) for freq in feature_frequencies.values()] for feature in all_features},
        index=pd.Index(feature_frequencies.keys(), name="manuscript")
    )
    if DROP_DOCUMENTED_FEATURES:
        frequency_matrix = frequency_matrix.div(frequency_matrix.sum(axis=1), axis=0)
        frequency_matrix = frequency_matrix.round(3)
        frequency_matrix = frequency_matrix.transpose()
    frequency_matrix.to_csv(OUTPUT_CSV)

def calculate_feature_frequencies(manuscript_result_csv: str) -> dict:
    df = pd.read_csv(manuscript_result_csv)
    frequencies = defaultdict(int)
    for features in df["features"].dropna().tolist():
        features = eval(features)
        for feature in features:
            if DROP_DOCUMENTED_FEATURES and feature['is_documented']:
                continue
            frequencies[feature['str']] += 1
    return frequencies

if __name__ == "__main__":
    main()
