# === CONFIG ===
import re
import xml.etree.ElementTree as ET

input_file = "/home/nikta/Desktop/OCR/data/CAB/Yasna/raw_XMLs_fixed/0005.xml"
output_txt = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/static_yasna.txt"

XML_NS = "http://www.w3.org/XML/1998/namespace"
XML_ID_KEY = f"{{{XML_NS}}}id"
VALID_BLOCK_ID = re.compile(r"^Y\d+\.\d+[a-z]?$", re.IGNORECASE)


# === Parse and clean ===
parser = ET.XMLParser(encoding="utf-8")
tree = ET.parse(input_file, parser=parser)
root = tree.getroot()

for elem in root.iter():
    elem.tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

# === Extract block_id + text ===
blocks = []
for ab in root.findall(".//ab"):
    block_id = ab.attrib.get(XML_ID_KEY) or ab.attrib.get("xml:id")
    if block_id and VALID_BLOCK_ID.match(block_id.strip()):
        text = "".join(ab.itertext()).strip()
        if text:
            blocks.append((block_id.strip(), text))

# === Write to TXT ===
with open(output_txt, "w", encoding="utf-8") as out:
    for block_id, text in blocks:
        out.write(f"{block_id}\t{text}\n")

print(f" Cleaned blocks written to: {output_txt}")