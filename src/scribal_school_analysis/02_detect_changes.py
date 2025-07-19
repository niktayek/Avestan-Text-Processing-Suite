import pandas as pd
import os
import re
import unicodedata
from pathlib import Path
from .config import OUTPUT_DIR
from .utils import memoize
from functools import partial

# INPUT_CSV = os.path.join(OUTPUT_DIR, "matches.csv")
MANUSCRIPT_ID = "0510"  # Example manuscript ID
INPUT_CSV = f"data/CAB/Yasna/{MANUSCRIPT_ID}_matches.csv"
FEATURE_CATALOG_CSV = 'data/CAB/feature_catalog.csv'
OUTPUT_CSV = os.path.join(OUTPUT_DIR, f"{MANUSCRIPT_ID}_matches_with_changes.csv")

############################################################################
# Graphemes for tokenization
############################################################################
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
    df["generated"] = df["generated"].fillna("").astype(str)

    feature_catalog = pd.read_csv(FEATURE_CATALOG_CSV)

    df["changes"] = df.apply(func=detect_changes, axis=1)
    df["features_comment"] = df["changes"].apply(partial(comment_on_changes, feature_catalog=feature_catalog))
    df["features_documented"] = df.apply(
        func=lambda row:
            True if row["features_comment"] else
            False if row["changes"] else
            None,
        axis=1,
    )

    df = df[[col for col in df.columns if col != 'address'] + ['address']]
    df.to_csv(OUTPUT_CSV, index=False)

def detect_changes(row):
    if not row["reference"]:
        return None
    return dp_changes(
        tokenize_graphemes(unicodedata.normalize("NFC", row["reference"])),
        tokenize_graphemes(unicodedata.normalize("NFC", row["generated"])),
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
def dp_changes(reference_tokens: list[str], generated_tokens: list[str]) -> str | None:
    # DP table for minimal edit distance
    m, n = len(reference_tokens), len(generated_tokens)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if reference_tokens[i - 1] == generated_tokens[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],     # delete
                    dp[i][j - 1],     # insert
                    dp[i - 1][j - 1], # substitute
                )

    # Backtrack to get the diff
    i, j = m, n
    changes = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and reference_tokens[i - 1] == generated_tokens[j - 1]:
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or dp[i][j] == dp[i - 1][j] + 1):
            changes.append({"type": "delete", "from": reference_tokens[i - 1], "to": None})
            i -= 1
        elif j > 0 and (i == 0 or dp[i][j] == dp[i][j - 1] + 1):
            changes.append({"type": "insert", "from": None, "to": generated_tokens[j - 1]})
            j -= 1
        else:
            changes.append({"type": "replace", "from": generated_tokens[j - 1], "to": reference_tokens[i - 1]})
            i -= 1
            j -= 1
    changes.reverse()

    changes = [
        f"{change['from']} to {change['to']}" if change['type'] == "replace" else
        f"{change['from']} deleted" if change['type'] == "delete" else
        f"{change['to']} inserted"
        for change in changes
    ]

    return ", ".join(changes) if changes else None

def comment_on_changes(changes: list[dict[str, str]], feature_catalog: pd.DataFrame) -> dict[str, str] | None:
    if not changes:
        return None

    for feature in feature_catalog.itertuples(index=False):
        if re.search(feature.Pattern, changes):
            return feature.Description

if __name__ == "__main__":
    main()
