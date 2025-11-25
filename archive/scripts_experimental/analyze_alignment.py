import json
import os
from lxml import etree
from src.interfaces.xml_translator import match_stanzas_by_id as ms

CANON = os.path.join(os.getcwd(), 'data', 'Yasna_Static.xml')
OURS = os.path.join(os.getcwd(), 'data', 'CAB', 'Yasna', '0005.xml')
STANZA = 'Y0.6'

# parse with recover
parser = etree.XMLParser(recover=True, remove_blank_text=True, huge_tree=True)
canon_tree = etree.parse(CANON, parser=parser)
our_tree = etree.parse(OURS, parser=parser)

canon_divs = ms.extract_divs_by_id(canon_tree)
our_divs = ms.extract_divs_by_id(our_tree)
canon_div = canon_divs.get(STANZA)
our_div = our_divs.get(STANZA)
canon_words = ms.extract_words_from_div(canon_div, insert_space_after_period=False)
our_words = ms.extract_words_from_div(our_div, insert_space_after_period=True)
alignment = ms.align_word_sequences(canon_words, our_words)

# compute matched our indices from canonical-aligned entries and the list of insert our indices
matched_our = set()
canon_aligned = []
insert_our = []
for item in alignment:
    if item['canon_index'] is not None and item['our_index'] is not None:
        matched_our.add(item['our_index'])
        canon_aligned.append((item['canon_index'], item['our_index']))
    if item['canon_index'] is None and item['our_index'] is not None:
        insert_our.append(item['our_index'])

print('canon_aligned (canon_index -> our_index):')
print(sorted(canon_aligned))
print('\nmatched_our indices:', sorted(matched_our))
print('\ninsert_our indices:', sorted(insert_our))
print('\nintersection (should be empty):', sorted(set(insert_our) & matched_our))

# print alignment entries where our_index appears both as matched and inserted
both = [oi for oi in insert_our if oi in matched_our]
if both:
    print('\nOur indices that are both matched and inserted (bad):', both)
    for oi in both:
        print('\nDetails for our_index', oi)
        for item in alignment:
            if item['our_index'] == oi:
                print(item)
else:
    print('\nNo duplicates found')
