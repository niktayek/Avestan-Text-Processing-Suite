# src — Avestan OCR & Analysis Toolkit

Python modules for the end-to-end Avestan OCR workflow: image/OCR helpers, token matching, feature/Leitfehler analysis, and scribal-school exploration. Each module can run on its own; together they form the research pipeline.

> For model training & OCR setup, see `../applying_ocr/README.md`
> or the Hugging Face card: **avestan-ocr-kraken-v1** — [https://huggingface.co/Nikyek/avestan-ocr-kraken-v1](https://huggingface.co/Nikyek/avestan-ocr-kraken-v1)

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
├─ calculating_distributions.py   # quick stats helpers  (consider renaming)
└─ calculating_percentages.py     # quick stats helpers  (consider renaming)
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
