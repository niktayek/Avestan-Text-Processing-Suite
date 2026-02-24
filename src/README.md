# src — Avestan Thesis Code

Core Python modules for the Master's thesis: OCR preprocessing, TEI apparatus construction, and external tool interfaces.

> For OCR model training, see `../applying_ocr/README.md`  
> Published model: **avestan-ocr-kraken-v1** — [https://huggingface.co/Nikyek/avestan-ocr-kraken-v1](https://huggingface.co/Nikyek/avestan-ocr-kraken-v1)

---

## Directory Structure

```
src/
├─ image_processing/            # Pre-OCR image preprocessing
│  └─ mirror.py                 # Image mirroring for Persian manuscript layout
│
├─ interfaces/                  # External tool integrations
│  ├─ cab/                      # CAB (Corpus Avesticum Berolinense) XML readers
│  ├─ escriptorium/             # eScriptorium OCR platform API
│  └─ xml_translator/           # TEI apparatus builder & variant classifier
│     ├─ tei_build_apparatus.py     # Extract collation from witnesses
│     ├─ tei_annotate_v3_direct.py  # Classification logic (decision ladder)
│     └─ verify_rules.py            # Rule validation utility
│
└─ tools/                       # Command-line utilities
```

---

## Pipeline Overview

**OCR Pipeline:**
1. Image preprocessing (`image_processing/mirror.py` for right-to-left manuscripts)
2. Model training via `../applying_ocr/Makefile` (Kraken framework)
3. Inference through eScriptorium (`interfaces/escriptorium/`)

**Apparatus Pipeline:**
1. Read witness transcriptions from CAB XML (`interfaces/cab/`)
2. Build collation (`xml_translator/tei_build_apparatus.py`)
3. Classify variants (`xml_translator/tei_annotate_v3_direct.py`)
4. Output TEI-encoded critical apparatus with @type annotations

---

## Quick Start

```bash
# From repository root
poetry install

# Run apparatus pipeline (requires witness data)
poetry run python apparatus/scripts/tei_build_apparatus.py --help
poetry run python apparatus/scripts/tag_apparatus.py --help
```

See `../apparatus/README.md` for complete apparatus pipeline documentation.

---

## Directory map (what lives here)

```
src/
├─ image_processing/            # pre/post OCR image helpers (tiling/cropping, cleanup)
│  └─ mirror.py                 # simple image mirroring/augmentation utility
├─ interfaces/                  # shared types & I/O schemas
│  ├─ cab/                      # CAB XML adapters / helpers
│  ├─ escriptorium/             # eScriptorium/ALTO interfaces
│  └─ xml_translator/           # converters / serialization helpers
├─ leitfehler/                  # additions/omissions/permutations/substitutions pipelines
├─ matchers/                    # token alignment strategies
│  ├─ dictionary_matcher/       # rule/lexicon-aware matcher (precise “x for y” tags)
│  ├─ sequence_matcher/         # DP alignment across lines/blocks (merges/splits)
│  └─ spellchecker_test/        # experimental noise/normalization + simple checker
├─ calculating_distributions.py   # quick stats helpers  (consider renaming)
└─ calculating_percentages.py     # quick stats helpers  (consider renaming)
├─ scribal_school_analysis/     # feature aggregation, similarity, clustering, catalogs
│  ├─ example_results/          # sample outputs
│  ├─ res/                      # resources (feature lists, etc.)
│  ├─ 01_match_tokens-dictionary.py
│  ├─ 02_detect_features.py
│  ├─ 03_create_frequency_matrix.py
│  ├─ 04_create_similarity_matrix.py
│  ├─ 05_propose_feature_catalog.py
│  ├─ 06_scribal_school_prediction.py
│  ├─ config.py  ·  utils.py  ·  README.md  ·  Overview.md
├─ utils/                       # shared helpers (Unicode, I/O, logging, parsing)

```

---

## How the pieces fit

* **OCR → Tokens:** `../applying_ocr/` produces ALTO/CAB; adapters in `interfaces/` read them.
* **Alignment:** `matchers/sequence_matcher` for robust block/line alignment; optionally pass pairs to `matchers/dictionary_matcher` for precise substitution/insert/delete tags and candidate corrections.
* **Features / Leitfehler:** outputs flow into `leitfehler/` to build omission/weighted matrices.
* **Scribal schools:** matrices → `scribal_school_analysis/` (similarity, dendrogram/cluster map, **manual** school assignment, catalogs).
* **(Optional) Spell checking:** `matchers/spellchecker_test/` is an experimental baseline for candidate suggestions (manual review required).

---

## Quick start

```bash
# from repo root
poetry install                 # or: pip install -e .
poetry run python -m pip --version

# examples
poetry run python src/matchers/sequence_matcher/matcher.py --help
poetry run python src/matchers/dictionary_matcher/matcher.py --help
poetry run python src/scribal_school_analysis/03_create_frequency_matrix.py --help
```

Python ≥ 3.10 recommended.

---

## Module notes & docs

* **`matchers/`** — see `matchers/README.md` for when to use dictionary vs. sequence matching.
* **`scribal_school_analysis/`** — overview & diagrams: `scribal_school_analysis/README.md#overview`.
* **`spellchecker_test/`** — experimental; accuracy not tuned; treat as candidate generator with manual review.

---

## Conventions

* Normalize Unicode (NFC/NFD) before matching; combining marks affect edit distance.
* Use per-tradition configs (normalization & substitution rules) to avoid labeling legitimate variants as errors.
* Clustering guides analysis; **scribal-school assignment remains a human, philologically guided decision**.
