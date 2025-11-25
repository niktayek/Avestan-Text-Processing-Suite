Yasna 9 — apparatus inputs

Place TEI apparatus files for Y.9 here. Format must match the Y.1 inputs:

- TEI namespace: http://www.tei-c.org/ns/1.0
- Each file contains <app> blocks, each with a <lem> and one or more <rdg wit="#ms…">.
- Readings should already include the witness list in @wit (e.g., wit="#ms0005 #ms0006").
- Example filenames (any *.xml is fine):
  - apparatus_multi_Y9_4ms_spans.xml
  - apparatus_multi_Y9_4ms_spans.with_v3_variants.xml

Adding manuscripts
- To “add manuscripts,” include them in the TEI input as additional witness tokens in rdg@wit.
  Example: wit="#ms0005 #ms0006 #ms0008 #ms0015 #ms0020 #ms0021"
- The annotator does not invent witnesses; it uses whatever is present in input TEI.

Run annotator (example)

PY=/Users/niktayekrangsafakar/Library/Caches/pypoetry/virtualenvs/ocr-lQ8MIrUH-py3.10/bin/python

$PY src/interfaces/xml_translator/tei_annotate_v3_direct.py \
  --tei res/Yasna/apparatus/Y9 \
  --features res/Yasna/meta/feature_scored.csv \
  --label-changes res/Yasna/meta/feature_label_changes.csv \
  --orthography-families res/Yasna/meta/orthography_families_v3.yaml \
  --lexical-whitelist res/Yasna/meta/lexical_whitelist_v3.txt \
  --overrides-features res/Yasna/meta/label_overrides_features.csv \
  --overrides-readings res/Yasna/meta/label_overrides_readings.csv \
  --unknown-out res/Yasna/meta/unknown_review_Y9.csv \
  --aggressive-infer

Afterwards, you can combine the outputs (optional) using the existing combiner by pointing --in-dir to this Y9 folder.
