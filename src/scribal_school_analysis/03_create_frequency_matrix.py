import os
from collections import defaultdict
import pandas as pd
from .config import OUTPUT_DIR

MANUSCRIPT_RESULT_CSVS = {
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
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "frequency_matrix.csv")
DROP_DOCUMENTED_FEATURES = False

def main():
    change_frequencies = {}
    for manuscript_name, file_path in MANUSCRIPT_RESULT_CSVS.items():
        change_frequencies[manuscript_name] = calculate_change_frequencies(file_path)
    
    all_features = set()
    for freq in change_frequencies.values():
        all_features.update(freq.keys())
    all_features = sorted(all_features)
    
    frequency_matrix = pd.DataFrame(
        {feature: [freq.get(feature, 0) for freq in change_frequencies.values()] for feature in all_features},
        index=pd.Index(change_frequencies.keys(), name="manuscript")
    )
    if DROP_DOCUMENTED_FEATURES:
        frequency_matrix = frequency_matrix.div(frequency_matrix.sum(axis=1), axis=0)
        frequency_matrix = frequency_matrix.round(3)
        frequency_matrix = frequency_matrix.transpose()
    frequency_matrix.to_csv(OUTPUT_CSV)

def calculate_change_frequencies(manuscript_result_csv: str) -> dict:
    df = pd.read_csv(manuscript_result_csv)
    frequencies = defaultdict(int)
    for changes in df["changes"].dropna().tolist():
        changes = eval(changes)
        for change in changes:
            if DROP_DOCUMENTED_FEATURES and change['is_documented']:
                continue
            frequencies[change['str']] += 1
    return frequencies

if __name__ == "__main__":
    main()
