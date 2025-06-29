import os
import xml.etree.ElementTree as ET
import pandas as pd
from collections import defaultdict

# === CONFIG ===
canonical_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/static_yasna.xml"
manuscript_dir = "/home/nikta/Desktop/OCR/data/CAB/Yasna/raw_XMLs"
output_csv = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/canonical_presence_matrix.csv"

# === Step 1: Load canonical stanza blocks ===
tree = ET.parse(canonical_path)
root = tree.getroot()
ns = {"xml": "http://www.w3.org/XML/1998/namespace"}

canonical_blocks = {}
for elem in root.findall(".//*[@xml:id]", namespaces=ns):
    xml_id = elem.attrib.get("{http://www.w3.org/XML/1998/namespace}id")
    if not xml_id:
        continue
    lines = elem.findall(".//l") or [elem]
    text = " ".join(l.text.strip() for l in lines if l.text)
    canonical_blocks[xml_id] = text.strip()

# === Step 2: Process each manuscript XML ===
presence_matrix = defaultdict(dict)
manuscripts = []

for filename in sorted(os.listdir(manuscript_dir)):
    if not filename.endswith(".xml"):
        continue
    ms_id = os.path.splitext(filename)[0]

    path = os.path.join(manuscript_dir, filename)
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"❌ Error in file {filename}: {e}")
        continue

    manuscripts.append(ms_id)
    found_ids = set()

    for elem in root.findall(".//*[@xml:id]", namespaces=ns):
        xml_id = elem.attrib.get("{http://www.w3.org/XML/1998/namespace}id")
        if not xml_id:
            continue
        found_ids.add(xml_id)

    for block_id in canonical_blocks:
        presence_matrix[block_id][ms_id] = "✅" if block_id in found_ids else "❌"

# === Step 3: Save as CSV ===
df = pd.DataFrame.from_dict(presence_matrix, orient="index")
df.index.name = "block_id"
df.to_csv(output_csv)

print(f"✅ Presence matrix saved to: {output_csv}")
