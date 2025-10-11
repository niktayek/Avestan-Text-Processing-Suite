import csv
import json
import pandas as pd


def memoize(memoize_for_args: list[str]=None):
    def memoizer(func):
        cache = {}

        def memoized(*args, **kwargs):
            if memoize_for_args is None:
                key = (args, frozenset(kwargs.items()))
            else:
                key = tuple(kwargs.get(arg) for arg in memoize_for_args)

            key = json.dumps(key, sort_keys=True)
            if key not in cache:
                cache[key] = func(*args, **kwargs)
            return cache[key]

        return memoized
    return memoizer


def write_csv(data: list[dict], output_file):
    fieldnames = data[0].keys() if data else []

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def read_csv(input_file) -> list[dict]:
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def calculate_similarity_tvd(feature_profile_1: pd.Series, feature_profile_2: pd.Series) -> float:
    """
    Calculate the Total Variation Distance (TVD) between two manuscripts based on their frequency profiles.
    """

    # Normalize frequencies to probabilities
    prob_1 = feature_profile_1 / feature_profile_1.sum()
    prob_2 = feature_profile_2 / feature_profile_2.sum()

    # Calculate Total Variation Distance
    tvd = (prob_1 - prob_2).abs().sum() / 2
    return 1 - tvd


def calculate_similarity_binary_hamming(feature_profile_1: pd.Series, feature_profile_2: pd.Series) -> float:
    """
    Calculate the Hamming distance between two binary feature profiles.
    """

    # Binarize the feature profiles
    binary_1 = (feature_profile_1 > 0).astype(int)
    binary_2 = (feature_profile_2 > 0).astype(int)

    # Calculate Hamming distance
    hamming_distance = (binary_1 != binary_2).mean()
    return 1 - hamming_distance
