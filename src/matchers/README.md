# matchers — Token Alignment & Comparison

Utilities for aligning OCR/Generated tokens with a canonical reference, and
deriving change information (substitutions, insertions, deletions). These
matchers are used upstream of feature/Leitfehler analysis and the scribal-school
pipeline.

---

## What’s here

### `dictionary_matcher/`
- **Goal:** high-precision, lexicon/rule-aware token alignment.
- **Good for:** extracting explicit `"x for y"` substitutions; generating
  candidate corrections; producing tidy per-token tables for manual review.
- **Typical outputs:** CSV with columns like  
  `generated, reference, distance, address, changes, comment, is_documented`.

### `sequence_matcher/`
- **Goal:** dynamic-programming alignment at block/line scope.
- **Good for:** handling merges/splits and tougher spans where dictionary
  matching is brittle; producing similarity/score information for each pair.
- **Typical outputs:** aligned pairs with scores and merge/split flags.

---

## Input / Output contract (common)

- **Inputs:** two token streams of the same passage  
  *Generated* (OCR or manual transliteration) vs. *Reference* (canonical).
- **Outputs (CSV):**
  - `generated` – token from generated stream
  - `reference` – best match from reference (empty if none)
  - `distance` – edit distance / score (implementation-specific)
  - `address` – JSON with page/line/token indices
  - Optional: `changes`, `comment`, `is_documented`, merge/split flags

These CSVs feed into `../leitfehler/` and `../scribal_school_analysis/`.

---

## Choosing a matcher

| Need | Use |
|---|---|
| Precise substitution tags, correction candidates | `dictionary_matcher/` |
| Robust alignment across merges/splits or noisy spans | `sequence_matcher/` |
| Best of both | Run `sequence_matcher/` first to align blocks, then pass pairs to `dictionary_matcher/` for fine-grained tagging |

---

## How to run

Each subfolder has its own scripts and CLI options. Open the subfolder README
for commands and examples:

- [`dictionary_matcher/README.md`](./dictionary_matcher/README.md)
- [`sequence_matcher/README.md`](./sequence_matcher/README.md)

> Tip: keep Unicode normalized (NFC/NFD) and use per-tradition configs (rule
> maps, stoplists) so legitimate variants aren’t mislabeled as “errors.”

---
