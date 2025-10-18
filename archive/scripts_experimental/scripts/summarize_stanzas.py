import os
import json
from lxml import etree
from src.interfaces.xml_translator import match_stanzas_by_id as ms

CANON = os.path.join(os.getcwd(), 'data', 'Yasna_Static.xml')
OURS = os.path.join(os.getcwd(), 'data', 'CAB', 'Yasna', '0005.xml')
STANZAS = ['Y0.7', 'Y0.8', 'Y0.9', 'Y0.10']

parser = etree.XMLParser(recover=True, remove_blank_text=True, huge_tree=True)
canon_tree = etree.parse(CANON, parser=parser)
our_tree = etree.parse(OURS, parser=parser)
canon_divs = ms.extract_divs_by_id(canon_tree)
our_divs = ms.extract_divs_by_id(our_tree)

out = []
for ST in STANZAS:
    canon_div = canon_divs.get(ST)
    our_div = our_divs.get(ST)
    if canon_div is None or our_div is None:
        out.append({'xml_id': ST, 'error': 'stanza missing'})
        continue
    canon_words = ms.extract_words_from_div(canon_div, insert_space_after_period=False)
    our_words = ms.extract_words_from_div(our_div, insert_space_after_period=True)
    alignment = ms.align_word_sequences(canon_words, our_words)
    matched = [a for a in alignment if a.get('matched') and a.get('canon_index') is not None]
    deletes = [a for a in alignment if a.get('relation') == 'delete' and a.get('canon_index') is not None]
    inserts = [a for a in alignment if a.get('canon_index') is None]
    many_to_one = [a for a in alignment if a.get('relation') == 'many-to-one']
    out.append({
        'xml_id': ST,
        'canon_word_count': len(canon_words),
        'our_word_count': len(our_words),
        'matched_count': len(matched),
        'delete_count': len(deletes),
        'insert_count': len(inserts),
        'many_to_one_count': len(many_to_one),
        'sample_inserts': [i['our_word'] for i in inserts[:5]]
    })

print(json.dumps(out, ensure_ascii=False, indent=2))
