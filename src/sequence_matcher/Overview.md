graph LR
    subgraph "Input Preparation"
        ocr_text_blocks["OCR Text Blocks<br/>(BlockID \\t Text)"]
        reference_text_blocks["Canonical Text Blocks<br/>(BlockID \\t Text)"]
        substitution_rules["Substitution Rules (Optional)<br/>(for normalization)"]
        normalized_ocr["Normalized OCR"]
        normalized_ref["Normalized Reference"]

        ocr_text_blocks -->|data_loader.py| normalized_ocr
        reference_text_blocks -->|data_loader.py| normalized_ref
        substitution_rules -->|config.py<br/>matcher.py| normalized_ocr
        substitution_rules -->|config.py<br/>matcher.py| normalized_ref
    end

    subgraph "Sequence Alignment"
        aligned_blocks["Aligned Block-Level Sequences"]

        normalized_ocr -->|matcher.py| aligned_blocks
        normalized_ref -->|matcher.py| aligned_blocks
    end

    subgraph "Post-Matching Output"
        alignment_csv["Alignment Results (Token-Level)<br/>(BlockID, OCR, Canonical, Score)"]
        alignment_analysis["Match Statistics<br/>(Match Score, Merge Count, etc.)"]

        aligned_blocks -->|print_matches.py| alignment_csv
        aligned_blocks -->|analyze.py| alignment_analysis
    end
