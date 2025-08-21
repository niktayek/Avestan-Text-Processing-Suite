import xml.etree.ElementTree as ET
import re
from xml.dom import minidom
import os

input_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/static_yasna.xml"
output_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/raw_XMLs_fixed/normalized/static_yasna_normalized.xml"

ns = {"xml": "http://www.w3.org/XML/1998/namespace"}
ET.register_namespace('', "http://www.tei-c.org/ns/1.0")

def normalize_id(original_id):
    return original_id.strip() if original_id else original_id

def clean_element(elem):
    tags_to_remove = {"abbr", "note", "foreign", "app", "rdg", "seg"}
    lang_filtered = {"ab", "foreign"}

    children = list(elem)
    for child in children:
        clean_element(child)

        tag_name = child.tag.split("}")[-1]
        lang = child.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")

        if tag_name == "lb" and child.attrib.get("break") == "no":
            elem.remove(child)
            continue
        if tag_name == "pb" and child.attrib.get("break") == "no":
            elem.remove(child)
            continue
        if tag_name == "supplied":
            tail = (child.text or '') + (child.tail or '')
            idx = list(elem).index(child)
            elem.remove(child)
            if tail:
                if idx > 0:
                    prev = list(elem)[idx - 1]
                    prev.tail = (prev.tail or '') + tail
                else:
                    elem.text = (elem.text or '') + tail
            continue
        if tag_name in tags_to_remove:
            elem.remove(child)
            continue
        if tag_name in lang_filtered and lang in {"Pahl", "Pers"}:
            elem.remove(child)
            continue

def process():
    tree = ET.parse(input_path)
    root = tree.getroot()

    for elem in root.iter():
        xml_id = elem.attrib.get("{http://www.w3.org/XML/1998/namespace}id")
        if xml_id:
            elem.set("{http://www.w3.org/XML/1998/namespace}id", normalize_id(xml_id))

    clean_element(root)
    raw = ET.tostring(root, encoding="unicode")
    try:
        pretty = minidom.parseString(raw).toprettyxml(indent="  ")
    except Exception:
        pretty = raw

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(pretty)

    print(f"✅ Cleaned static Yasna saved to: {output_path}")

if __name__ == "__main__":
    process()
