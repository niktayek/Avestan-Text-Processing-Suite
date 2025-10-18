import os
import csv
from lxml import etree
from collections import Counter
from src.interfaces.xml_translator import match_stanzas_by_id as ms

CANON = os.path.join(os.getcwd(), 'data', 'Yasna_Static.xml')
OURS = os.path.join(os.getcwd(), 'data', 'CAB', 'Yasna', '0005.xml')
OUT_DIR = os.path.join(os.getcwd(), 'res')
CSV_OUT = os.path.join(OUT_DIR, 'stanza_word_matches_Y1.1-Y1.23_by_our_tight.csv')

STANZAS = [f'Y1.{i}' for i in range(1,24)]

os.makedirs(OUT_DIR, exist_ok=True)
parser = etree.XMLParser(recover=True, remove_blank_text=True, huge_tree=True)
canon_tree = etree.parse(CANON, parser=parser)
our_tree = etree.parse(OURS, parser=parser)
canon_divs = ms.extract_divs_by_id(canon_tree)
our_divs = ms.extract_divs_by_id(our_tree)

# Parameters (tight)
ratio_threshold = 0.75
window = 2
max_canon_span = 3

rows = []
counts = Counter()
for ST in STANZAS:
    canon_div = canon_divs.get(ST)
    our_div = our_divs.get(ST)
    if canon_div is None or our_div is None:
        # stanza missing in one of the files
        continue
    canon_words = ms.extract_words_from_div(canon_div, insert_space_after_period=False)
    our_words = ms.extract_words_from_div(our_div, insert_space_after_period=True)
    alignment = ms.align_word_sequences(canon_words, our_words, window=window, ratio_threshold=ratio_threshold, max_canon_span=max_canon_span)

    our_to_canons = {i: [] for i in range(len(our_words))}
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

    for oi, ow in enumerate(our_words):
        cis = sorted(set(our_to_canons.get(oi, [])))
        if not cis:
            rows.append([ST, oi, ow, '', '', 'unmatched', False])
            counts['unmatched'] += 1
            continue
        canon_tokens = [canon_words[ci] for ci in cis]
        canon_indexes_str = ";".join(str(ci) for ci in cis)
        canon_words_str = " ".join(canon_tokens)
        if len(cis) > 1:
            relation = 'many-to-one'
            matched = True
        else:
            ci = cis[0]
            try:
                a = ms.normalize_token(canon_words[ci])
                b = ms.normalize_token(ow)
            except Exception:
                a = canon_words[ci].lower()
                b = ow.lower()
            relation = 'equal' if a == b else 'substitution'
            matched = True
        rows.append([ST, oi, ow, canon_indexes_str, canon_words_str, relation, matched])
        counts[relation] += 1

with open(CSV_OUT, 'w', encoding='utf-8', newline='') as csvf:
    writer = csv.writer(csvf)
    writer.writerow(['xml_id','our_index','our_word','canon_indexes','canon_words','relation','matched'])
    for r in rows:
        writer.writerow(r)

print('Wrote:', CSV_OUT)
print('Counts:', counts)
