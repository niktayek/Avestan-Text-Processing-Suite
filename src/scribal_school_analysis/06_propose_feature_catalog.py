import pandas as pd
import os
from collections import defaultdict

from .config import OUTPUT_DIR

FREQUENCY_MATRIX_PATH = os.path.join(OUTPUT_DIR, "frequency_matrix.csv")
SCRIBAL_SCHOOL_ASSIGNMENT_PATH = "data/CAB/Yasna/scribal-school-assignment.csv"
QUANTITATIVE_FEATURE_CATALOG_PATH = os.path.join(OUTPUT_DIR, "quantitative_feature_catalog.csv")
QUALITATIVE_FEATURE_CATALOG_PATH = os.path.join(OUTPUT_DIR, "qualitative_feature_catalog.csv")

def main():
    frequency_matrix = pd.read_csv(FREQUENCY_MATRIX_PATH, index_col='manuscript', dtype={'manuscript': str})
    scribal_school_assignment = read_scribal_school_assignment(SCRIBAL_SCHOOL_ASSIGNMENT_PATH)

    quantitative_feature_catalog = create_quantitative_feature_catalog(scribal_school_assignment, frequency_matrix)
    quantitative_feature_catalog.to_csv(QUANTITATIVE_FEATURE_CATALOG_PATH)

    qualitative_feature_catalog = create_qualitative_feature_catalog(quantitative_feature_catalog)
    qualitative_feature_catalog.to_csv(QUALITATIVE_FEATURE_CATALOG_PATH)

def create_quantitative_feature_catalog(scribal_school_assignment: dict[str, list[str]], frequency_matrix: pd.DataFrame) -> pd.DataFrame:
    schools = set()
    for manuscript, schools_list in scribal_school_assignment.items():
        schools.update(schools_list)

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
    return feature_catalog

def create_qualitative_feature_catalog(quantitative_feature_catalog):
    feature_catalog = pd.DataFrame(
        index=quantitative_feature_catalog.index,
        columns=quantitative_feature_catalog.columns,
        dtype=str,
    )

    quantitative_feature_catalog = quantitative_feature_catalog.div(quantitative_feature_catalog.sum(axis=1), axis=0)

    feature_catalog = quantitative_feature_catalog.map(
        lambda prob:
            "absent" if prob == 0 else
            "rare" if prob < 0.1 else
            "common" if prob < 0.5 else
            "frequent" if prob < 0.9 else
            "very frequent"
    )

    return feature_catalog

def read_scribal_school_assignment(file_path) -> dict[str, list[str]]:
    scribal_school_assignment = pd.read_csv(SCRIBAL_SCHOOL_ASSIGNMENT_PATH, dtype=str)
    assignment = defaultdict(list)
    for _, row in scribal_school_assignment.iterrows():
        manuscript = row['manuscript']
        schools = row['scribal_school'].split(',')
        for school in schools:
            assignment[manuscript].append(school.strip())
    return assignment

if __name__ == "__main__":
    main()
