import os
import pandas as pd
from .config import OUTPUT_DIR
from .utils import calculate_similarity

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
                calculate_similarity(frequency_matrix.loc[manuscript_1], frequency_matrix.loc[manuscript_2])
            )

    similarity_matrix.to_csv(OUTPUT_CSV, index_label='manuscript')

if __name__ == "__main__":
    main()
