graph LR
    subgraph "Data Preparation"
        clean_text["Clean Avestan Corpus<br/>(Canonical Tokens)"]
        noisy_text["Noisy OCR-like Text<br/>(Simulated Errors)"]
        substitution_rules["Substitution Rules<br/>(OCR Error Patterns)"]

        clean_text -->|noise.py| noisy_text
        substitution_rules -->|noise.py| noisy_text
    end

    subgraph "Preprocessing"
        normalized_text["Normalized Noisy Tokens"]

        noisy_text -->|normalizer.py| normalized_text
    end

    subgraph "Spell Checking"
        corrected_output["Corrected Tokens"]
        canonical_vocab["Canonical Vocabulary"]

        normalized_text -->|model.py| corrected_output
        canonical_vocab -->|model.py| corrected_output
    end

    subgraph "Evaluation"
        evaluation_report["Accuracy / Match Stats"]

        corrected_output -->|evaluate_spellcheck.py| evaluation_report
        clean_text -->|evaluate_spellcheck.py| evaluation_report
    end
