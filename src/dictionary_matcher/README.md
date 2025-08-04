# Dictionary-Based Substitution Detection and OCR Error Correction

This module implements a substitution-aware sequence alignment system designed for comparing OCR output from Avestan manuscripts to canonical forms. It identifies regular variation patterns, tags them (e.g., `"ō for u"`, `"a inserted"`), and supports both linguistic feature analysis and automated error correction.

It includes:
- A rule-based token matcher
- A change extraction system for `"x for y"` substitutions
- Correction generators based on canonical/OCR alignment
- Format converters (CSV, JSON, XML)
- Configurable post-processing tools

---

##  Core Use Cases

- Detect and tag orthographic and phonological substitutions in OCR output
- Convert alignment diffs into interpretable `"x for y"` changes
- Create feature-tagged datasets for scribal analysis
- Train or test spell checkers and normalizers
- Generate auto-corrections for integration with eScriptorium or CAB

---

## 📂 Module Structure

### 1.  Token Matching and Alignment

| Script | Description |
|--------|-------------|
| `matcher.py` | Core grapheme-level aligner. Aligns OCR tokens to canonical tokens using edit distance with equivalence rules (e.g., `ō == u`). |
| `matcher_utils.py` | Includes normalization, equivalence class handling, and token preprocessing. |
| `config.py` | Paths to substitution rule files, token lists, and alignment parameters. |
| `trie_differ.py` | Experimental fuzzy matcher using trie-based structure for approximate word suggestions. |

### 2.  Filling the Changes (`filling_changes/`)

This component converts aligned OCR/manual token pairs into `"x for y"`-style diffs, with linguistic tagging.

| Script | Description |
|--------|-------------|
| `filling_changes.py` | Extracts granular changes (`inserted`, `deleted`, `substituted`) from character-level diffs between matched tokens. |
| `filling_changes_with_tagging.py` | Adds orthographic/phonological labels based on substitution rules (e.g., `š́ for š`, `ao for a`). |
| `XML_tags_cleaning_for_fiiling_changes.py` | Preprocessing tool that removes XML markup and normalizes text for fair comparison. |

**Output format:**

```csv
OCR Token, Canonical Token, Change Type, Tag
frašōtəməm, fərəšō. + təməm, substitution + merge, ao for a; merge; ō for u
```

### 3.  Correction Generator (`replacer/`)

These tools suggest replacements based on known mappings and aligned pairs.

| Script | Description |
|--------|-------------|
| `replacer.py` | Applies substitution rules to OCR tokens to suggest canonical-normalized forms. |
| `replace_word_generator.py` | Builds word-level replacement candidates from alignment and applies them for automated post-processing. |

### 4.  Format Conversion

| Script | Description |
|--------|-------------|
| `xml_to_csv.py` | Converts block-token data from XML to CSV for alignment. |
| `csv_to_json.py` / `json_to_csv.py` | Interchange utilities between JSON and CSV. |

### 5.  Result Analysis and Statistics

| Script | Description |
|--------|-------------|
| `analyze_matches.py` | Quantifies how many tokens were matched, substituted, inserted, or deleted. |
| `classify_matches.py` | Classifies change types and links them to rule-based tags. |
| `utils.py` | Shared helper functions (I/O, cleaning, etc.). |

Intermediate results are saved to the `res/` directory.

---

##  Example Workflow

```bash
# 1. Convert input
python xml_to_csv.py --ocr path/to/ocr.xml --canonical path/to/canonical.xml

# 2. Match tokens
python matcher.py --ocr_csv res/ocr.csv --canonical_csv res/canonical.csv --output res/matches.csv

# 3. Extract and tag substitutions
python filling_changes_with_tagging.py --matches res/matches.csv --rules substitution_rules.csv

# 4. Generate auto-corrections
python replace_word_generator.py --input res/matches.csv --output res/corrections.csv
```

---

##  Notes

- Substitution rules are customizable in a CSV format and support many-to-many mappings.
- Designed to integrate upstream with Kraken/eScriptorium and downstream with scribal school or Leitfehler analysis.
- Token merge thresholds and equivalence classes are controlled via `config.py`.

---

##  Research Context

This module provides the computational backbone for a broader study of scribal variation in Avestan manuscripts. Its goal is not just to "correct" OCR output, but to preserve and highlight meaningful variation — whether due to dialectal influence, recitation patterns, or historical orthography.

Substitution tagging feeds directly into:
- **Leitfehler detection** (via aligned variants)
- **Scribal school classification** (via normalized feature frequency)
- **OCR correction and evaluation** (via filtered substitution models)

---

## 📬 Contact

For usage questions or to report issues, please contact the repository maintainer at [your GitHub profile/email].