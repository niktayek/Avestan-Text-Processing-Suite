# src – Avestan OCR and Scribal Analysis Codebase

This directory contains all source code for the end-to-end analysis of Avestan manuscripts, from raw OCR output through error correction, normalization, and philological analysis.

It includes modules for:

- Preparing training data and processing OCR outputs (Kraken + eScriptorium)
- Translating ALTO XML to CAB-compatible format
- Detecting OCR errors and substitutions using rule-based and DP matchers
- Modeling orthographic and phonological variation across manuscripts
- Performing Leitfehler-based collation and clustering
- Analyzing scribal school distributions based on feature frequencies

---

## 📁 Directory Overview

### `CAB/`
Reads canonical CAB XML format and provides stanza-level and word-level access to transliterations.

### `eScriptorium/`
Parses ALTO XML produced by eScriptorium (both training and OCR output). `ocr_xml.py` reads layout and token info; `ocr_text.py` extracts and cleans the recognized text.

### `preparing_for_OCR/`
Includes image processing scripts (e.g., `mirror.py`) to enhance OCR quality by correcting input image orientation and other visual preprocessing tasks.

### `XML_cleaning/`
Handles common structural issues in XML files. `fix_broken_XMLs.py` repairs malformed XML, `text_to_clean_text.py` strips metadata for plain-text comparison, and `XML_id_normalizer.py` harmonizes stanza/block IDs across datasets.

### `xml_translator/`
Maps ALTO OCR output into CAB XML format. Includes alignment routines (`matcher.py`) and `generate_new_xml.py` to reconstruct normalized XML using CAB-compatible tags.

---

### `dictionary_matcher/`
Rule-based matcher for detecting and correcting substitutions in OCR output using a substitution dictionary. Includes:

- `matcher.py`, `matcher_utils.py`: token-level alignment logic
- `filling_changes/`: extraction of `"x for y"` substitutions
- `replacer/`: automatic correction and transformation
- `xml_to_csv.py`, `csv_to_json.py`: conversion utilities

### `sequence_matcher/`
Improved grapheme-level matcher using dynamic programming. Aligns OCR tokens to canonical forms, handles merged or split tokens, and computes edit distances while applying substitution rules.

- `matcher.py`: core DP alignment
- `print_matches.py`: outputs detailed match results
- `res/`: sample results or intermediate match data

### `spellchecker_test/`
Experimental module for spell-checking and OCR noise simulation.

- `noise.py`: injects realistic OCR-like variation
- `normalizer.py`: canonical form prediction
- `evaluate_spellcheck.py`: accuracy metrics
- `model.py`: custom lightweight spell checker architecture

---

### `Leitfehler/`
Scripts for detecting systematic additions, omissions, and substitutions across manuscripts. Includes tools for generating:

- Omission matrices (`build_leitfehler_matrix.py`)
- Tree-based clustering (`Leitfehler_tree_builder.py`)
- Weighted tagging (`weighted_tagging_Leitfehler.py`)
- Permutation and substitution statistics

Also contains comparative analysis tools like `compare_ids.py`, `compare_tokens.py`, and multiple shared scripts for reuse across comparison levels.

---

### `scribal_school_analysis/`
Core logic for identifying scribal schools based on orthographic/phonological features.

- `01_match_tokens-dictionary.py`: matches OCR to canonical forms
- `02_detect_features.py`: applies feature rules (e.g., `ō for u`, `š́ for š`)
- `03_create_frequency_matrix.py`: computes token-level feature distributions
- `04_create_similarity_matrix.py`: builds Jaccard/feature similarity matrices
- `05_propose_feature_catalog.py`: supports normalization of feature labels
- `06_scribal_school_prediction.py`: attempts classification or clustering

Also includes `example_results/`, `utils.py`, and `Overview.md` to document workflow.

---

### `Calculating_distributions_percentages/`
Statistical scripts for aggregating feature counts and computing feature frequency distributions across manuscripts.

- `calculationg_distributions.py`: raw counts
- `calculationg_percentages.py`: relative percentages for normalized comparison

---

## 🧩 Related Information

- All modules assume manuscript data from the **CAB project** and **OCR output from Kraken/eScriptorium**
- For training workflows and OCR model setup, refer to the parent `README.md` or `Avestan-OCR-Training` repo
- Each module can be run independently on its component data (e.g., XML input, tagged token lists, alignment CSVs)

---

## 🧠 Credits & Usage

This codebase was developed as part of a larger MA thesis and ongoing research into Avestan OCR post-processing, scribal variation analysis, and philological manuscript collation. For academic use or collaboration inquiries, please contact the repository owner.
