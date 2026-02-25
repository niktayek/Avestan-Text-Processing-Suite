# Experimental Code - Removed from Thesis Repo

**Date**: February 24, 2026  
**Reason**: This repository now contains only code directly related to the Master's thesis (*Integrating OCR and Automated Apparatus Construction for Avestan Texts*). Experimental work developed during the research process but not included in the final thesis has been archived.

---

## What Was Removed

The following experimental code has been removed from this repository:

### 1. **Jupyter Notebooks** (30+ files)
- Colab notebooks for OCR training
- eScriptorium API integrations
- Colleague-facing tools for CAB researchers
- Network analysis notebooks

**Purpose**: These were created to make OCR accessible to non-technical colleagues at CAB. They were not part of the thesis methodology (which used Makefile-based training in VS Code).

### 2. **Token Matching Experiments** (`src/matchers/`)
- Dictionary matcher
- Sequence matcher
- Spellchecker tests

**Purpose**: Exploratory work for OCR troubleshooting and post-correction. Not included in the final thesis scope.

### 3. **Leitfehler Analysis** (`src/leitfehler/`)
- Omission/addition detection
- Permutation analysis
- Substitution tracking
- Matrix building for manuscript relationships

**Purpose**: Stemmatic analysis tools explored during research but ultimately replaced by the configuration-driven apparatus pipeline in the thesis.

### 4. **Scribal School Analysis** (`src/scribal_school_analysis/`)
- Feature frequency matrices
- Similarity clustering
- Manual school assignment tools
- Feature catalog generation

**Purpose**: Advanced philological analysis explored but not finalized for the thesis. Related to RQ3 (regional traditions) but implemented differently in the final apparatus.

### 5. **Utility Modules** (`src/utils/`)
- Shared helpers for matchers and leitfehler analysis

**Purpose**: Support code for experimental modules above.

---

## Where to Find Archived Code

### Local Backup
All removed code is archived at:
```
~/Desktop/Avestan-Archive-20260224/
```

### Git History
The code exists in git history and can be recovered:
```bash
# View the last version before cleanup
git checkout pre-cleanup-backup-20260224

# Or restore a specific folder
git checkout pre-cleanup-backup-20260224 -- src/leitfehler
```

### Published Companion Repositories
This experimental code now lives in dedicated repositories:
- **[avestan-manuscript-digitization-toolkit](https://github.com/niktayek/avestan-manuscript-digitization-toolkit)**: Jupyter notebooks and Colab workflows for OCR training and manuscript processing
- **[avestan-computational-philology](https://github.com/niktayek/avestan-computational-philology)**: Leitfehler, matchers, and scribal school analysis tools

---

## Thesis Scope (What Remains)

This repository now contains ONLY:

### ✅ OCR Pipeline
- Training workflow (`applying_ocr/Makefile`)
- Image preprocessing (`src/image_processing/`)
- Published model on HuggingFace

### ✅ Critical Apparatus Pipeline
- Witness collation (`apparatus/scripts/tei_build_apparatus.py`)
- Variant classification (`apparatus/scripts/tag_apparatus.py`)
- Configuration-driven decision ladder (YAML policies)
- TEI-encoded output

### ✅ Supporting Infrastructure
- TEI/CAB/eScriptorium interfaces (`src/interfaces/`)
- Documentation and architecture guides

---

## For Reviewers

If you're reviewing this repository for PhD applications or research evaluation:
- The current codebase reflects the **actual thesis contributions**
- Experimental work shows research breadth but was excluded for scope control
- All decisions were made to maintain a coherent narrative aligned with the 4 research questions

---

## Questions?

Contact: niktaayekrang@gmail.com

**Related Repositories**:
- [Avestan OCR Model](https://huggingface.co/Nikyek/avestan-ocr-kraken-v1) - Published model on HuggingFace
- [Avestan Manuscript Digitization Toolkit](https://github.com/niktayek/avestan-manuscript-digitization-toolkit) - Colab notebooks and OCR training workflows
- [Avestan Computational Philology](https://github.com/niktayek/avestan-computational-philology) - Experimental computational philology tools
