import os
import xml.etree.ElementTree as ET
import pandas as pd

# === CONFIG ===
ocr_folder = "/home/nikta/Desktop/OCR/data/CAB/Yasna/raw_XMLs_fixed"  # Folder with all OCR XML files
output_csv = "/home/nikta/Desktop/OCR/data/CAB/Yasna/ocr_blocks_combined.csv"

# === Function to extract block ID and text ===
def get_all_ab_blocks(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        blocks = []
        for ab in root.findall(".//ab"):  # ✅ No 'tei:' prefix
            # xml:id attribute still uses XML namespace
            block_id = ab.attrib.get("{http://www.w3.org/XML/1998/namespace}id")
            text = "".join(ab.itertext()).strip()
            if block_id and text:
                blocks.append((block_id, text))
        return blocks
    except ET.ParseError as e:
        print(f"⚠️ Failed to parse {xml_file}: {e}")
        return []

# === Collect blocks from all XML files ===
all_blocks = []
for fname in os.listdir(ocr_folder):
    if fname.endswith(".xml"):
        filepath = os.path.join(ocr_folder, fname)
        print(f"🔍 Parsing {fname} ...")
        blocks = get_all_ab_blocks(filepath)
        all_blocks.extend(blocks)

# === Save to CSV ===
df = pd.DataFrame(all_blocks, columns=["block_id", "ocr_text"])
df.to_csv(output_csv, index=False)
print(f"✅ OCR blocks saved to: {output_csv}")
