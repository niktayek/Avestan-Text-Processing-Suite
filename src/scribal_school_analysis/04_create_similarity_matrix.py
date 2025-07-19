import os
import pandas as pd
from .config import OUTPUT_DIR

FREQUENCY_MATRIX_CSV = os.path.join(OUTPUT_DIR, "frequency_matrix.csv")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "similarity_matrix.csv")

def main():
    frequency_matrix = pd.read_csv(FREQUENCY_MATRIX_CSV, index_col='manuscript', dtype={'manuscript': str})

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
                calculate_similarity(manuscript_1, manuscript_2, frequency_matrix)
            )

    similarity_matrix.to_csv(OUTPUT_CSV, index_label='manuscript')

def calculate_similarity(manuscript_1: str, manuscript_2: str, frequency_matrix: pd.DataFrame) -> float:
    """
    Calculate the Total Variation Distance (TVD) between two manuscripts based on their frequency profiles.
    """
    freq_1 = frequency_matrix.loc[manuscript_1]
    freq_2 = frequency_matrix.loc[manuscript_2]

    # Normalize frequencies to probabilities
    prob_1 = freq_1 / freq_1.sum()
    prob_2 = freq_2 / freq_2.sum()
    # Calculate Total Variation Distance
    tvd = (prob_1 - prob_2).abs().sum() / 2
    return 1 - tvd

if __name__ == "__main__":
    main()
