import re
from pathlib import Path
import xml.dom.minidom

# === File paths ===
input_path = Path("/home/nikta/Desktop/OCR/data/CAB/Yasna/static_yasna.xml")
output_path = Path("/home/nikta/Desktop/OCR/data/CAB/Yasna/static_yasna_cleaned.xml")

# === Load input XML ===
with input_path.open(encoding="utf-8") as f:
    text = f.read()

# === Step 1: Remove <lb break="no"/> and <pb break="no"/>
text = re.sub(r'<lb break="no"\s*/>\s*', '', text)
text = re.sub(r'<pb[^>]*break="no"[^>]*/>\s*', '', text)

# === Step 2: Unwrap <supplied>…</supplied> (preserve content)
text = re.sub(r'<supplied[^>]*>(.*?)</supplied>', r'\1', text, flags=re.DOTALL)

# === Step 3: Remove <abbr>…</abbr> completely (with content)
text = re.sub(r'<abbr\b[^>]*>[\s\S]*?</abbr>', '', text)

# === Step 4: Remove <ab> or <foreign> blocks with xml:lang="Pahl" or "Pers"
text = re.sub(
    r'<(ab|foreign)\b[^>]*xml:lang=["\'](?:Pahl|Pers)["\'][^>]*>[\s\S]*?</\1>',
    '',
    text,
    flags=re.DOTALL
)

# === Step 5: Normalize whitespace inside text nodes only (not tags)
text = re.sub(r'>\s+([^<\s][^<]*?)\s+<', r'>\1<', text)

# === Step 6: Normalize special characters
text = text.replace("⸳", ".")
text = text.replace("⁛", "")

# === Step 7: Pretty-print the final result
try:
    dom = xml.dom.minidom.parseString(text)
    pretty_xml = dom.toprettyxml(indent="  ")
except Exception as e:
    print("⚠️ Pretty-print failed:", e)
    pretty_xml = text

# === Save cleaned and formatted XML
with output_path.open("w", encoding="utf-8") as f:
    f.write(pretty_xml)

print(f"✅ Cleaned and formatted XML saved to: {output_path.resolve()}")
