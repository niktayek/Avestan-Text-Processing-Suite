# Avestan OCR & Scribal Analysis

Tools for **Avestan manuscript processing**: OCR (Kraken + eScriptorium), token matching, feature/Leitfehler analysis, and **scribal-school** exploration.

**Model card:** [avestan-ocr-kraken-v1](https://huggingface.co/Nikyek/avestan-ocr-kraken-v1)

---

## Overview

This repository is a modular toolkit that:

1. Applies OCR to manuscript images (segmentation + recognition).
2. Aligns OCR or manually transliterated text to a **canonical** reference.
3. Detects grapheme-level changes (substitutions / insertions / deletions; Leitfehler).
4. Aggregates features across manuscripts to compute similarity, cluster manuscripts, and support **manual** scribal-school assignment.
5. Produces quantitative & qualitative feature catalogs.

### End-to-End at a Glance

```mermaid
graph LR
  classDef invisible fill:transparent,stroke:transparent;

  subgraph "Applying OCR"
    pad1[" "]:::invisible
    A["Images"] --> B["eScriptorium / Kraken"]
    B --> C["ALTO XML / CAB XML"]
  end

  subgraph "Matching & Features"
    pad2[" "]:::invisible
    D["Sequence / Dictionary Matchers"]
    E["Feature Detection (incl. Leitfehler)"]
    C --> D --> E
  end

  subgraph "Scribal School Analysis"
    pad3[" "]:::invisible
    F["Frequency / Similarity Matrices"]
    G["Tree / Clustermap"]
    H["Manual School Assignment"]
    I["Feature Catalogs (quant/qual)"]
    E --> F --> G --> H --> I
  end
```
