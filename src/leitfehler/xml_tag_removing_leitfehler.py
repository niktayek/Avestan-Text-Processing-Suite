import xml.etree.ElementTree as ET

# === CONFIG ===
input_file = "/home/nikta/Desktop/OCR/data/CAB/Yasna/static_yasna.xml"
output_file = "/home/nikta/Desktop/OCR/data/CAB/Yasna/res/static_yasna_cleaned.xml"

XML_NS = "http://www.w3.org/XML/1998/namespace"
XML_ID_KEY = f"{{{XML_NS}}}id"

# === PARSE XML ===
parser = ET.XMLParser(encoding="utf-8")
tree = ET.parse(input_file, parser=parser)
root = tree.getroot()

# === STEP 1: Strip namespaces from all tags ===
def strip_namespace(tag):
    return tag.split("}")[-1] if "}" in tag else tag

for elem in root.iter():
    elem.tag = strip_namespace(elem.tag)

# === STEP 2: Mark all elements that contain xml:id or have descendants with it ===
def mark_preserve(elem):
    preserve = XML_ID_KEY in elem.attrib
    for child in list(elem):
        if mark_preserve(child):
            preserve = True
    elem.set("_preserve", str(preserve))  # temporarily store this flag
    return preserve

mark_preserve(root)

# === STEP 3: Remove elements that are not marked for preservation ===
def prune_tree(elem):
    for child in list(elem):
        if child.get("_preserve") == "True":
            prune_tree(child)
        else:
            # Preserve text and tail
            if child.text:
                elem.text = (elem.text or '') + child.text
            if child.tail:
                if len(elem):
                    last = elem[-1]
                    last.tail = (last.tail or '') + child.tail
                else:
                    elem.text = (elem.text or '') + child.tail
            elem.remove(child)
    elem.attrib.pop("_preserve", None)  # cleanup temporary flag

prune_tree(root)

# === STEP 4: Rename xml:id to just "xml:id" (optional) ===
for elem in root.iter():
    if XML_ID_KEY in elem.attrib:
        elem.attrib["xml:id"] = elem.attrib.pop(XML_ID_KEY)

# === SAVE OUTPUT ===
tree.write(output_file, encoding="utf-8", xml_declaration=True)
print(f"✅ Final cleaned XML written to: {output_file}")
