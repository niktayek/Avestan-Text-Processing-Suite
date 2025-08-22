# Spell Checker and OCR Error Simulation for Avestan

> **Status (experimental / not production-ready)**  
> This is a lightweight pipeline for simulating OCR errors, normalizing tokens, and proposing spell-corrections for Avestan. **Accuracy is currently insufficient for unattended use.** I have **not** spent extensive time tuning or evaluating the model; outputs **require manual review**. Treat this as a **research aid for candidate generation**, not a final corrector.

---

## Overview

This module lets you: (1) inject OCR-like noise into clean Avestan tokens, (2) normalize tokens with rule sets, (3) generate correction candidates with a simple spell-checker baseline, and (4) evaluate against a gold standard. It’s meant to surface likely corrections and quantify error patterns—not to replace expert curation.

---

## Goals

- Simulate OCR-like spelling errors from clean Avestan data.
- Normalize OCR outputs using known orthographic/phonological mappings.
- Evaluate correction quality against a gold reference.
- Prototype simple spell-checker ideas (edit distance + rules).

---

## Intended Use (and Non-Use)

**Use it to:**
- Produce _candidate_ corrections for manual review.
- Explore substitution frequencies and error classes.
- Test normalization rules on small samples.

**Do **not** use it to:**
- Automatically rewrite large corpora without supervision.
- Compare traditions/schools without per-tradition configuration.
- Conflate legitimate scribal/phonological variants with OCR errors.

---

## Key Components

### 1) Noise Injection

| Script | Description |
|---|---|
| `noise.py` | Corrupts clean tokens with OCR-like errors (e.g., substitutions `k↔d`, `m↔z`, insertions/deletions, merges). Uses configurable probabilities and error patterns. |

**Use case:** Create realistic “noisy” text for testing correction/normalization.

### 2) Normalization

| Script | Description |
|---|---|
| `normalizer.py` | Applies rule-based normalization (e.g., `š́→š`, `ō→u`, abbreviation expansion). Targets canonical consistency; distinct from OCR error simulation. |

### 3) Spell Checker (baseline)

| Script | Description |
|---|---|
| `model.py` | Simple baseline (edit-distance candidate generation + rule filtering; optional vocab constraint). Designed for quick experiments, **not** SOTA results. |

**Optional bits (planned/partial):**
- Edit-distance candidates
- Rule-based accept/reject via substitution map
- Optional confidence scoring / ranking

### 4) Evaluation

| Script | Description |
|---|---|
| `evaluate_spellcheck.py` | Compares predictions to gold; reports accuracy and basic stats (precision/recall optional). |

---

## Example Workflow

```bash
# 1) Inject OCR noise into a clean corpus
python noise.py --input clean.txt --output noisy.txt --rules substitution_rules.csv

# 2) Normalize (optional but recommended)
python normalizer.py --input noisy.txt --output normalized.txt --rules normalization_rules.csv

# 3) Run the simple spell checker
python model.py --input normalized.txt --output corrected.txt --vocab canonical.txt --rules substitution_rules.csv

# 4) Evaluate against gold
python evaluate_spellcheck.py --target clean.txt --predicted corrected.txt --report report.json
Tip: Start on a small slice of data (e.g., a subset of stanzas/blocks) to tune thresholds before scaling.

Configuration
substitution_rules.csv: maps noisy→clean characters or grapheme sequences; also used to filter/score candidates.

Keep per-tradition variants in separate profiles if possible (e.g., rules_kerman.csv, rules_yazd.csv).

normalization_rules.csv: orthographic/phonological mappings that should not be treated as errors.

canonical.txt: vocabulary list used for candidate constraints; expanding this reduces over-correction and OOV issues.

Known Limitations & Failure Modes
Legitimate variation ≠ errors. Regular alternations should often be accepted, not “corrected.” Examples you’ll see in Avestan manuscripts:

Vowels: ā ↔ ā̊, epenthetic i, a ↔ ā.

Consonants: t ↔ ϑ, δ ↔ d, variants of š (e.g., š́/ṣ̌/š).

Abbreviations / spacing / dots: e.g., y. for yasnāica, line-break merges/splits, dot misalignment.

OCR-specific confusions (common): k↔d, n↔b/u, m↔z, ϑ↔x, t↔c, plus RTL/transliteration quirks.

Context blindness. Token-level decisions can over-/under-correct without stanza/block context.

Vocabulary coverage. Out-of-vocabulary forms and school-specific variants reduce accuracy.

Parameter sensitivity. Edit-distance thresholds and rule weights strongly affect results; defaults are not tuned.

Practical Tips to Improve (still manual-review first)
Whitelist acceptable alternations (by tradition) so they’re not flagged as errors.

Expand canonical.txt with manuscript-/school-specific forms.

Use context: penalize candidates that break local collocations; prefer those that keep known sequences.

Balance precision/recall: start strict (high precision) to reduce reviewer load; relax later for coverage.

Ablate and report by category: substitutions vs. merges/splits; with vs. without normalization.

Normalize Unicode (NFC/NFD) consistently; combining marks can inflate edit distanc
