#!/usr/bin/env bash
set -euo pipefail

# A) Fill changes → overrides from word matches
python src/interfaces/xml_translator/fill_changes_to_overrides.py \
  --matches res/Yasna/meta/yasna_matches.csv \
  --features res/Yasna/meta/feature_scored.csv \
  --out-features res/Yasna/meta/label_overrides_features.csv \
  --out-readings res/Yasna/meta/label_overrides_readings.csv

# B) Optional: fold in unknowns-based auto overrides too
if [ -f "res/Yasna/meta/unknown_review_after_overrides.csv" ]; then
python src/interfaces/xml_translator/auto_overrides_from_unknowns.py \
  --unknown-in res/Yasna/meta/unknown_review_after_overrides.csv \
  --features   res/Yasna/meta/feature_scored.csv \
  --out-features res/Yasna/meta/label_overrides_features.csv \
  --out-readings res/Yasna/meta/label_overrides_readings.csv
fi

# C) Apply to TEI
python src/interfaces/xml_translator/tei_annotate_v3_direct.py \
  --tei res/Yasna/apparatus/multi \
  --features res/Yasna/meta/feature_scored.csv \
  --label-changes res/Yasna/meta/feature_label_changes.csv \
  --orthography-families res/Yasna/meta/orthography_families_v3.yaml \
  --lexical-whitelist res/Yasna/meta/lexical_whitelist_v3.txt \
  --overrides-features res/Yasna/meta/label_overrides_features.csv \
  --overrides-readings res/Yasna/meta/label_overrides_readings.csv \
  --unknown-out res/Yasna/meta/unknown_review_after_overrides.csv \
  --aggressive-infer
