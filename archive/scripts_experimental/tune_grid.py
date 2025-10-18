#!/usr/bin/env python3
import os
from lxml import etree
from src.interfaces.xml_translator import match_stanzas_by_id as ms

CANON = os.path.join(os.getcwd(), 'data', 'Yasna_Static.xml')
OURS = os.path.join(os.getcwd(), 'data', 'CAB', 'Yasna', '0005.xml')
STANZAS = ['Y0.7']  # focused test; expand if you want

parser = etree.XMLParser(recover=True, remove_blank_text=True, huge_tree=True)
canon_tree = etree.parse(CANON, parser=parser)
our_tree = etree.parse(OURS, parser=parser)
canon_divs = ms.extract_divs_by_id(canon_tree)
our_divs = ms.extract_divs_by_id(our_tree)

def inspect_alignment(alignment, keys=(15,16)):
    # Count many-to-one relations and find mapping for specific canonical indices
    mto = sum(1 for e in alignment if e.get('relation') == 'many-to-one')
    mapped = {k: None for k in keys}
    for e in alignment:
        ci = e.get('canon_index')
        if ci in mapped:
            mapped[ci] = e
    return mto, mapped

ratios = [0.55, 0.60, 0.65]
spans = [2, 3, 4]
window = 3

for ratio in ratios:
    for span in spans:
        print('\n=== params: ratio=%.2f max_canon_span=%d window=%d ===' % (ratio, span, window))
        for st in STANZAS:
            canon_div = canon_divs.get(st)
            our_div = our_divs.get(st)
            if canon_div is None or our_div is None:
                print(st, 'missing stanza')
                continue
            canon_words = ms.extract_words_from_div(canon_div, insert_space_after_period=False)
            our_words = ms.extract_words_from_div(our_div, insert_space_after_period=True)
            alignment = ms.align_word_sequences(canon_words, our_words, window=window, ratio_threshold=ratio, max_canon_span=span)
            mto, mapped = inspect_alignment(alignment)
            print(f"{st}: canon={len(canon_words)} our={len(our_words)} many-to-one_count={mto}")
            for k, v in mapped.items():
                if v is None:
                    print(f"  canon_index {k}: NOT MAPPED")
                else:
                    print(f"  canon_index {k}: relation={v['relation']} our_index={v['our_index']} our_word={v['our_word']!r}")

print('\nDone grid')
