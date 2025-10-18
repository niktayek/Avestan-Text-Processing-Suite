from lxml import etree
import os

CANON = os.path.join(os.getcwd(), 'data', 'Yasna_Static.xml')
OURS = os.path.join(os.getcwd(), 'data', 'CAB', 'Yasna', '0005.xml')
STANZA = 'Y0.6'

# forgiving parser
parser = etree.XMLParser(recover=True, remove_blank_text=False, huge_tree=True)
our_tree = etree.parse(OURS, parser=parser)

# find the div for STANZA
root = our_tree.getroot()
our_div = None
for div in root.findall('.//div'):
    xml_id = div.get('{http://www.w3.org/XML/1998/namespace}id') or div.get('xml:id') or div.get('id')
    if xml_id == STANZA:
        our_div = div
        break

if our_div is None:
    print('stanza not found')
    raise SystemExit(1)

print('--- Serialized ab content ---')
for ab in our_div.findall('.//ab'):
    print(etree.tostring(ab, encoding='unicode', pretty_print=True))

print('\n--- Node listing (tag, xml:lang, text, tail, attributes) ---')
for ab in our_div.findall('.//ab'):
    ab_copy = etree.fromstring(etree.tostring(ab))
    for node in ab_copy.iter():
        tag = etree.QName(node.tag).localname if isinstance(node.tag, str) else node.tag
        lang = node.get('{http://www.w3.org/XML/1998/namespace}lang') or node.get('xml:lang') or node.get('lang')
        text = node.text
        tail = node.tail
        attrs = {k: v for k,v in node.attrib.items()}
        print(f'TAG={tag!s} LANG={lang!s} TEXT={text!r} TAIL={tail!r} ATTRS={attrs}')
    print('\n--- end ab ---\n')
