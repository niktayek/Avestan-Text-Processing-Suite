import argparse
from pathlib import Path
from copy import deepcopy
from lxml import etree

NS_TEI = 'http://www.tei-c.org/ns/1.0'
NS_XML = 'http://www.w3.org/XML/1998/namespace'
NS = {'tei': NS_TEI, 'xml': NS_XML}


def ensure_taxonomy(header: etree._Element):
    enc = header.find('.//tei:encodingDesc', namespaces=NS)
    if enc is None:
        enc = etree.SubElement(header, f'{{{NS_TEI}}}encodingDesc')
    tax = enc.find('.//tei:taxonomy[@xml:id="varClass"]', namespaces=NS)
    if tax is None:
        tax = etree.SubElement(enc, f'{{{NS_TEI}}}taxonomy')
        tax.set(f'{{{NS_XML}}}id', 'varClass')
        # Insert categories matching annotator output
        for cat in ['variants', 'readings', 'missing', 'unknown']:
            c = etree.SubElement(tax, f'{{{NS_TEI}}}category')
            c.set(f'{{{NS_XML}}}id', cat)
            c.text = cat.capitalize()
    else:
        # Ensure expected categories exist
        existing = {c.get(f'{{{NS_XML}}}id') for c in tax.findall('./tei:category', namespaces=NS)}
        for cat in ['variants', 'readings', 'missing', 'unknown']:
            if cat not in existing:
                c = etree.SubElement(tax, f'{{{NS_TEI}}}category')
                c.set(f'{{{NS_XML}}}id', cat)
                c.text = cat.capitalize()


def build_combined(title: str) -> etree._ElementTree:
    root = etree.Element(f'{{{NS_TEI}}}TEI', nsmap={None: NS_TEI, 'xml': NS_XML})
    header = etree.SubElement(root, f'{{{NS_TEI}}}teiHeader')
    fileDesc = etree.SubElement(header, f'{{{NS_TEI}}}fileDesc')
    titleStmt = etree.SubElement(fileDesc, f'{{{NS_TEI}}}titleStmt')
    titleEl = etree.SubElement(titleStmt, f'{{{NS_TEI}}}title')
    titleEl.text = title
    pubStmt = etree.SubElement(fileDesc, f'{{{NS_TEI}}}publicationStmt')
    etree.SubElement(pubStmt, f'{{{NS_TEI}}}p').text = 'Generated automatically'
    sourceDesc = etree.SubElement(fileDesc, f'{{{NS_TEI}}}sourceDesc')
    etree.SubElement(sourceDesc, f'{{{NS_TEI}}}p').text = 'Combined from multiple TEI apparatus files'

    # Ensure taxonomy exists exactly once
    ensure_taxonomy(header)

    text = etree.SubElement(root, f'{{{NS_TEI}}}text')
    body = etree.SubElement(text, f'{{{NS_TEI}}}body')
    return etree.ElementTree(root)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in-dir', required=True, help='Directory containing *.v3.xml apparatus files')
    ap.add_argument('--out', required=True, help='Output combined TEI path')
    ap.add_argument('--title', required=True, help='Title for combined TEI')
    ap.add_argument('--include-pattern', required=False, help='Comma-separated glob patterns to include (relative to in-dir). If omitted, includes all *.v3.xml')
    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tree = build_combined(args.title)
    root = tree.getroot()
    body = root.find('.//tei:body', namespaces=NS)

    patterns = []
    if args.include_pattern:
        patterns = [p.strip() for p in args.include_pattern.split(',') if p.strip()]
    files = []
    if patterns:
        for pat in patterns:
            files.extend(sorted(in_dir.glob(pat)))
        # de-duplicate while preserving order
        seen = set()
        uniq = []
        for f in files:
            if f not in seen:
                uniq.append(f)
                seen.add(f)
        files = uniq
    else:
        files = sorted(in_dir.glob('*.v3.xml'))
    merged = 0
    for fpath in files:
        try:
            src = etree.parse(str(fpath))
        except Exception:
            continue
        # Create div for this file
        stem = fpath.with_suffix('')  # remove only .xml; leaves *.v3
        stem_str = stem.name
        div = etree.SubElement(body, f'{{{NS_TEI}}}div')
        div.set(f'{{{NS_XML}}}id', f'from-{stem_str}')
        head = etree.SubElement(div, f'{{{NS_TEI}}}head')
        head.text = stem_str
        # Append all apps in order
        apps = src.xpath('.//tei:app', namespaces=NS)
        for app in apps:
            app_copy = deepcopy(app)
            # Ensure unique xml:ids by prefixing with source stem
            def _prefix_ids(el):
                xmlid = el.get(f'{{{NS_XML}}}id')
                if xmlid:
                    el.set(f'{{{NS_XML}}}id', f'{stem_str}__{xmlid}')
                for child in el:
                    _prefix_ids(child)
            _prefix_ids(app_copy)
            div.append(app_copy)
        merged += 1

    tree.write(str(out_path), encoding='utf-8', pretty_print=True, xml_declaration=True)
    print(f"Combined {merged} input files into {out_path}")


if __name__ == '__main__':
    main()
