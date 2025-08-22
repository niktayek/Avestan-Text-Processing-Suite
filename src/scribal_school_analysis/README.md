# Feature Analyzer — Scribal School Analysis
**Overview**

This project implements a modular pipeline for computational analysis of Avestan manuscripts. It aligns OCR-generated or manually transliterated text to a canonical reference at the token level, detects grapheme-level substitutions/insertions/deletions, and annotates each change with contextual metadata and a philologically grounded feature catalog.

Per manuscript, the system builds a feature profile. Profiles are aggregated into a frequency (or weighted) matrix across manuscripts. From there, we compute similarities, visualize/clustermap, and support manual scribal-school assignment. Finally, we derive quantitative and qualitative feature catalogs that summarize the typicality of each variant within each school. The pipeline is reproducible, extensible, and designed to support both statistical analysis and traditional philology.


For the latest overview, see the main [README](./README.md#overview).


**Pipeline at a Glance**
```mermaid
graph LR
  classDef invisible fill:transparent,stroke:transparent,opacity:0;

  existing_feature_catalog["Existing Feature Catalog<br/>(previous research)"]

  %% -------- Manuscript X --------
  subgraph "Manuscript X Analysis"
    padX[" "]:::invisible
    generated_X["Generated Text<br/>(OCR / Manual Transliteration)"]
    reference_X["Reference Text<br/>(Canonical Transliteration)"]
    match_tokens_X["Match Tokens<br/>(01_match_tokens-dictionary.py)"]
    detect_features_X["Detect Features<br/>(02_detect_features.py)"]
    tagged_X["Tag / Normalize Changes<br/>(02_detect_features.py)"]

    generated_X --> match_tokens_X
    reference_X --> match_tokens_X
    match_tokens_X --> detect_features_X --> tagged_X
    existing_feature_catalog --> tagged_X
  end

  %% -------- Manuscript Y --------
  subgraph "Manuscript Y Analysis"
    padY[" "]:::invisible
    generated_Y["Generated Text<br/>(OCR / Manual Transliteration)"]
    reference_Y["Reference Text<br/>(Canonical Transliteration)"]
    match_tokens_Y["Match Tokens<br/>(01_match_tokens-dictionary.py)"]
    detect_features_Y["Detect Features<br/>(02_detect_features.py)"]
    tagged_Y["Tag / Normalize Changes<br/>(02_detect_features.py)"]

    generated_Y --> match_tokens_Y
    reference_Y --> match_tokens_Y
    match_tokens_Y --> detect_features_Y --> tagged_Y
    existing_feature_catalog --> tagged_Y
  end

  %% -------- Manuscript Z --------
  subgraph "Manuscript Z Analysis"
    padZ[" "]:::invisible
    generated_Z["Generated Text<br/>(OCR / Manual Transliteration)"]
    reference_Z["Reference Text<br/>(Canonical Transliteration)"]
    match_tokens_Z["Match Tokens<br/>(01_match_tokens-dictionary.py)"]
    detect_features_Z["Detect Features<br/>(02_detect_features.py)"]
    tagged_Z["Tag / Normalize Changes<br/>(02_detect_features.py)"]

    generated_Z --> match_tokens_Z
    reference_Z --> match_tokens_Z
    match_tokens_Z --> detect_features_Z --> tagged_Z
    existing_feature_catalog --> tagged_Z
  end

  %% -------- Scribal School Analysis --------
  subgraph "Scribal School Analysis"
    padS[" "]:::invisible
    freq_matrix["Create Frequency Matrix<br/>(03_create_frequency_matrix.py)"]
    sim_matrix["Create Similarity Matrix + Viz<br/>(04_create_similarity_matrix.py)"]
    assign_schools["Manual Scribal School Assignment"]
    propose_catalog["Propose Feature Catalog<br/>(05_propose_feature_catalog.py)"]
    predict_school["School Prediction (optional)<br/>(06_scribal_school_prediction.py)"]
    quant_catalog["Quantitative Feature Catalog<br/>(CSV)"]
    qual_catalog["Qualitative Feature Catalog<br/>(CSV)"]

    tagged_X --> freq_matrix
    tagged_Y --> freq_matrix
    tagged_Z --> freq_matrix

    freq_matrix --> sim_matrix --> assign_schools --> propose_catalog
    propose_catalog --> quant_catalog
    propose_catalog --> qual_catalog
    freq_matrix --> predict_school
  end

  ```

**Steps**
1) Match Tokens — 01_match_tokens-dictionary.py

Align generated (OCR/manual) vs. reference (canonical) tokens.
Output CSV: generated, reference, distance (Levenshtein), address (JSON).
Unmatched: reference="", distance=1000.

2) Detect & Tag Features — 02_detect_features.py

From matched pairs, derive grapheme insertions / deletions / substitutions, normalize labels, and map to catalog entries.
Adds: changes, comment, is_documented, normalized feature_label.

3) Create Frequency Matrix — 03_create_frequency_matrix.py

Aggregate per manuscript: rows = manuscripts, cols = features, values = counts/weights.

4) Create Similarity Matrix (+ visualization) — 04_create_similarity_matrix.py

Compute pairwise similarity/distance; emit clustermap/dendrogram images.

5) Manual Scribal School Assignment → Catalog — 05_propose_feature_catalog.py

Use matrices + visuals to assign schools (manual). Produce quantitative and qualitative catalogs.

6) (Optional) Scribal School Prediction — 06_scribal_school_prediction.py

Score a new manuscript profile against school catalogs.

| Stage            | Input                            | Output                                   |
| ---------------- | -------------------------------- | ---------------------------------------- |
| Match Tokens     | Generated text, Reference text   | Matched CSV (pairs + distance + address) |
| Detect & Tag     | Matched CSV, Feature catalog     | Tagged CSV (normalized features)         |
| Frequency Matrix | Tagged CSVs                      | Matrix CSV                               |
| Similarity       | Matrix CSV                       | Similarity CSV + dendrogram/clustermap   |
| Catalog          | Tagged CSVs + school assignments | Quant & Qual catalogs (CSV)              |
| Prediction       | Matrix/Catalogs                  | Scores per school (CSV)                  |

**Practical Notes**

Per-tradition configs: feature stoplists / merge rules / normalization.

Unicode normalization (NFC/NFD) to keep edit distance honest.

Inspect block/stanza outliers before downstream steps.

**Limitations**

Alignment errors propagate; review diffs at block/stanza scope.

Catalog coverage is incomplete; expect unmapped/novel features.

Clustering guides; final school assignment is manual.

Use separate rule profiles for variant traditions (Iranian vs. Indian, etc.).