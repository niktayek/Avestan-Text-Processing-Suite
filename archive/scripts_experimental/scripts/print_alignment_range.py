import os
import json
from lxml import etree
from src.interfaces.xml_translator import match_stanzas_by_id as ms

CANON = os.path.join(os.getcwd(), 'data', 'Yasna_Static.xml')
OURS = os.path.join(os.getcwd(), 'data', 'CAB', 'Yasna', '0005.xml')
STANZA = 'Y0.10'
START = 0
END = 40

parser = etree.XMLParser(recover=True, remove_blank_text=True, huge_tree=True)
canon_tree = etree.parse(CANON, parser=parser)
our_tree = etree.parse(OURS, parser=parser)
canon_divs = ms.extract_divs_by_id(canon_tree)
our_divs = ms.extract_divs_by_id(our_tree)
canon_div = canon_divs.get(STANZA)
our_div = our_divs.get(STANZA)
if canon_div is None or our_div is None:
    print(json.dumps({'error': 'stanza missing', 'stanza': STANZA}, ensure_ascii=False))
    raise SystemExit(1)
canon_words = ms.extract_words_from_div(canon_div, insert_space_after_period=False)
our_words = ms.extract_words_from_div(our_div, insert_space_after_period=True)
alignment = ms.align_word_sequences(canon_words, our_words)

slice_entries = [a for a in alignment if a.get('canon_index') is not None and START <= a['canon_index'] <= END]
print(json.dumps({'xml_id': STANZA, 'canon_words_slice': canon_words[START:END+1], 'alignment_slice': slice_entries}, ensure_ascii=False, indent=2))
