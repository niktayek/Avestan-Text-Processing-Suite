# System Architecture: The Four Research Questions

This document maps the system architecture to the four research questions that frame this thesis and guide its development.

---

## Overview: RQ1 → RQ2 → RQ3 ✓ RQ4

```
RQ1: OCR Pipeline        RQ2: Apparatus Pipeline      RQ3: Pattern Capture      RQ4: Modularity
─────────────────        ───────────────────────      ──────────────────        ──────────────
Images                   Variants                     Region Detection          Config-Driven
├─ Kraken Model          ├─ Decision Ladder           ├─ Orthography Rules      ├─ Each component
├─ Transfer Learning     ├─ 7-Stage Classifier       ├─ Tradition Awareness    │  operates independently
├─ 99.2% Accuracy        ├─ YAML Rules                └─ Iranian vs Indian      ├─ Configuration files
└─ HuggingFace Release   └─ TEI Output                                          └─ Adjustable without code
                                                                                   changes
```

---

## Research Question 1: OCR via Transfer Learning

### The Question
**"Can transfer learning enable high-accuracy OCR for Avestan despite limited training data?"**

### Why It Matters
- Low-resource script with no pre-existing models
- Only ~50 pages of Avestan manuscripts available for training
- Need to demonstrate feasibility for other ancient languages (Pahlavi, Sogdian)

### How It's Answered

**Architecture Component**: `src/interfaces/escriptorium/ + Kraken`

```
Training Data (43 pages)      Kraken CRNN         Trained Model       Release
     ↓                            ↓                     ↓               ↓
CAB/eScriptorium ──→ Hebrew Base ──→ Fine-tune ──→ 99.2% CER ──→ HuggingFace
Ground Truth         (Transfer)       (Iteration)   97% WER        (Public)
```

**Key Components**:
1. **Hebrew proxy**: Started with Hebrew-trained model (structural similarities)
2. **Iterative refinement**: Trained on 43 pages with error feedback loop
3. **Character confidence scores**: Model provides uncertainty estimates for human review
4. **Public release**: Model available on [Hugging Face](https://huggingface.co/Nikyek/avestan-ocr-kraken-v1)

**Validation Metrics**:
- Character Error Rate (CER): 0.8% → 99.2% accuracy
- Word Error Rate (WER): 3% → 97% accuracy
- Comparable to commercial systems on well-supported languages

**Impact**: Demonstrates transfer learning pathway for other ancient scripts; lowers barrier to OCR adoption in digital humanities.

---

## Research Question 2: Variant Classification Rules

### The Question
**"Can philological knowledge be encoded into rules that automatically classify variants as trivial vs. meaningful?"**

### Why It Matters
- Manual variant classification is labor-intensive
- Different regional traditions (Iran vs. India) have different expectations
- Need to distinguish scribal convention from textual corruption
- Scholars need transparent, auditable decision-making

### How It's Answered

**Architecture Component**: `apparatus/scripts/tag_apparatus.py + policies/`

```
Raw Apparatus              Decision Ladder              Tagged Apparatus
(Variant Readings)         (7 Stages)                  (Classified)
     ↓                          ↓                            ↓
<rdg wit="#ms0005">     Stage 1: Empty?          @ana="#readings"
  stōmaine              Stage 2: Normalize       @cert="0.98"
</rdg>      ──────────→ Stage 3: Spacing    ──→ @n="aō→ō"
            (repeat)   Stage 4: Families
<rdg wit="#ms0006">     Stage 5: Consonants
  staōmaine            Stage 6: Length
</rdg>                 Stage 7: YAML Rules
                       [φ none fire → trivial]
```

**Key Components**:

1. **Stage 1–3**: Basic checks (empty, normalization, spacing)
2. **Stage 4**: `orthography_families_v4.yaml` — Character groupings
   - Short vowels: ə/e/i treated as equivalent
   - Diphthongs: aō/ō/ao/o treated as equivalent
   - Consonants: t/ϑ, p/f, etc.

3. **Stage 5–6**: Computational heuristics
   - Consonant skeleton: If ≥80% match, difference is minor
   - Length differential: If <60% or >150%, difference is structural

4. **Stage 7**: `classification_policy.yaml` — Context-sensitive rules
   - Condition: Manuscript tradition (Iranian/Indian) + atomic operation
   - Decision: Trivial, meaningful, or unknown
   - If no rule fires: Default to trivial

**Validation Results (Yasna 9, 14 witnesses)**:
- Total readings: 9,618
- Trivial (88.81%): 8,542 readings
- Meaningful (2.88%): 277 readings
- Missing (8.31%): 799 readings
- Unknown (0%): 0 readings

→ Distribution consistent with liturgical conservatism; rule coverage is sufficient.

**Impact**: Demonstrates that encoding expert knowledge produces reproducible, auditable classification; enables scholars to inspect, critique, and refine rules.

---

## Research Question 3: Regional Pattern Capture

### The Question
**"Can the apparatus pipeline systematically capture regional transmission patterns (Iranian vs. Indian traditions)?"**

### Why It Matters
- Avestan manuscripts split into distinct regional communities
- Each community has systematic orthographic signatures
- Need to recognize these patterns to contextualize variants
- Enables tracing manuscript relationships and transmission history

### How It's Answered

**Architecture Component**: `orthography_families_v4.yaml + classification_policy.yaml`

Martínez Porro's (2020) research identified **systematic orthographic patterns**:

| Pattern | Iranian Tradition | Indian Tradition |
|---------|------------------|-----------------|
| **Diphthongs** | aō → ō (monophthongization ~25%) | aō preserved |
| **Vowel Length** | ī/ū confuse (~100%) | Usually distinct |
| **Palatal Consonants** | z/j/ž rarely confused | Frequent confusion (Gujarati) |
| **Nasal Vowels** | ą (not ą̇) | ą̇ (sometimes with -m) |
| **Syncope** | Present (short vowels drop) | Preserved more often |
| **Anaptyxis** | Rare | Extensive (vowel insertion) |

**Pipeline Implementation**:

In `classification_policy.yaml`:
```yaml
rules:
  # Iranian monophthongization is expected (~25% rate)
  - id: "iranian_aoe_monophthongization"
    conditions:
      - manuscript_tradition: "Iranian"
      - atomic_op: "aō→ō"
    classification: "trivial"
    frequency: "~25%"

  # Indian Old Exegetical preserves diphthongs strictly
  - id: "indian_oldexeg_diphthong_preserved"
    conditions:
      - manuscript_tradition: "Indian_OldExegetical"
      - atomic_op: "aō→ō"
    classification: "meaningful"
    frequency: "rare"

  # Indian z→j is a known tradition change
  - id: "indian_palatal_z_to_j"
    conditions:
      - manuscript_tradition: "Indian_Liturgical"
      - atomic_op: "z→j"
    classification: "trivial"
    frequency: "systematic"
```

**Validation**: Quantitative analysis of Yasna 9

- **aō diphthong instances**: 92 total
  - Iranian witnesses: 0–5.4% monophthongization (sporadic)
  - Indian witnesses: ~80% diphthong preservation (conservative)
  - Result: Rule-based classification correctly distinguishes traditions

- **Meaningful variant distribution**:
  - Iranian witnesses: 8–17 meaningful variants each (tight, conservative cluster)
  - Indian witnesses: Variable (8–66), reflecting greater diversity in Indian tradition
  - Result: Captures documented transmission stratification

**Impact**: Demonstrates that computational methods can recover the social/textual community patterns documented by philologists; makes these patterns queryable for future research.

---

## Research Question 4: Modular, Reusable Architecture

### The Question
**"Is the architecture modular and reusable for other Avestan texts or related scripts?"**

### Why It Matters
- Need to scale beyond Yasna 9 (pilot chapter)
- Other traditions may have different rules
- Pahlavi, Sogdian, and related scripts share structural features
- Scholars should be able to adapt without rewriting code

### How It's Answered

**Architecture Component**: Everything is **configuration-driven**

```
Modular Design
──────────────

┌─────────────────────────────────────────────────────────────┐
│ OCR Pipeline (src/interfaces/escriptorium)                  │
│ ├─ Input: Manuscript images                                │
│ └─ Output: ALTO XML transcriptions                          │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ Alignment (apparatus/scripts/tei_build_apparatus.py)        │
│ ├─ Input: Base text (lemma) + witness transcriptions        │
│ └─ Output: Raw apparatus (all variant readings)             │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ Classification (apparatus/scripts/tag_apparatus.py)         │
│ ├─ Input: Raw apparatus + configuration files              │
│ ├─ Config 1: orthography_families_v4.yaml (Stage 4)        │
│ ├─ Config 2: classification_policy.yaml (Stage 7)          │
│ └─ Output: Tagged apparatus (classified variants)           │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ Output (apparatus/scripts/tei_annotation_summary.py)        │
│ ├─ Statistics, XML export, analysis                        │
│ └─ Ready for scholarly inspection/publication               │
└─────────────────────────────────────────────────────────────┘
```

**Each component is independent and configuration-driven:**

1. **OCR**: Can be run standalone; outputs ALTO XML
2. **Alignment**: Operates on any base text + witnesses
3. **Classification**: Reads external YAML rule files
4. **Output**: Generates various formats (XML, statistics, etc.)

**Adaptation Examples**:

### Example 1: New Avestan Chapter (Yasna 10)
Simply provide:
- Base text: Yasna 10 segments
- Witnesses: Y10 transcriptions
- Configuration: Reuse existing `orthography_families_v4.yaml` + `classification_policy.yaml`

→ Run pipeline: Should work with minimal template adjustments

### Example 2: Pahlavi Script
Would require:
- New OCR model: Train Kraken on Pahlavi manuscripts
- New orthography families: Edit `orthography_families_v4.yaml` for Pahlavi phonology
- New rules: Edit `classification_policy.yaml` for Pahlavi traditions
- Code: No changes needed (pipeline is generic)

### Example 3: User's Own Script
- Replace OCR model
- Edit configuration files to your script's patterns
- Run existing pipeline scripts (unchanged)

**Validation** (RQ4):

**Modularity**: Each component has clear input/output contracts
- OCR → ALTO XML
- ALTO XML + lemma → raw apparatus
- Raw apparatus + rules → tagged apparatus

**Reusability**: All decision logic in YAML, not code
- Added witness group rules during thesis? Took 5 minutes
- Adjusted diphthong family? Edited one line in YAML
- Re-ran entire pipeline? Completed in under a minute

**Documentation**: Repository provides templates
- Example configuration files
- README for each component
- Sample commands copied from thesis results

**Impact**: Demonstrates tool that supports collaborative digital humanities; enables Avestan community to extend it rather than starting from scratch.

---

## System Interdependencies

```
Research Questions → Thesis Chapters → Code Components → Configuration
───────────────────────────────────────────────────────────────────────

RQ1: Transfer Learning     Chapter 3.4          src/interfaces/      (no external
     OCR                   (Model Dev)          escriptorium/          config)
                                                + Kraken

RQ2: Classification        Chapter 3.5–3.6      apparatus/scripts/   classification
     Rules                 (Apparatus           tag_apparatus.py     _policy.yaml
                           Pipeline)                                 +
                                                                     orthography
                                                                     _families.yaml

RQ3: Pattern Capture       Chapter 4            apparatus/policies/  Regional rules
     (Iran vs India)       (Evaluation)         + classification    in YAML

RQ4: Modularity &          Chapter 5            All components       Config-driven
     Reusability           (Synthesis)          + clear interfaces   throughout
```

---

## Key Design Principles

1. **Expert Knowledge First**: Encode philological research as executable rules
2. **Transparency Over Accuracy**: Prefer interpretable rules over opaque ML
3. **Configuration-Driven**: Logic in external files, not code
4. **Modular Components**: Each stage can run independently
5. **Publish Intermediate Results**: Make OCR model, rules, and data available
6. **Community Accountability**: Invite critique, iteration, improvement

---

## Future Extensions

Based on RQ4 (modularity), the architecture enables:

- **More Avestan texts**: Visperad, Vidēvdād (using adapted rules)
- **Pahlavi**: New OCR model + rule sets
- **Sogdian, Khotanese**: Similar transfer learning approach
- **Witness groups**: Load from metadata (currently commented out in code)
- **Cross-tradition analysis**: Compare spelling patterns across regions
- **Machine learning integration**: Add neural classifiers alongside rules

All without rewriting the core pipeline.

---

## Repository Navigation

To understand each RQ:

| RQ | Primary Thesis Chapter | Primary Code | Configuration | Test Results |
|----|------------------------|--------------|----------------|--------------|
| **RQ1** | Chapter 3.4 | `src/interfaces/escriptorium/` | — | [HuggingFace Model](https://huggingface.co/Nikyek/avestan-ocr-kraken-v1) |
| **RQ2** | Chapter 3.5–3.6 | `apparatus/scripts/tag_apparatus.py` | `apparatus/policies/` | Table 4.1–4.3 |
| **RQ3** | Chapter 4.2–4.3 | `apparatus/policies/` | `classification_policy.yaml` | Figures 4.1–4.5 |
| **RQ4** | Chapter 5.2.4 | All components | All `.yaml` files | Demo configs in repo |

---

**Last updated**: February 23, 2026
