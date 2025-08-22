import xml.etree.ElementTree as ET
import re

# === CONFIG ===
input_file = "/home/nikta/Desktop/OCR/data/CAB/Yasna/raw_XMLs_fixed/0088.xml"
output_txt = "/home/nikta/Desktop/OCR/data/CAB/Yasna/txt/0088.txt"

XML_NS = "http://www.w3.org/XML/1998/namespace"
XML_ID_KEY = f"{{{XML_NS}}}id"

# Match only IDs like Y0.1, Y9.12, etc.
VALID_MOTHER_ID = re.compile(r"^Y\d+\.\d+$", re.IGNORECASE)

# === Parse XML ===
parser = ET.XMLParser(encoding="utf-8")
tree = ET.parse(input_file, parser=parser)
root = tree.getroot()

# Remove namespaces from tag names
for elem in root.iter():
    elem.tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

# === Collect only stanza-level <div> with xml:id like Y#.#
blocks = []
for elem in root.iter():
    if elem.tag != "div":
        continue
    xml_id = elem.attrib.get(XML_ID_KEY) or elem.attrib.get("xml:id")
    if xml_id and VALID_MOTHER_ID.match(xml_id.strip()):
        text = "".join(elem.itertext()).strip()
        if text:
            blocks.append((xml_id.strip(), text))

# === Write to file in document order
with open(output_txt, "w", encoding="utf-8") as out:
    for block_id, text in blocks:
        out.write(f"{block_id}\t{text}\n")

print(f"✅ Mother ID blocks written in correct order to: {output_txt}")
