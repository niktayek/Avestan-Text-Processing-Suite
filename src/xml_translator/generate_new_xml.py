import json

from lxml import etree

from src.cab.cab_xml import CABXML
from src.escriptorium.ocr_xml import OCRXML
from src.xml_translator.config import (
    CAB_XML_PATH,
    OCR_XML_DIR,
    MATCH_JSON_PATH,
    NEW_XML_PATH,
)


def main():
    cab_text = CABXML(CAB_XML_PATH)
    ocr_text = OCRXML(OCR_XML_DIR)

    with open(MATCH_JSON_PATH, "r") as f:
        matches = json.loads(f.read())

    tree = etree.parse(CAB_XML_PATH)
    xml = tree.getroot()
    empty_all_abs(xml)
    prev_match_ind = 0
    for match_ind in range(len(matches)):
        prev_cab_id = cab_text[matches[prev_match_ind]['cab_ind']].address.id
        cur_cab_id = cab_text[matches[match_ind]['cab_ind']].address.id
        if prev_cab_id != cur_cab_id:
            # ocr_segment = ' '.join(word for _, word in ocr_text[matches[prev_match_ind]['ocr_ind']:matches[match_ind]['ocr_ind']])
            ocr_segment = generate_ocr_segment(ocr_text, matches[prev_match_ind]['ocr_ind'], matches[match_ind]['ocr_ind'])
            replace_text(xml, prev_cab_id, ocr_segment)
            prev_match_ind = match_ind
    ocr_segment = ' '.join(word for _, word in ocr_text[matches[prev_match_ind]['ocr_ind']:matches[-1]['ocr_ind']])
    cur_cab_id = cab_text[matches[-1]['cab_ind']].address.id
    replace_text(xml, cur_cab_id, ocr_segment)

    tree.write(NEW_XML_PATH, encoding="utf-8", xml_declaration=True)

def replace_text(xml, cab_id, ocr_segment):
    ab = xml.find(f'.//ab[@{{http://www.w3.org/XML/1998/namespace}}id="{cab_id}"]')
    if ab is None:
        return
    # ab.text = ocr_segment
    for item in ocr_segment:
        if item.startswith("<page"):
            ab.append(etree.Element('pb', n=item.split()[1][:-2]))
        elif item.startswith("<line"):
            ab.append(etree.Element("lb", n=item.split()[1][:-2]))
        else:
            if len(ab) > 0:
                ab[-1].tail = ' '.join([ab[-1].tail or "", item])
            else:
                ab.text = " ".join([ab.text or "", item])

def empty_all_abs(xml):
    for ab in xml.findall(".//ab"):
        for child in ab:
            ab.remove(child)
        ab.text = ""


def generate_ocr_segment(ocr_text, start, end):
    prev_address = ocr_text[start].address
    ocr_segment = []
    if start == 0 or prev_address.page != ocr_text[start - 1].address.page:
        ocr_segment.append(f'<page {prev_address.page}/>')
    if start == 0 or prev_address.line != ocr_text[start - 1].address.line:
        ocr_segment.append(f'<line {prev_address.line + 1}/>')
    ocr_segment.append(ocr_text[start].word)
    for i in range(start + 1, end):
        cur_address = ocr_text[i].address
        if cur_address.page != prev_address.page:
            ocr_segment.append(f'<page {cur_address.page}/>')
        if cur_address.line != prev_address.line:
            ocr_segment.append(f'<line {cur_address.line + 1}/>')
        ocr_segment.append(ocr_text[i].word)
        prev_address = cur_address
    return ocr_segment

if __name__ == "__main__":
    main()
