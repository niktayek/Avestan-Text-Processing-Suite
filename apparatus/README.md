# Apparatus

A consolidated folder for TEI apparatus generation, classification, and archives.

## Structure
- `scripts/` — primary scripts for building and tagging
  - `tei_build_apparatus.py` — boundary-aware builder (primary)
  - `tag_apparatus.py` — classification/tagging
  - `fix_specific_alignments.py` — targeted post-fixes
  - `verify_rules.py` — validate YAML classification rules
  - `tei_annotation_summary.py` — summarize tagged apparatus stats
  - `tei_build_multi_view.py` — helper to inspect multi-view apparatus
- `outputs/Y9/` — current Yasna 9 apparatus outputs
  - `apparatus_Y9_14mss.xml`
  - `apparatus_Y9_14mss_tagged.xml`
- `policies/` — classification policy and orthography families
  - `classification_policy.yaml`
  - `orthography_families_v4.yaml`
- `archive/Y9/` — historical outputs from retired approaches

## Usage

Build and tag the Y9 apparatus from the project root:

```bash
# Build apparatus (Y9, 14 manuscripts)
poetry run python apparatus/scripts/tei_build_apparatus.py \
  --lemma-file data/Canonical_Yasna.txt \
  --witness-dir res/Yasna/witnesses \
  --output apparatus/outputs/Y9/apparatus_Y9_14mss.xml \
  --stanza-range Y9.1-Y9.14 \
  --manuscripts ms0005 ms0006 ms0015 ms0110 ms0234 ms0400 ms0235 ms4000 ms4010 ms4020 ms4045 ms4050 ms4500 ms5000

# Tag readings
poetry run python apparatus/scripts/tag_apparatus.py \
  --input apparatus/outputs/Y9/apparatus_Y9_14mss.xml \
  --output apparatus/outputs/Y9/apparatus_Y9_14mss_tagged.xml \
  --policy apparatus/policies/classification_policy.yaml \
  --families apparatus/policies/orthography_families_v4.yaml
```

## Notes
- Primary implementation: `apparatus/scripts/tag_apparatus.py`
- Outputs are generated to `apparatus/outputs/Y9/`; results also stored under `res/Yasna/apparatus/Y9/`
- Archives in `apparatus/archive/Y9/` preserve historical outputs for traceability
