#!/usr/bin/env python3
"""
Post-process a span-based apparatus XML to split multi-token lemma <app> entries
into single-token <app> entries when there is no evidence of an actual merge/split
in any witness.

Heuristic: A multi-token lemma app is retained if ANY reading either
  - Has fewer tokens than the lemma (merge), OR
  - Has more tokens than the lemma (split/expansion), OR
  - Shows a token count mismatch after simple whitespace tokenization.
Otherwise (all readings have exactly the same token count as lemma), we split
into per-token apps, aligning token indices 1:1.

Types (@type) are preserved for each token portion; if a reading was marked "meaningful"
for the whole span but we split, we downgrade to "trivial" if token text equals lemma token,
otherwise keep "meaningful".
"""
import argparse
from lxml import etree
from pathlib import Path
from typing import List

NS_TEI = 'http://www.tei-c.org/ns/1.0'
NS_XML = 'http://www.w3.org/XML/1998/namespace'
NS = {None: NS_TEI, 'xml': NS_XML}

def tokenize(text: str) -> List[str]:
    return [t for t in text.strip().split() if t]

def should_keep_multispan(lem_tokens: List[str], rdg_texts: List[str]) -> bool:
    L = len(lem_tokens)
    for rt in rdg_texts:
        if rt.strip() == '':
            # missing reading still compatible; skip
            continue
        toks = tokenize(rt)
        if len(toks) != L:
            return True  # merge or split or expansion
    return False  # all readings 1:1; can split

def split_app(app: etree._Element, root_div: etree._Element, id_counter_start: int) -> int:
    # Returns number of new apps created, modifies tree (app removed)
    lem_el = app.find('.//{http://www.tei-c.org/ns/1.0}lem') or app.find('lem')
    if lem_el is None:
        return 0
    lem_tokens = tokenize(' '.join(lem_el.itertext()))
    rdgs = app.findall('.//{http://www.tei-c.org/ns/1.0}rdg') or app.findall('rdg')
    rdg_text_lists = [tokenize(' '.join(r.itertext())) for r in rdgs]
    # Create per-token apps
    created = 0
    for ti, lem_tok in enumerate(lem_tokens):
        new_app = etree.SubElement(root_div, f'{{{NS_TEI}}}app')
        new_app.set(f'{{{NS_XML}}}id', f"{app.get(f'{{{NS_XML}}}id','split')}-{ti}")
        new_lem = etree.SubElement(new_app, f'{{{NS_TEI}}}lem')
        new_lem.text = lem_tok
        for r, toks in zip(rdgs, rdg_text_lists):
            new_rdg = etree.SubElement(new_app, f'{{{NS_TEI}}}rdg')
            for attr in r.attrib:
                new_rdg.set(attr, r.get(attr))
            if ti < len(toks):
                new_rdg.text = toks[ti]
                # Adjust type if original was meaningful but token matches lemma
                orig_type = r.get('type','')
                if orig_type == 'meaningful' and toks[ti].strip() == lem_tok.strip():
                    new_rdg.set('type', 'trivial')
            else:
                new_rdg.text = ''
                new_rdg.set('type', 'missing')
        created += 1
    # Remove original app
    parent = app.getparent()
    parent.remove(app)
    return created


def process(input_path: Path, output_path: Path):
    tree = etree.parse(str(input_path))
    root = tree.getroot()
    # Find body div containing apps
    apps = root.xpath('.//tei:app', namespaces={'tei': NS_TEI}) or root.xpath('.//app')
    div = None
    if apps:
        div = apps[0].getparent()
        while div is not None and etree.QName(div.tag).localname != 'div':
            div = div.getparent()
    if div is None:
        print("No <app> entries found.")
        return
    to_split = []
    for app in apps:
        lem_el = app.find('.//tei:lem', namespaces={'tei': NS_TEI}) or app.find('lem')
        if lem_el is None:
            continue
        lem_text = ' '.join(lem_el.itertext()).strip()
        lem_tokens = tokenize(lem_text)
        if len(lem_tokens) <= 1:
            continue
        rdgs = app.findall('.//tei:rdg', namespaces={'tei': NS_TEI}) or app.findall('rdg')
        rdg_texts = [' '.join(r.itertext()).strip() for r in rdgs]
        if not should_keep_multispan(lem_tokens, rdg_texts):
            to_split.append(app)
    total_created = 0
    for app in to_split:
        total_created += split_app(app, div, total_created)
    tree.write(str(output_path), encoding='utf-8', xml_declaration=True, pretty_print=True)
    print(f"Refined apparatus written: {output_path}\nOriginal apps: {len(apps)} Split apps added: {total_created}")


def main():
    ap = argparse.ArgumentParser(description="Split non-merge multi-token lemma apparatus entries")
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    process(Path(args.input), Path(args.output))

if __name__ == '__main__':
    main()
