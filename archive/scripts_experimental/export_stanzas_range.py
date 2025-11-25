import os
import json
import csv
from lxml import etree
from src.interfaces.xml_translator import match_stanzas_by_id as ms

CANON = os.path.join(os.getcwd(), 'data', 'Yasna_Static.xml')
OURS = os.path.join(os.getcwd(), 'data', 'CAB', 'Yasna', '0005.xml')
STANZAS = ['Y0.6', 'Y0.7', 'Y0.8', 'Y0.9', 'Y0.10', 'Y0.11']
OUT_DIR = os.path.join(os.getcwd(), 'res')
JSON_OUT = os.path.join(OUT_DIR, 'stanza_word_matches_Y0.6-Y0.11.json')
CSV_OUT = os.path.join(OUT_DIR, 'stanza_word_matches_Y0.6-Y0.11.csv')

os.makedirs(OUT_DIR, exist_ok=True)
parser = etree.XMLParser(recover=True, remove_blank_text=True, huge_tree=True)
canon_tree = etree.parse(CANON, parser=parser)
our_tree = etree.parse(OURS, parser=parser)
canon_divs = ms.extract_divs_by_id(canon_tree)
our_divs = ms.extract_divs_by_id(our_tree)

results = []
for ST in STANZAS:
    canon_div = canon_divs.get(ST)
    our_div = our_divs.get(ST)
    if canon_div is None or our_div is None:
        results.append({'xml_id': ST, 'error': 'stanza not found in one of the files'})
        continue
    canon_words = ms.extract_words_from_div(canon_div, insert_space_after_period=False)
    our_words = ms.extract_words_from_div(our_div, insert_space_after_period=True)
    # tuned parameters for this export: allow larger many-to-one concatenation and slightly lower ratio
    alignment = ms.align_word_sequences(canon_words, our_words, window=3, ratio_threshold=0.60, max_canon_span=4)
    results.append({
        'xml_id': ST,
        'canon_word_count': len(canon_words),
        'our_word_count': len(our_words),
        'canon_words': canon_words,
        'our_words': our_words,
        'alignment': alignment
    })

with open(JSON_OUT, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# write CSV: one row per alignment entry
with open(CSV_OUT, 'w', encoding='utf-8', newline='') as csvf:
    writer = csv.writer(csvf)
    writer.writerow(['xml_id','canon_index','our_index','canon_word','our_word','relation','matched'])
    for stanza in results:
        if 'alignment' not in stanza:
            writer.writerow([stanza.get('xml_id'), 'ERROR', '', stanza.get('error'), '', '', ''])
            continue
        for ent in stanza['alignment']:
            writer.writerow([
                stanza['xml_id'],
                '' if ent.get('canon_index') is None else ent.get('canon_index'),
                '' if ent.get('our_index') is None else ent.get('our_index'),
                ent.get('canon_word',''),
                ent.get('our_word',''),
                ent.get('relation',''),
                ent.get('matched', False)
            ])

print('Wrote:', JSON_OUT, CSV_OUT)
