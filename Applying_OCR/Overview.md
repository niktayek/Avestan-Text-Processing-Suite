graph LR
    subgraph "Image & Transcription Preparation"
        manuscript_images["Avestan Manuscript Images"]
        transcription_xml["Transcription in ALTO XML<br/>(from CAB or manually corrected OCR)"]
        segmented_data["Segmented Line/Word Regions"]
        labeled_training_data["Aligned Image–Text Pairs"]

        manuscript_images -->|Segmentation GUI<br/>eScriptorium| segmented_data
        segmented_data -->|Manually aligned<br/>or copy-pasted text| labeled_training_data
        transcription_xml -->|Aligned via GUI| labeled_training_data
    end

    subgraph "Model Training (Kraken)"
        training_config["Makefile Config"]
        recognition_model["Recognition Model (.mlmodel)"]
        segmentation_model["Segmentation Model (.mlmodel)"]

        labeled_training_data -->|Training Step 1| segmentation_model
        labeled_training_data -->|Training Step 2| recognition_model
        training_config -->|Makefile targets| recognition_model
        training_config -->|Makefile targets| segmentation_model
    end

    subgraph "Inference (OCR Application)"
        new_images["New Unseen Manuscript Images"]
        predicted_xml["Predicted ALTO XML<br/>(via eScriptorium or CLI)"]

        new_images -->|Apply segmentation_model| segmented_data_new
        segmented_data_new -->|Apply recognition_model| predicted_xml
    end

    subgraph "Post-OCR Processing"
        predicted_xml -->|xml_translator.py| cab_format_output["CAB XML Format Output"]
    end
