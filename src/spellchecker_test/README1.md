# Spell Checker and OCR Error Simulation for Avestan

This module evaluates and experiments with automatic correction of OCR output from Avestan manuscripts. It includes a **simple spell checker model**, a **normalizer**, and a **noise injection tool** for simulating OCR variation. The main purpose is to test whether common OCR and scribal errors can be detected and corrected using lightweight linguistic models.

---

## Goals

- Simulate OCR-like spelling errors from clean Avestan data
- Normalize OCR outputs based on known rules or character mappings
- Evaluate correction quality against ground truth
- Develop and benchmark small-scale spell checker models

---

## Key Components

### 1. Noise Injection

| Script | Description |
|--------|-------------|
| `noise.py` | Randomly corrupts Avestan tokens by simulating OCR errors, including character substitutions (`k ↔ d`, `m ↔ z`), deletions, insertions, and mismerges. Uses user-defined probabilities and error patterns. |

**Use case**: generate training or evaluation data with realistic "bad OCR" text for use in spell-checker testing.

---

### 2. Normalization

| Script | Description |
|--------|-------------|
| `normalizer.py` | Applies normalization rules to input tokens (e.g., `š́ → š`, `ō → u`, or expansion of abbreviations). May serve as preprocessing before model correction. |

**Note**: These rules are distinct from OCR error patterns — they reflect orthographic variation and target canonical consistency.

---

### 3. Spell Checker Model

| Script | Description |
|--------|-------------|
| `model.py` | Implements a basic spell checker model. Likely a rule-based or edit-distance candidate generator, with potential for integration with language models. Accepts a list of clean canonical tokens and corrects noisy OCR-like input. |

**Planned or implemented features**:
- Edit-distance candidate generation
- Rule-based filtering using substitution rules
- Optional confidence scoring

---

### 4. Evaluation

| Script | Description |
|--------|-------------|
| `evaluate_spellcheck.py` | Compares model output to gold-standard correction targets. Computes accuracy, precision/recall, and optionally confusion matrices or substitution frequencies. |

---

## Example Workflow

```bash
# 1. Inject OCR noise into clean Avestan corpus
python noise.py --input clean.txt --output noisy.txt --rules substitution_rules.csv

# 2. Normalize input before feeding to spell checker (optional)
python normalizer.py --input noisy.txt --output normalized.txt

# 3. Run spell checker model
python model.py --input normalized.txt --output corrected.txt --vocab canonical.txt

# 4. Evaluate results
python evaluate_spellcheck.py --target clean.txt --predicted corrected.txt
