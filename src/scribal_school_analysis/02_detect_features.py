import pandas as pd
import os
import re
import unicodedata
from pathlib import Path
from .config import OUTPUT_DIR
from .utils import memoize
from functools import partial

MANUSCRIPT_ID = "0510"

# INPUT
INPUT_CSV = f"data/CAB/Yasna/{MANUSCRIPT_ID}_matches.csv"
OLD_FEATURE_CATALOG_PATH = 'data/CAB/feature_catalog.csv'

# OUTPUT
OUTPUT_CSV = os.path.join(OUTPUT_DIR, f"{MANUSCRIPT_ID}_features.csv")

# Configuration
SPECIAL_GRAPHEMES = sorted(
    [
        'ə̄u', 'aō', 'aē', 'āu', 'āi', 'ōi', 'ou', 'ai', 'au',
        'ā̊', 'ą̇', 'ə̄', 't̰', 'x́', 'xᵛ', 'ŋ́', 'ŋᵛ', 'š́', 'ṣ̌', 'ṇ', 'ń', 'ɱ', 'ġ', 'γ', 'δ', 'ẏ', 'č', 'ž', 'β',
        'ā', 'ą', 'ō', 'ē', 'ū', 'ī',
        'a', 'o', 'ə', 'e', 'u', 'i',
        'k', 'x', 'g', 'c', 'j', 't', 'ϑ', 'd', 'p', 'b', 'ŋ', 'n', 'm',
        'y', 'v', 'r', 'l', 's', 'z', 'š', 'h', 'uu', 'ii'
    ],
    key=len,
    reverse=True,
)
SPECIAL_GRAPHEME_RE = re.compile('|'.join(map(re.escape, SPECIAL_GRAPHEMES)))

def main():
    df = pd.read_csv(INPUT_CSV)
    df["reference"] = df["reference"].fillna("").astype(str)
    df["transliterated"] = df["transliterated"].fillna("").astype(str)

    feature_catalog = pd.read_csv(OLD_FEATURE_CATALOG_PATH)

    df["features"] = df.apply(func=detect_changes, axis=1)
    df["features"] = df["features"].apply(partial(attach_feature_metadata, feature_catalog=feature_catalog))

    df = df[[col for col in df.columns if col != 'address'] + ['address']]
    df.to_csv(OUTPUT_CSV, index=False)

def detect_changes(row):
    if not row["reference"]:
        return None
    return dp_features(
        tokenize_graphemes(unicodedata.normalize("NFC", row["reference"])),
        tokenize_graphemes(unicodedata.normalize("NFC", row["transliterated"])),
    )

# @memoize()
def tokenize_graphemes(word: str) -> list[str]:
    tokens = []
    i = 0
    while i < len(word):
        match = SPECIAL_GRAPHEME_RE.match(word, i)
        if match:
            tokens.append(match.group())
            i = match.end()
        else:
            tokens.append(word[i])
            i += 1
    return tokens

# @memoize()
def dp_features(reference_tokens: list[str], transliterated_tokens: list[str]) -> str | None:
    # DP table for minimal edit distance
    m, n = len(reference_tokens), len(transliterated_tokens)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if reference_tokens[i - 1] == transliterated_tokens[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],     # delete
                    dp[i][j - 1],     # insert
                    dp[i - 1][j - 1], # substitute
                )

    # Backtrack to get the diff
    i, j = m, n
    features = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and reference_tokens[i - 1] == transliterated_tokens[j - 1]:
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or dp[i][j] == dp[i - 1][j] + 1):
            features.append({"type": "delete", "from": reference_tokens[i - 1]})
            i -= 1
        elif j > 0 and (i == 0 or dp[i][j] == dp[i][j - 1] + 1):
            features.append({"type": "insert", "to": transliterated_tokens[j - 1]})
            j -= 1
        else:
            features.append({"type": "replace", "from": transliterated_tokens[j - 1], "to": reference_tokens[i - 1]})
            i -= 1
            j -= 1
    features.reverse()

    for feature in features:
        feature['str'] = (
            f"{feature['to']} for {feature['from']}" if feature['type'] == 'replace' else
            f"{feature['to']} inserted" if feature['type'] == 'insert' else
            f"{feature['from']} deleted"
        )

    return features

def attach_feature_metadata(features: list[dict[str, str]], feature_catalog: pd.DataFrame) -> dict[str, str] | None:
    if not features:
        return features

    for feature in features:
        feature_str = (
            f"{feature['from']} for {feature['to']}" if feature['type'] == 'replace' else
            f"{feature['to']} inserted" if feature['type'] == 'insert' else
            f"{feature['from']} deleted"
        )
        feature['is_documented'] = False
        feature['description'] = None
        for cataloged_feature in feature_catalog.itertuples(index=False):
            if re.search(cataloged_feature.Pattern, feature_str):
                feature["description"] = cataloged_feature.Description
                feature["is_documented"] = True
                break
    return features

if __name__ == "__main__":
    manuscript_ids = [
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
    for manuscript_id in manuscript_ids:
        MANUSCRIPT_ID = manuscript_id
        INPUT_CSV = f"data/CAB/Yasna/{MANUSCRIPT_ID}_matches.csv"
        OUTPUT_CSV = os.path.join(OUTPUT_DIR, f"{MANUSCRIPT_ID}_features.csv")
        print(f"Processing manuscript {MANUSCRIPT_ID}...")
        main()
