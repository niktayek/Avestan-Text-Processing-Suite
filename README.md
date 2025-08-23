# src — Avestan OCR & Analysis Toolkit

Python modules for the Avestan OCR + analysis pipeline: image/OCR helpers, token
matching, feature/Leitfehler analysis, and scribal-school exploration. Each
module can run on its own; together they form the end-to-end workflow.

> For training workflows and OCR model setup, see `../applying_ocr/README.md`
> or the Hugging Face model card:
> **avestan-ocr-kraken-v1** — https://huggingface.co/Nikyek/avestan-ocr-kraken-v1

---

## Directory map

- **image_processing/** — utilities used before/after eScriptorium/Kraken
  (cropping/tiling, cleanup, post-OCR fixes).
- **interfaces/** — shared dataclasses/protocols for consistent I/O and typing.
- **leitfehler/** — detect additions/omissions/permutations/substitutions;
  build omission/weighted matrices; create trees/cluster maps.
- **matchers/** — token alignment strategies:
  - **dictionary_matcher/** – rule/lexicon-aware matcher for precise
    `"x for y"` substitutions, insertions, deletions; good for correction
    candidates and tidy per-token tables.
  - **sequence_matcher/** – dynamic-programming alignment across blocks/lines;
    handles merges/splits and noisy spans; produces scores.
- **scribal_school_analysis/** — aggregate tagged features into
  frequency/similarity matrices; visualize (tree/cluster map); support **manual**
  scribal-school assignment; derive quantitative/qualitative feature catalogs.
- **utils/** — common helpers (Unicode normalization, file I/O, logging, parsing).

Each subfolder has its own README with usage and examples.

---

## Typical flows

- **OCR → tokens:** `../applying_ocr/` → ALTO/XML → `matchers/`
- **Features / Leitfehler:** `matchers/` → `leitfehler/` → matrices & visualizations
- **Scribal schools:** matrices → `scribal_school_analysis/`
  (similarity, clustering, catalogs; manual assignment)

Optional: use `matchers/dictionary_matcher` outputs to propose correction
candidates; review manually before applying.

