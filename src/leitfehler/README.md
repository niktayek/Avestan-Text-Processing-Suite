# Leitfehler Detection and Manuscript Relationship Modeling

This module implements a comprehensive system for detecting **Leitfehler** (guiding errors) in Avestan manuscripts, based on comparisons between OCR output and a normalized canonical edition. These errors include **omissions**, **additions**, **substitutions**, and **permutations**, which are then used to model genealogical relationships among manuscripts.

The pipeline combines philological intuition with computational techniques such as block-level comparison, edit-distance alignment, omission matrix generation, and tree construction using Jaccard or frequency-based similarity metrics.

---

##  Goals

- Automatically detect recurring scribal differences in OCR-transcribed Avestan manuscripts.
- Annotate these differences at the block (stanza) and token level.
- Create **omission matrices** to quantify where manuscripts diverge.
- Construct **clustering trees** that hypothesize scribal lineages or transmission patterns.
- Allow philologists to review the most significant errors and use them in manual collation.

---

##  Modules and Key Scripts

###  1. OCR vs Canonical Comparison

These scripts align the OCR output (from Kraken/eScriptorium) to a cleaned canonical edition (usually from CAB), identify mismatches, and classify them by type.

| Script | Description |
|--------|-------------|
| `compare_ids.py` | Compares block IDs (e.g., Y10.4a) between OCR and canonical data and identifies mismatches or missing entries. |
| `compare_tokens.py` | Token-by-token comparison across shared block IDs using Levenshtein similarity and normalization. |
| `compare_tokens_soroush.py`, `compare_tokens_soroush2.py` | Experimental or collaborative versions of token matchers with alternate logic. |
| `checking.py`, `checking_for_Y9-Y12.py` | Validates critical regions (like Yasna 9–12) for stanza alignment errors. |

---

###  2. Error Type Detection

Each category of scribal divergence is handled by its own logic layer. All are designed to be modular and composable.

| Error Type | Scripts |
|------------|---------|
| **Omissions/Additions** | `addition_omission_new.py`, `shared_addition_omission.py`, `shared_omission.py` |
| **Permutations** | `shared_permutation.py` |
| **Substitutions** | `shared_substitution_word_level.py`, `shared_susbtitution_stanza_level.py` |
| **Markup Preprocessing** | `XML_tag_removing_Leitfehler.py` removes layout tags before comparison |

Each outputs line-specific annotations (e.g., `Y11.2a`, token offset 3) and variant statistics.

---

###  3. Omission Matrix Construction

| Script | Description |
|--------|-------------|
| `matrix_builder_no_filtering.py` | Builds binary omission matrices: rows = blocks, columns = manuscripts. |
| `matrix_final.py` | Final matrix builder with additional filters (e.g., substitution-aware omission confirmation). |
| `matrix_tree_Leitfehler_detector.py` | Runs the complete omission + tree construction pipeline with minimal config. |

Matrices are saved in `.csv` and `.json` formats and used downstream for clustering.

---

###  4. Leitfehler Tagging

| Script | Description |
|--------|-------------|
| `tagging_Leitfehler.py` | Tags omission patterns in manuscripts as candidate Leitfehler. |
| `weighted_tagging_Leitfehler.py` | Applies frequency weighting to filter out common or low-discriminative omissions. |

Leitfehler tags can be used for filtering, visualization, or tree bootstrapping.

---

###  5. Tree Construction & Visualization

| Script | Description |
|--------|-------------|
| `Leitfehler_tree_builder.py` | Constructs Newick-style trees from omission matrices. |
| `weighted_tree_builder_Leitfehler.py` | Same as above but supports omission frequency weights. |
| `Jaccard_clustermap.py` | Renders heatmaps and clustering dendrograms using Jaccard distance. |

Outputs include `.nwk` tree files, `.csv` distance matrices, and `.png` plots.

---

###  6. Text Extraction Utilities

| Script | Description |
|--------|-------------|
| `XML_text_exctractor.py`, `XML_text_extractor_1.py` | Extracts canonical blocks/stanzas from CAB XML for use in comparison. |

---

##  Example Outputs

### Omission Matrix

```csv
Block ID, Ms.5, Ms.6, Ms.8, Ms.9
Y10.1a,     0,    1,    0,    1
Y10.2b,     1,    1,    0,    0
Y10.3c,     0,    1,    1,    0
```

### Leitfehler Tree (Newick format)

```
((Ms5:0.2,Ms6:0.2):0.4,(Ms8:0.3,Ms9:0.3):0.3);
```

### Heatmap (Jaccard similarity)

A matrix plotted using `Jaccard_clustermap.py`, showing distance-based clustering of manuscripts.

---

##  Background

Leitfehler (“guiding errors”) are systemic errors or omissions passed down in a group of manuscripts. Their detection helps reconstruct transmission histories and editorial genealogies.

This pipeline blends philological principles with programmatic tooling to scale the detection and analysis of these errors.

---

##  Integration

This module fits into the larger Avestan OCR project:

- **Input**: OCR output (Kraken), canonical text (CAB), aligned tokens (from `dictionary_matcher/`)
- **Output**: Trees, matrices, and tagged omissions for use in clustering or manual edition work
