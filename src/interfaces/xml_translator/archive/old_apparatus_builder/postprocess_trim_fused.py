import argparse
import re
import unicodedata
from lxml import etree
from pathlib import Path

NS_TEI = 'http://www.tei-c.org/ns/1.0'
NS_XML = 'http://www.w3.org/XML/1998/namespace'
NS = {'tei': NS_TEI, 'xml': NS_XML}


def nfc(s: str) -> str:
    return unicodedata.normalize('NFC', str(s))


def strip_punct(s: str) -> str:
    return re.sub(r"[\.,;:·⸳]", '', s)


def collapse_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def norm_for_compare(s: str) -> str:
    s = nfc(s)
    s = strip_punct(s)
    s = collapse_ws(s)
    return re.sub(r"\s+", "", s)


def best_substring_window(target: str, source: str) -> str:
    """Return the substring of 'source' (original chars/spacing) that best matches 'target' (nospace).

    Compares on nospace, returns original substring boundaries.
    """
    t = norm_for_compare(target)
    s = nfc(source)
    s_ns = norm_for_compare(source)
    if not s_ns:
        return source
    tlen = len(t)
    if tlen == 0:
        return source
    # Map from nospace index to original string index
    ns_to_orig = []
    for idx, ch in enumerate(s):
        if ch.isspace():
            continue
        if ch in '.,;:·⸳':
            continue
        ns_to_orig.append(idx)
    best_sub = (0, len(s_ns))
    best_r = -1.0
    # limit windows to around target length ±2
    start_L = max(1, tlen - 2)
    end_L = min(len(s_ns), tlen + 2)
    for L in range(start_L, end_L + 1):
        for start in range(0, len(s_ns) - L + 1):
            sub = s_ns[start:start + L]
            r = _ratio(t, sub)
            if r > best_r:
                best_r = r
                best_sub = (start, start + L)
    a_ns, b_ns = best_sub
    if not ns_to_orig:
        return source
    a_orig = ns_to_orig[a_ns] if a_ns < len(ns_to_orig) else 0
    b_orig = (ns_to_orig[b_ns - 1] + 1) if (b_ns - 1) < len(ns_to_orig) and (b_ns - 1) >= 0 else len(s)
    return s[a_orig:b_orig]


def _ratio(a: str, b: str) -> float:
    # lightweight ratio; avoid importing difflib for small strings
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    # Jaccard over bigrams as a rough proxy
    def bigrams(x: str):
        return {x[i:i+2] for i in range(max(0, len(x) - 1))}
    A, B = bigrams(a), bigrams(b)
    if not A and not B:
        return 1.0 if a == b else 0.0
    inter = len(A & B)
    union = len(A | B) or 1
    return inter / union


def process(in_path: Path, out_path: Path, min_ratio: float = 0.80, overlength_factor: float = 1.4):
    tree = etree.parse(str(in_path))
    root = tree.getroot()
    changed = 0
    apps = root.xpath('.//tei:app', namespaces=NS)
    for app in apps:
        lem_el = app.find('./tei:lem', namespaces=NS)
        if lem_el is None:
            continue
        lem_text = ''.join(lem_el.xpath('.//text()', namespaces=NS)).strip()
        # Only attempt for single-token lemma (no spaces when normalized)
        if ' ' in collapse_ws(lem_text):
            continue
        t_norm = norm_for_compare(lem_text)
        if not t_norm:
            continue
        for rdg in app.xpath('./tei:rdg', namespaces=NS):
            rdg_text = ''.join(rdg.xpath('.//text()', namespaces=NS))
            s_norm = norm_for_compare(rdg_text)
            if not s_norm:
                continue
            # Skip if already equal after nospace compare
            if s_norm == t_norm:
                continue
            # Skip if reading is not significantly longer
            if len(s_norm) <= int(len(t_norm) * overlength_factor):
                continue
            # If reading contains repeated target at least twice (nospace), or best-window is very close, trim
            occurs = s_norm.count(t_norm)
            trimmed = best_substring_window(lem_text, rdg_text)
            trim_norm = norm_for_compare(trimmed)
            if occurs >= 2 or _ratio(t_norm, trim_norm) >= min_ratio:
                if trim_norm and trim_norm != s_norm:
                    # Replace rdg text content
                    # Clear children and set text
                    for child in list(rdg):
                        rdg.remove(child)
                    rdg.text = trimmed
                    changed += 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(out_path), encoding='utf-8', pretty_print=True)
    print(f"Post-processed {in_path} → {out_path} (trimmed {changed} readings)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', required=True, help='Input per-word apparatus XML (.v3.xml or raw)')
    ap.add_argument('--out', dest='out', required=True, help='Output path for trimmed XML')
    ap.add_argument('--min-ratio', type=float, default=0.80)
    ap.add_argument('--overlength-factor', type=float, default=1.4)
    args = ap.parse_args()
    process(Path(args.inp), Path(args.out), min_ratio=args.min_ratio, overlength_factor=args.overlength_factor)


if __name__ == '__main__':
    main()
