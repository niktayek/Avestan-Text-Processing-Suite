# Avestan Text Processing Suite

**OCR and Rule-Based Critical Apparatus for the Avestan Manuscripts**

**Status**: Research code implementing a thesis submitted to Freie Universität Berlin, 2025  
**OCR Model**: Published on [Hugging Face](https://huggingface.co/Nikyek/avestan-ocr-kraken-v1)

**Citation**: Please use [CITATION.cff](CITATION.cff) for citation metadata. This repository implements research from:

> Yekrang Safakar, N. (2025). *Integrating OCR and Automated Apparatus Construction for Avestan Texts*. Master's thesis, Freie Universität Berlin.

**Security note**: GitHub Dependabot reports 4 remaining alerts, all transitive dependencies from the Kraken OCR framework:
- **Pillow PSD vulnerability** (High): This codebase only processes PNG/JPG/TIFF manuscript images, not PSD files, so the vulnerability does not apply. Will update when Pillow 11.4.0+ becomes available in the Poetry index.
- **PyTorch vulnerabilities** (3 alerts: Critical, Moderate, Low): These relate to `torch.load()` on untrusted models and resource handling. This project does not load external PyTorch models or call `torch.load()` directly—OCR inference is handled internally by Kraken. Will update when patched PyTorch releases become available.

All dependencies are locked at their latest available versions (as of Feb 2025) and pose minimal practical risk for this research codebase's intended use.

---

## Overview

This repository implements two interconnected pipelines for processing historical Avestan manuscripts:

### 1. **OCR Pipeline** (Research Question 1)
- **Transfer learning OCR** for the Avestan script (right-to-left, diacritically dense)
- **99.2% character accuracy** trained on ~43 pages of manually annotated ground truth
- **Model available** on [Hugging Face](https://huggingface.co/Nikyek/avestan-ocr-kraken-v1) for reuse
- **Uses Kraken** (open-source framework for historical scripts)
- **Key achievement**: Demonstrates that high-quality OCR for low-resource ancient languages is feasible through strategic transfer learning

### 2. **Critical Apparatus Pipeline** (Research Question 2)
- **Configuration-driven classification** that distinguishes trivial orthographic variants from meaningful textual differences
- **Rule-based decision ladder** encoding decades of philological expertise from Martínez Porro (2020)
- **Auditable rules** (all decision logic in human-readable YAML configuration files, not black-box ML)
- **Output**: TEI-encoded critical apparatus with per-reading classification (trivial / meaningful / missing / unknown)
- **Performance**: On Yasna 9 (14 witnesses), correctly classifies **88.8% as trivial**, **2.9% as meaningful** — consistent with liturgical conservatism
- **Key achievement**: Demonstrates that philological expertise can be formalized as transparent, adjustable computational rules

### 3. **Supporting Contributions**
- **Regional pattern recognition** (Research Question 3): Captures Iranian vs. Indian manuscript traditions through orthography family rules
- **Modular, reusable architecture** (Research Question 4): Configuration-driven design enables adaptation to other Avestan texts and related scripts (Pahlavi, Sogdian)

---

## Intended Users

- **Philologists & textual scholars**: Accelerate manuscript collation; focus your expertise on interpretation rather than mechanical comparison
- **Computational linguists**: Use as a template for applying computational methods to other low-resource historical languages
- **Digital humanities researchers**: Reference implementation of transparent, auditable AI for humanities scholarship
- **Avestan community**: Open infrastructure for digitizing and analyzing the Avestan manuscript tradition

---

## Quick Start

### Prerequisites
- Python 3.10+
- [Poetry](https://python-poetry.org) for dependency management

### Installation
```bash
# Clone the repository
git clone https://github.com/niktayek/Avestan-Text-Processing-Suite.git
cd Avestan-Text-Processing-Suite

# Install dependencies
poetry install
```

### Run the Apparatus Pipeline

**Note**: The example commands below require Avestan text data and witness transcriptions, which are not included in this repository due to copyright considerations. You'll need to provide your own TEI-encoded lemma file and witness manuscripts.

Example workflow (adapt paths to your data):
```bash
# Build apparatus from witness transcriptions
poetry run python apparatus/scripts/tei_build_apparatus.py \
  --lemma-file <path-to-your-lemma.xml> \
  --witness-dir <path-to-witness-directory> \
  --output apparatus/outputs/apparatus_output.xml \
  --stanza-range <stanza-range>

# Classify variants as trivial vs. meaningful
poetry run python apparatus/scripts/tag_apparatus.py \
  --input apparatus/outputs/apparatus_output.xml \
  --output apparatus/outputs/apparatus_output_tagged.xml \
  --policy apparatus/policies/classification_policy.yaml \
  --families apparatus/policies/orthography_families_v4.yaml
```

---

## Repository Structure

```
avestan-text-processing-suite/
├── apparatus/                          # Critical apparatus pipeline
│   ├── scripts/
│   │   ├── tei_build_apparatus.py     # Extract apparatus from witnesses
│   │   ├── tag_apparatus.py           # Classify variants (the decision ladder)
│   │   ├── verify_rules.py            # Validate classification rules
│   │   └── tei_annotation_summary.py  # Statistics on tagged apparatus
│   ├── policies/
│   │   ├── classification_policy.yaml        # Decision rules (trivial vs. meaningful)
│   │   └── orthography_families_v4.yaml      # Regional tradition rules (Iranian vs. Indian)
│   ├── outputs/                        # Generated apparatus outputs
│   └── README.md                       # Apparatus pipeline documentation
│
├── src/
│   └── interfaces/                    # Integrations with external tools
│       ├── escriptorium/              # eScriptorium OCR platform interface
│       ├── cab/                       # CAB (Corpus Avesticum Berolinense) reader
│       └── xml_translator/            # ALTO/PAGE XML conversions
│
├── data/                              # Reference texts and canonical editions
│   └── Yasna_Static.xml              # Canonical lemma for Yasna apparatus
│
├── res/                               # Results and witness transcriptions
│   └── Yasna/
│       ├── witnesses/                # Manuscript transcriptions
│       └── apparatus/                # Generated apparatus outputs
│
├── LICENSE                            # MIT License
├── CITATION.cff                       # Citation metadata
├── README.md                          # This file
├── ARCHITECTURE.md                    # System design & research questions
└── pyproject.toml                     # Python project configuration
```

## Key Results (Validation on Yasna 9)

| Metric | Value | Interpretation |
|--------|-------|-----------------|
| **OCR Character Accuracy** | 99.2% | High fidelity transcription of diacritically complex script |
| **OCR Word Accuracy** | 97% | Reliable enough for downstream apparatus construction |
| **Trivial variant rate** | 88.8% | Expected for liturgical text; confirms decision ladder calibration |
| **Meaningful variant rate** | 2.9% | Substantive differences warranting editorial attention |
| **Unknown classification rate** | 0% | Decision ladder has sufficient rule coverage |
| **Apparatus entries** | 712 | Complete collation of all Yasna 9 segments across witnesses |
| **Total readings analyzed** | 9,618 | Across 14 witnesses, 712 segments × variable witness count |

**Validation**: Classified variants were manually reviewed by philologists; results align with traditional textual criticism expectations.

## The Research Questions

This work addresses four core research questions:

### **RQ1: Can OCR models trained on other languages, e.g., Hebrew, be successfully adapted for Avestan manuscripts via transfer learning, and what level of recognition accuracy is achievable with limited ground-truth data?**
**Answer**: Yes. Starting from a Hebrew-trained Kraken model and iteratively refining on ~43 pages of ground truth achieved 99.2% character accuracy. This demonstrates a template for bootstrapping OCR for other low-resource scripts.

### **RQ2: Can orthographic variants in Avestan manuscripts be automatically classified as trivial or substantive using rule-based systems that encode philological knowledge?**
**Answer**: Yes. Martínez Porro's systematic orthographic analysis was formalized as configuration files (YAML) defining "orthography families" (character groupings by phonetic equivalence) and "decision policies" (rules for classification). Because all logic is explicit and human-readable, the system is transparent and adjustable.

### **RQ3: Can computational analysis of orthographic patterns support the construction of critical apparatuses that accurately reflect regional transmission traditions and manuscript relationships?**
**Answer**: Yes. Configuration-driven rules distinguish Iranian vs. Indian traditions. For example, Iranian monophthongization (aō → ō) occurs in ~3% of Iranian witnesses but is preserved in Indian copies, correctly captured by tradition-specific rules.

### **RQ4: To what extent is the apparatus pipeline scalable, modular, and adaptable for other Avestan texts or related scripts?**
**Answer**: Each component (OCR, alignment, normalization, classification) operates independently via well-defined interfaces. All philological logic is externalized in configuration files, allowing users to adapt rules for different texts or scripts without code changes.

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed explanation of each RQ and how the codebase addresses it.

---

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System design and research questions
- **[apparatus/README.md](apparatus/README.md)** — The variant classification pipeline (decision ladder)
- **[COLAB_INSTRUCTIONS.md](COLAB_INSTRUCTIONS.md)** — Training OCR models in Google Colab for non-technical users
- **[colab_ocr_package/](colab_ocr_package/)** — Complete package with trained models, test images, and Colab notebooks for hands-on model training

The full methodology is documented in the thesis: *Integrating OCR and Automated Apparatus Construction for Avestan Texts* (Yekrang Safakar, 2025).

---

## Limitations & Scope

1. **Apparatus requires error-free input**: The classification pipeline works best with manually reviewed transcriptions. Raw OCR output should be post-edited before feeding to apparatus generation.
2. **Witness group metadata not yet loaded**: Configuration exists for distinguishing scribal schools (Iranian Yazdi/Kermani, Indian Navsari/Surat) but is currently commented out in the code. Future work will integrate this.
3. **Syncope detection incomplete**: The system detects most orthographic operations but omits "vowel deleted" changes in some cases.

---

## Development & Contributing

Contributions are welcome! Please:

1. **Report issues** via GitHub Issues (bugs, documentation gaps, etc.)
##
**Nikta Yekrang Safakar**
- Master's degree: Iranistik, Freie Universität Berlin (2024)
- Current affiliation: Leibniz-Zentrum Allgemeine Sprachwissenschaft (ZAS) and Humboldt University of Berlin
- Email: niktaayekrang@gmail.com
- GitHub: [@niktayek](https://github.com/niktayek)

---

## Acknowledgments

This Master's thesis was supervised by **Prof. Dr. Alberto Cantera Glera** (primary supervisor) and **Dr. des. Jaime Martínez Porro** (second supervisor) at the Iranistik department, Freie Universität Berlin. The work was developed in collaboration with the **Corpus Avesticum Berolinense (CAB) project**.

Special thanks to:
- **Alberto Cantera** (Director, CAB; Freie Universität Berlin) for manuscript access, guidance, and supervision
- **Javier Martínez Porro** (Avestan philologist) whose systematic orthographic analysis provided the theoretical foundation for classification rules and for serving as second supervisor
- **Daniel Stökl Ben Ezra** (Hebrew philology and eScriptorium expertise) for technical advice on historical script OCR
- **The Kraken and eScriptorium communities** for open-source tools and responsive development support

---

## Author & Affiliation

**Nikta Yekrang Safakar**
- Master's thesis, Freie Universität Berlin (December 2025)
- Current affiliation: Leibniz-Zentrum Allgemeine Sprachwissenschaft (ZAS) and Humboldt University of Berlin
- Email: niktaayekrang@gmail.com

---

## Citation

See [CITATION.cff](CITATION.cff) for machine-readable metadata. Standard form:

Yekrang Safakar, N. (2025). *Integrating OCR and Automated Apparatus Construction for Avestan Texts*. Master's thesis, Freie Universität Berlin. https://github.com/niktayek/Avestan-Text-Processing-Suite

---

## Questions

- Issues: Open a GitHub issue with details of the problem
- Methodology: See ARCHITECTURE.md or the thesis
- Contact: niktaayekrang@gmail.com

**Repository**: https://github.com/niktayek/Avestan-Text-Processing-Suite  
**Last updated**: February 2026