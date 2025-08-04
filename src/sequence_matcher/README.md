# Sequence Matcher – Avestan OCR Alignment via Dynamic Programming

This module implements a dynamic programming-based sequence alignment tool tailored for comparing OCR output to canonical Avestan text. It refines token-level matching using grapheme-level alignment logic and supports substitution rules, token merging, and normalization.

It complements and enhances the `dictionary_matcher/` by aligning longer sequences (token spans or full blocks) instead of comparing only isolated token pairs.

---

##  Use Cases

- Detect substitution, merge, and insertion errors at the grapheme level
- Handle complex mismatches (e.g., `"frašōtəməm"` ⇄ `"fərəšō. + təməm"`)
- Quantify match accuracy and identify ambiguous alignments
- Generate evaluation tables and export matched sequences

---

##  How It Differs from `dictionary_matcher/`

| Feature                        | `dictionary_matcher/`                       | `sequence_matcher/`                         |
|-------------------------------|---------------------------------------------|---------------------------------------------|
| Match scope                   | Single token at a time                      | Full block-level token sequences            |
| Alignment algorithm           | Rule-based diffs + string comparison        | Dynamic programming + edit distance         |
| Merge/split detection         | Limited                                     | Robust (supports merge/split decisions)     |
| Substitution rules            | Required                                    | Optional (can learn similarity from form)   |
| Confidence scoring            | No                                          | Yes (match scores per alignment)            |
| Intended use                  | Feature tagging, `"x for y"` substitution   | Full block alignment, OCR evaluation        |
| Output format                 | `"x for y"`, token-level diffs              | Aligned sequences + scores + diagnostics    |
| Speed                         | Fast for short text                         | Slightly slower for long spans              |

In short: **use `dictionary_matcher/` for precise tagging and correction**, and **`sequence_matcher/` for high-quality alignment, evaluation, and ambiguous case handling**.

---

##  Pipeline Overview

1. **Load input sequences** (OCR and canonical)
2. **Normalize tokens** using phonological and orthographic rules
3. **Align sequences** using dynamic programming with configurable penalties
4. **Output alignments** as token-level matches, diffs, and match scores

---

##  Module Structure

| Script | Description |
|--------|-------------|
| `matcher.py` | Core sequence alignment engine using Levenshtein-style DP. Handles substitutions, merges, and skips with rule-based normalization. |
| `data_loader.py` | Loads OCR and canonical data from structured CSV or plain text. Tokenizes and maps block IDs. |
| `print_matches.py` | Generates human-readable output of aligned OCR–canonical token pairs, highlighting substitutions, merges, or errors. |
| `analyze.py` | Computes alignment quality statistics, such as match ratios, total substitutions, merges, and unaligned tokens. |
| `config.py` | Stores substitution rules, cost weights (merge, insert, replace), and file paths. |

---

##  Example Workflow

```bash
# 1. Prepare input: OCR and canonical block-aligned texts
# Format: BlockID \t Text per line

# 2. Align sequences
python matcher.py --ocr path/to/ocr.txt --ref path/to/canonical.txt --out res/matches.txt

# 3. Print detailed match results
python print_matches.py --matches res/matches.txt --output res/formatted_output.csv

# 4. Analyze alignment statistics
python analyze.py --matches res/matches.txt
```

---

## Example Output

**Aligned Token Example (CSV):**

| Block ID | OCR Token | Canonical Token | Match Score | Substitutions |
|----------|-----------|-----------------|-------------|----------------|
| Y10.2a   | frašōtəməm | fərəšō. + təməm | 0.84        | ao for a, merge, ō for u |

---

##  Integration

This module can be used to:
- Refine outputs from `dictionary_matcher/`
- Generate token alignments for `Leitfehler` analysis
- Evaluate OCR model quality across blocks
- Aid feature tagging in `scribal_school_analysis`

It is especially effective for handling **merged or split tokens**, which are common in real manuscript OCR outputs.

---

##  Design Highlights

- Supports rule-based normalization (e.g., `š́ == š`, `ō == u`)
- Penalizes insertions/deletions vs. merges differently
- Outputs confidence scores to help select best matches
- Can be used for generating aligned pairs for supervised correction models

---

##  Future Work

- Confidence thresholding for automated filtering
- Integration with spellchecker output evaluation
- Multi-hypothesis alignment with n-best candidates

