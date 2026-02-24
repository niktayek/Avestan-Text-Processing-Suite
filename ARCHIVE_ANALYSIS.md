# Archive Analysis: AvestanOCR & OCR Download Folders

**Analysis Date**: February 24, 2026  
**Analyst**: GitHub Copilot  
**Purpose**: Identify unique, non-repetitive materials from thesis work-in-progress folders suitable for publication/archival

---

## Executive Summary

After analyzing `/Users/niktayekrangsafakar/Downloads/AvestanOCR` and `/Users/niktayekrangsafakar/Downloads/OCR`, I found several categories of materials that are either:
1. **Unique** (not in main repo)
2. **Updated versions** (differ from main repo versions)
3. **Experimental/deprecated** (valuable for archival but not production use)

### Critical Findings

✅ **39 trained OCR models** (.mlmodel files) - **UNIQUE & VALUABLE**  
⚠️ **All leitfehler & scribal_school scripts** - exist in main repo but **DIFFER** (possible updates/fixes)  
✅ **Full eScriptorium deployment** - complete Docker setup for local OCR infrastructure  
✅ **Unique preprocessing scripts** - image manipulation, multi-OCR comparison, transliteration  
⚠️ **Processed manuscript data** - large image/text datasets (may contain copyrighted material)

---

## Detailed Inventory

### 1. Trained OCR Models (39 files) - **HIGH PRIORITY**

**Location**: `/Users/niktayekrangsafakar/Downloads/AvestanOCR/models_on_eScriptorium/`

**Models Found**:
- **Manuscript-specific recognition models**: 0040, 0088, 0089, 0090, 0091, 0093, 2000, 4030, 4210, TD2, lb2
- **Segmentation models**: Multiple versions (seg1, seg2, seg4, seg7)
- **Special purpose**: Pash_Ant.mlmodel, kraken_trained_on_sephardi.mlmodel
- **Mirrored variants**: Models trained on flipped images (Persian manuscripts read right-to-left)

**Status**: ✅ **NOT in main repository** - These are experimental/intermediate models from your training process

**Value**:
- Research transparency: Shows model iteration/evolution
- Comparative analysis: Different models for different manuscript families
- Reusability: Others working on similar scripts (Pahlavi, Sogdian) could fine-tune these
- Academic credibility: Demonstrates extensive experimentation

**Recommendation**: 
- **Create separate repository**: "avestan-ocr-model-zoo" or "avestan-ocr-experiments"
- **Include README** documenting: which manuscript each model was trained on, accuracy metrics, training date, intended use
- **License**: CC-BY or similar (academic use)
- **Link from main repo** as "experimental models"

---

### 2. Unique Preprocessing Scripts - **MEDIUM PRIORITY**

**Location**: `/Users/niktayekrangsafakar/Downloads/AvestanOCR/src/`

**Scripts Found** (not in main repo):
1. **Binarization.py** - Image binarization for OCR preprocessing
2. **Line_to_character.py** - Segmentation refinement
3. **Prase_XML.py** [Parse_XML] - XML parsing utilities
4. **grayscale.py / grayscale_0040.py** - Manuscript-specific grayscale conversion
5. **manually_cutting.py** - Interactive image segmentation tool
6. **multi_ocr.py** - **NOTABLE**: Compares multiple OCR engines (Tesseract, Kraken, Google Cloud Vision)
7. **noise_reduction.py** - Manuscript image denoising
8. **ocr_transliterate.py** - Avestan ↔ Latin transliteration with ligature handling

**Status**: ✅ **NOT in main repository**

**Value**:
- **multi_ocr.py**: Shows you compared commercial (Google Vision) vs. open-source (Kraken) - valuable methodological transparency
- **Image preprocessing pipeline**: Could help others working with degraded manuscripts
- **Transliteration mapping**: Complete Avestan ↔ Latin character mapping with special ligatures

**Recommendation**:
- **Add to main repo** under `src/experimental/` or `src/preprocessing/`
- **Document limitations**: Some scripts have hardcoded paths (e.g., Windows paths in multi_ocr.py line 10)
- **Note dependencies**: multi_ocr.py requires Google Cloud credentials (paid API)

---

### 3. eScriptorium Full Deployment - **ARCHIVAL VALUE**

**Location**: `/Users/niktayekrangsafakar/Downloads/AvestanOCR/ocr/escriptorium/`

**Contents**: Complete eScriptorium installation with:
- Docker configuration (docker-compose.yml)
- Django application code
- Database migrations
- nginx/prometheus monitoring setup
- GitLab CI/CD pipeline

**Status**: ⚠️ This is the **official eScriptorium project** (not your code) - appears to be a cloned/forked installation

**Value**:
- Shows you set up local OCR infrastructure (not just used cloud services)
- Demonstrates technical capability (Docker, Django, deployment)
- Could be useful if you made custom modifications to eScriptorium

**Recommendation**:
- **DO NOT republish** the entire eScriptorium codebase (copyright issue)
- **Document your setup** instead: Create `ESCRIPTORIUM_SETUP.md` documenting:
  - Installation steps you followed
  - Custom configurations you made
  - Integration with your Kraken models
  - Lessons learned / troubleshooting tips
- **Check for modifications**: If you customized eScriptorium code, extract ONLY your changes as patches

---

### 4. Leitfehler & Scribal School Analysis - **VERSION COMPARISON NEEDED**

**Location**: `/Users/niktayekrangsafakar/Downloads/OCR/src/leitfehler/` and `scribal_school_analysis/`

**Status**: ⚠️ **ALL files exist in main repo but DIFFER**

**Files Affected** (24+ scripts):
- addition_omission_new.py
- leitfehler_detector.py
- matrix_builder_no_filtering.py
- weighted_tree_builder_leitfehler.py
- scribal_school_analysis/01_match_tokens-dictionary.py through 06_scribal_school_prediction.py
- ...and many more

**Possible Reasons for Differences**:
1. Bug fixes / improvements made after thesis submission
2. Experimental features that didn't make it into thesis
3. Code refactoring (same logic, different style)
4. Path updates (hardcoded paths fixed)

**Recommendation**: ⚠️ **REQUIRES MANUAL REVIEW**

**Action Items**:
1. **Compare specific files** to determine nature of changes:
   ```bash
   diff /path/to/main/repo/file.py /path/to/downloads/file.py | less
   ```
2. **Identify improvements**: Cherry-pick bug fixes or enhancements
3. **Discard deprecated code**: If downloads version is older/worse, ignore it
4. **Document divergence**: If downloads folder has experimental features, document why they weren't included

**I can help with this if you tell me which files are most critical to compare.**

---

### 5. Processed Manuscript Data - **COPYRIGHT SENSITIVE**

**Location**: `/Users/niktayekrangsafakar/Downloads/AvestanOCR/data/`

**Contents**:
- Processed images for manuscripts: 0015, 0088, 0089, 0090, 0091, 0093, 0120, 2030, 4210
- Text outputs: OCR results, cleaned transcriptions
- Special collections: Patet_Irani_Antia, Videvdad, Visperad
- JSON metadata: matches.json

**Status**: ⚠️ **Large datasets with potential copyright issues**

**Value**:
- **Ground truth data**: OCR training/testing annotations
- **Intermediate outputs**: Shows processing pipeline stages
- **Diverse text types**: Beyond Yasna (Videvdad, Visperad, Patet Irani)

**Recommendation**: ⚠️ **PROCEED CAREFULLY**

**Options**:
1. **Contact copyright holders** (manuscript libraries) for permission to share processed data
2. **Share only metadata** (file lists, statistics) not actual images/text
3. **Create sample subset** (5-10 lines) for demonstration purposes under fair use
4. **Document data sources** in README without redistributing

---

### 6. Documentation & Miscellaneous

**Files**:
- `Background check of the Avestan.odt` - ODT document (not readable as text)
- Text files: `0015_based on_0090.txt`, `2030_cleaned.txt`, etc.
- `static_yasna.xml` - Appears to be a reference text

**Status**: ⚠️ **Unclear without opening ODT file**

**Recommendation**:
- **Open the ODT** manually to see if it contains:
  - Research notes worth converting to Markdown
  - Literature review / bibliography
  - Methodology documentation
  - Meeting notes / supervisor feedback
- If valuable, **convert to Markdown** and add to main repo docs/

---

## Proposed Repository Structure

Based on this analysis, I recommend creating **2-3 new repositories**:

### Option A: Conservative (2 repos)

```
1. Avestan-Text-Processing-Suite (main repo - KEEP AS IS)
   ├─ Core apparatus + OCR pipelines (current state)
   
2. avestan-ocr-experiments (NEW)
   ├─ models/ (39 .mlmodel files)
   ├─ preprocessing/ (unique scripts from AvestanOCR/src)
   ├─ evaluation/ (comparison studies, if any)
   └─ README.md (documents each model, training date, metrics)
```

### Option B: Comprehensive (3 repos)

```
1. Avestan-Text-Processing-Suite (main repo - ENHANCED)
   ├─ Add "experimental" preprocessing scripts
   ├─ Add ESCRIPTORIUM_SETUP.md
   ├─ Link to other repos in README
   
2. avestan-ocr-model-zoo (NEW)
   ├─ published_models/
   │   └─ avestan-ocr-kraken-v1/ (Hugging Face mirror)
   ├─ experimental_models/
   │   ├─ manuscript_specific/ (0040, 0088, etc.)
   │   ├─ segmentation/ (seg models)
   │   └─ transfer_learning/ (Sephardi-based)
   └─ model_cards/ (detailed documentation per model)
   
3. avestan-manuscripts-data-samples (NEW)
   ├─ sample_ground_truth/ (5-10 lines per manuscript)
   ├─ metadata/ (manuscript catalog, statistics)
   └─ README.md (data sources, citation requirements)
```

### Option C: Monorepo with Sub-modules

```
Avestan-Text-Processing-Suite (EXPANDED)
├─ src/ (current code)
├─ models/
│   ├─ production/ (published HF model)
│   └─ experimental/ (39 .mlmodel files)
├─ preprocessing/
│   └─ experimental/ (unique scripts)
├─ data/
│   └─ samples/ (minimal fair-use examples)
└─ docs/
    ├─ ESCRIPTORIUM_SETUP.md
    ├─ MODEL_TRAINING_LOG.md
    └─ DATA_SOURCES.md
```

---

## Recommended Actions (Prioritized)

### Phase 1: High-Value Extraction (Do This First)

1. ✅ **Extract 39 OCR models**
   - Create `avestan-ocr-experiments` repo
   - Add README documenting each model
   - Include training logs/metrics if available
   - License as CC-BY 4.0
   
2. ✅ **Add preprocessing scripts to main repo**
   - Create `src/preprocessing/experimental/`
   - Copy: Binarization.py, multi_ocr.py, ocr_transliterate.py, noise_reduction.py
   - Fix hardcoded paths / add configuration
   - Document Google Cloud Vision as optional dependency

3. ✅ **Document eScriptorium setup**
   - Create `docs/ESCRIPTORIUM_SETUP.md` in main repo
   - Describe installation, configuration, integration
   - Do NOT include eScriptorium source code

### Phase 2: Code Reconciliation (Requires Your Input)

4. ⚠️ **Compare leitfehler & scribal_school_analysis versions**
   - I can help diff specific files
   - Identify which version is "better"
   - Cherry-pick improvements into main repo
   - **I NEED YOUR GUIDANCE**: Which files do you remember making significant changes to?

### Phase 3: Documentation & Data (Low Priority / Optional)

5. ⚠️ **Review ODT document**
   - Open manually
   - Assess if content is worth preserving
   - Convert valuable sections to Markdown

6. ⚠️ **Data samples** (if permitted)
   - Contact manuscript libraries for permission
   - OR create minimal fair-use samples (5-10 lines)
   - Document provenance meticulously

---

## Next Steps - Your Decision

**I need your input on:**

1. **Repository strategy**: Option A (conservative 2 repos), Option B (comprehensive 3 repos), or Option C (expanded monorepo)?

2. **Leitfehler/scribal_school comparison**: Should I diff specific files to find improvements? Which files are most critical?

3. **Model publication priority**: All 39 models, or just the best ones? (I can help identify best based on naming conventions)

4. **Data sharing boundaries**: Are you comfortable sharing ANY processed manuscript data, or strictly code-only?

5. **Timeline**: Is this urgent (PhD applications), or can we work through this methodically over a few sessions?

---

## Technical Notes

- All .mlmodel files are Kraken 4.x/5.x format (compatible with current pipeline)
- eScriptorium deployment appears to be version 0.13.x (circa 2022-2023)
- Multi_ocr.py references Google Cloud Vision API (requires paid credentials)
- Some scripts have Windows path separators (need fixing for cross-platform use)

---

**Analysis complete. Awaiting your decisions on extraction strategy and priorities.**
