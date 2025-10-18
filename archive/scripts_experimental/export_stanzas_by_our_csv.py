import os
import csv
from lxml import etree
from src.interfaces.xml_translator import match_stanzas_by_id as ms

CANON = os.path.join(os.getcwd(), 'data', 'Yasna_Static.xml')
OURS = os.path.join(os.getcwd(), 'data', 'CAB', 'Yasna', '0005.xml')
STANZAS = ['Y0.6', 'Y0.7', 'Y0.8', 'Y0.9', 'Y0.10', 'Y0.11']
OUT_DIR = os.path.join(os.getcwd(), 'res')
CSV_OUT = os.path.join(OUT_DIR, 'stanza_word_matches_Y0.6-Y0.11_by_our.csv')

os.makedirs(OUT_DIR, exist_ok=True)
parser = etree.XMLParser(recover=True, remove_blank_text=True, huge_tree=True)
canon_tree = etree.parse(CANON, parser=parser)
our_tree = etree.parse(OURS, parser=parser)
canon_divs = ms.extract_divs_by_id(canon_tree)
our_divs = ms.extract_divs_by_id(our_tree)

rows = []
for ST in STANZAS:
    canon_div = canon_divs.get(ST)
    our_div = our_divs.get(ST)
    if canon_div is None or our_div is None:
        # add a placeholder row
        rows.append([ST, '', '', '', '', 'stanza not found', False])
        continue
    canon_words = ms.extract_words_from_div(canon_div, insert_space_after_period=False)
    our_words = ms.extract_words_from_div(our_div, insert_space_after_period=True)
    alignment = ms.align_word_sequences(canon_words, our_words, window=3, ratio_threshold=0.60, max_canon_span=4)

    # Build mapping our_index -> list of canon_indexes
    our_to_canons = {i: [] for i in range(len(our_words))}
    # alignment may contain merged summaries with 'canon_indexes' or canon_index per entry
    for ent in alignment:
        if ent.get('our_index') is None:
            continue
        oi = ent['our_index']
        if 'canon_indexes' in ent and ent['canon_indexes']:
            for ci in ent['canon_indexes']:
                our_to_canons.setdefault(oi, []).append(ci)
        elif ent.get('canon_index') is not None:
            ci = ent['canon_index']
            our_to_canons.setdefault(oi, []).append(ci)

    # write one row per our token
    for oi, ow in enumerate(our_words):
        cis = sorted(set(our_to_canons.get(oi, [])))
        if not cis:
            rows.append([ST, oi, ow, '', '', 'unmatched', False])
            continue
        canon_tokens = [canon_words[ci] for ci in cis]
        canon_indexes_str = ";".join(str(ci) for ci in cis)
        canon_words_str = " ".join(canon_tokens)
        # decide relation
        if len(cis) > 1:
            relation = 'many-to-one'
            matched = True
        else:
            ci = cis[0]
            # normalize and compare
            try:
                a = ms.normalize_token(canon_words[ci])
                b = ms.normalize_token(ow)
            except Exception:
                a = canon_words[ci].lower()
                b = ow.lower()
            relation = 'equal' if a == b else 'substitution'
            matched = True
        rows.append([ST, oi, ow, canon_indexes_str, canon_words_str, relation, matched])

# write CSV
with open(CSV_OUT, 'w', encoding='utf-8', newline='') as csvf:
    writer = csv.writer(csvf)
    writer.writerow(['xml_id','our_index','our_word','canon_indexes','canon_words','relation','matched'])
    for r in rows:
        writer.writerow(r)

print('Wrote:', CSV_OUT)
