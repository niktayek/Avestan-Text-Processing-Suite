import os
import xml.etree.ElementTree as ET

from xml.sax.saxutils import escape

from_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/raw_XMLs"
to_path = "/home/nikta/Desktop/OCR/data/CAB/Yasna/raw_XMLs_fixed"

os.makedirs(to_path, exist_ok=True)


def try_fix(content):
    # Escape standalone & characters
    content = content.replace("&", "&amp;")

    # Basic trimming of trailing garbage after root close
    if "</TEI>" in content:
        content = content.split("</TEI>")[0] + "</TEI>"
    elif "</tei:TEI>" in content:
        content = content.split("</tei:TEI>")[0] + "</tei:TEI>"

    return content


for fname in os.listdir(from_path):
    if not fname.endswith(".xml"):
        continue

    file_path = os.path.join(from_path, fname)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Try to parse as-is
    try:
        ET.fromstring(content)
        fixed_path = os.path.join(to_path, fname)
        with open(fixed_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f" OK: {fname}")
        continue
    except ET.ParseError:
        pass

    # Try fixing
    fixed_content = try_fix(content)
    try:
        ET.fromstring(fixed_content)
        fixed_path = os.path.join(to_path, fname)
        with open(fixed_path, "w", encoding="utf-8") as f:
            f.write(fixed_content)
        print(f"🔧 Fixed: {fname}")
    except ET.ParseError as e:
        print(f" Still broken: {fname} — {e}")
