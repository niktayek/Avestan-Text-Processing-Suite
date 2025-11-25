#!/usr/bin/env python3
"""
Fix specific alignment issues in apparatus XML.

Addresses known problematic witness alignments that the DP algorithm mishandles.
"""

import argparse
from lxml import etree
from pathlib import Path

NS_TEI = 'http://www.tei-c.org/ns/1.0'
NS_XML = 'http://www.w3.org/XML/1998/namespace'


def fix_alignments(input_path: Path, output_path: Path):
    """Apply targeted fixes to specific apparatus entries."""
    tree = etree.parse(str(input_path))
    root = tree.getroot()
    
    # Detect namespace
    nsmap = root.nsmap
    ns = {'tei': nsmap[None]} if None in nsmap else {}
    
    fixes_applied = []
    
    # Fix 1: app-Y9.1c-0-2 ms0005 - add missing ādəm.
    app = root.xpath('.//tei:app[@xml:id="app-Y9.1c-0-2"]', namespaces=ns) if ns else root.xpath('.//app[@xml:id="app-Y9.1c-0-2"]')
    if app:
        app = app[0]
        rdg = app.xpath('.//tei:rdg[@wit="#ms0005"]', namespaces=ns) if ns else app.xpath('.//rdg[@wit="#ms0005"]')
        if rdg:
            rdg = rdg[0]
            old_text = ''.join(rdg.itertext()).strip()
            if old_text == 'pərəsat̰.':
                rdg.text = 'ādəm. pərəsat̰.'
                fixes_applied.append(f"app-Y9.1c-0-2 ms0005: '{old_text}' → 'ādəm. pərəsat̰.'")
    
    # Fix 2: app-Y9.1d-9-10 ms0235 - remove aməšahe. spillover
    app = root.xpath('.//tei:app[@xml:id="app-Y9.1d-9-10"]', namespaces=ns) if ns else root.xpath('.//app[@xml:id="app-Y9.1d-9-10"]')
    if app:
        app = app[0]
        rdg = app.xpath('.//tei:rdg[@wit="#ms0235"]', namespaces=ns) if ns else app.xpath('.//rdg[@wit="#ms0235"]')
        if rdg:
            rdg = rdg[0]
            old_text = ''.join(rdg.itertext()).strip()
            if 'aməšahe.' in old_text:
                rdg.text = old_text.replace(' aməšahe.', '').replace('aməšahe.', '').strip()
                fixes_applied.append(f"app-Y9.1d-9-10 ms0235: '{old_text}' → '{rdg.text}'")
    
    # Fix 3: app-Y9.3b-10-11 ms0235 - merge with next app
    app1 = root.xpath('.//tei:app[@xml:id="app-Y9.3b-10-11"]', namespaces=ns) if ns else root.xpath('.//app[@xml:id="app-Y9.3b-10-11"]')
    app2 = root.xpath('.//tei:app[@xml:id="app-Y9.3b-11-12"]', namespaces=ns) if ns else root.xpath('.//app[@xml:id="app-Y9.3b-11-12"]')
    if app1 and app2:
        app1, app2 = app1[0], app2[0]
        rdg1 = app1.xpath('.//tei:rdg[@wit="#ms0235"]', namespaces=ns) if ns else app1.xpath('.//rdg[@wit="#ms0235"]')
        rdg2 = app2.xpath('.//tei:rdg[@wit="#ms0235"]', namespaces=ns) if ns else app2.xpath('.//rdg[@wit="#ms0235"]')
        if rdg1 and rdg2:
            rdg1, rdg2 = rdg1[0], rdg2[0]
            text1 = ''.join(rdg1.itertext()).strip()
            text2 = ''.join(rdg2.itertext()).strip()
            if text1 == 'ərə.' and text2 == 'nāuuaicit̰.':
                rdg1.text = 'ərənāuuaicit̰.'
                rdg2.text = ''  # Empty second reading since it's merged into first
                fixes_applied.append(f"app-Y9.3b-10-11 & app-Y9.3b-11-12 ms0235: merged 'ərə.' + 'nāuuaicit̰.' → 'ərənāuuaicit̰.' in first app")
    
    # Fix 4: app-Y9.7b-7-8 and app-Y9.7b-8-9 ms0015 - merge hā + ahmāi
    app1 = root.xpath('.//tei:app[@xml:id="app-Y9.7b-7-8"]', namespaces=ns) if ns else root.xpath('.//app[@xml:id="app-Y9.7b-7-8"]')
    app2 = root.xpath('.//tei:app[@xml:id="app-Y9.7b-8-9"]', namespaces=ns) if ns else root.xpath('.//app[@xml:id="app-Y9.7b-8-9"]')
    if app1 and app2:
        app1, app2 = app1[0], app2[0]
        rdg1 = app1.xpath('.//tei:rdg[@wit="#ms0015"]', namespaces=ns) if ns else app1.xpath('.//rdg[@wit="#ms0015"]')
        rdg2 = app2.xpath('.//tei:rdg[@wit="#ms0015"]', namespaces=ns) if ns else app2.xpath('.//rdg[@wit="#ms0015"]')
        if rdg1 and rdg2:
            rdg1, rdg2 = rdg1[0], rdg2[0]
            text1 = ''.join(rdg1.itertext()).strip()
            text2 = ''.join(rdg2.itertext()).strip()
            if text1 == 'hā' and text2 == 'ahmāi.':
                rdg1.text = 'hā.ahmāi.'
                # For rdg2, need to get correct reading for aṣ̌iš. lemma - check neighboring witnesses
                # Most have aṣ̌əš. so use that
                rdg2.text = 'aṣ̌iš.'
                fixes_applied.append(f"app-Y9.7b-7-8 & app-Y9.7b-8-9 ms0015: merged 'hā' + 'ahmāi.' → 'hā.ahmāi.' in first app, restored 'aṣ̌iš.' in second")
    
    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(output_path), encoding='utf-8', xml_declaration=True, pretty_print=True)
    
    print(f"✅ Applied {len(fixes_applied)} alignment fixes:")
    for fix in fixes_applied:
        print(f"   • {fix}")
    print(f"\nOutput written to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Fix specific alignment issues in apparatus XML')
    parser.add_argument('--input', required=True, help='Input apparatus XML file')
    parser.add_argument('--output', required=True, help='Output fixed apparatus XML file')
    args = parser.parse_args()
    
    fix_alignments(Path(args.input), Path(args.output))


if __name__ == '__main__':
    main()
