import json
import os
from lxml import etree

# import the module we've been editing
from src.interfaces.xml_translator import match_stanzas_by_id as ms

CANON = os.path.join(os.getcwd(), 'data', 'Yasna_Static.xml')
OURS = os.path.join(os.getcwd(), 'data', 'CAB', 'Yasna', '0005.xml')
STANZA = 'Y0.6'

# forgiving parser to match behavior in module
try:
    canon_tree = etree.parse(CANON)
except etree.XMLSyntaxError:
    parser = etree.XMLParser(recover=True, remove_blank_text=True, huge_tree=True)
    canon_tree = etree.parse(CANON, parser=parser)

try:
    our_tree = etree.parse(OURS)
except etree.XMLSyntaxError:
    parser = etree.XMLParser(recover=True, remove_blank_text=True, huge_tree=True)
    our_tree = etree.parse(OURS, parser=parser)

canon_divs = ms.extract_divs_by_id(canon_tree)
our_divs = ms.extract_divs_by_id(our_tree)

canon_div = canon_divs.get(STANZA)
our_div = our_divs.get(STANZA)

if canon_div is None or our_div is None:
    print(json.dumps({'error': 'stanza not found', 'stanza': STANZA}, ensure_ascii=False))
    raise SystemExit(1)

canon_words = ms.extract_words_from_div(canon_div, insert_space_after_period=False)
our_words = ms.extract_words_from_div(our_div, insert_space_after_period=True)
alignment = ms.align_word_sequences(canon_words, our_words)

out = {
    'xml_id': STANZA,
    'canon_word_count': len(canon_words),
    'our_word_count': len(our_words),
    'canon_words': canon_words,
    'our_words': our_words,
    'alignment': alignment
}
print(json.dumps(out, ensure_ascii=False, indent=2))
