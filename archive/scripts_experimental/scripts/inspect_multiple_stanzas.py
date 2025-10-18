import json
import os
from lxml import etree
from src.interfaces.xml_translator import match_stanzas_by_id as ms

CANON = os.path.join(os.getcwd(), 'data', 'Yasna_Static.xml')
OURS = os.path.join(os.getcwd(), 'data', 'CAB', 'Yasna', '0005.xml')
STANZAS = ['Y0.7', 'Y0.8', 'Y0.9', 'Y0.10']

# forgiving parser to match behavior in module
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
    alignment = ms.align_word_sequences(canon_words, our_words)
    results.append({
        'xml_id': ST,
        'canon_word_count': len(canon_words),
        'our_word_count': len(our_words),
        'canon_words': canon_words,
        'our_words': our_words,
        'alignment': alignment
    })

print(json.dumps(results, ensure_ascii=False, indent=2))
