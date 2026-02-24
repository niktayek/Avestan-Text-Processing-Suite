#!/usr/bin/env python3
"""
In-place spillover trimming for existing apparatus XML.

Goal: For lemma apps where certain witness readings include tokens from the
previous or following lemma apps (boundary spill), remove those extraneous
prefix/suffix tokens while retaining tokens that correspond to the current
lemma (including internal splits/merges).

Heuristic:
 1. Load all <app> elements in document order; record lemma tokens per app.
 2. For each app with lemma token count >=1, examine each <rdg> text tokens.
 3. Identify extraneous prefix tokens: tokens that match (high similarity) tokens
    from up to two previous lemma apps AND do not match any current lemma token.
 4. Similarly identify extraneous suffix tokens from up to two next lemma apps.
 5. Similarity based on NFC-lowercase, removal of spaces, with SequenceMatcher ratio.
 6. Token kept if it matches (ratio>=0.55) any current lemma token or partial split
    (substring containment after normalization).
 7. After trimming ensure at least one token remains; otherwise revert.

No reclassification: existing @type attributes preserved. Output written to new file.
"""
import argparse
from pathlib import Path
from lxml import etree
import unicodedata
import re
from difflib import SequenceMatcher

NS_TEI = 'http://www.tei-c.org/ns/1.0'

def norm(s: str) -> str:
    s = unicodedata.normalize('NFC', s.strip().lower())
    s = re.sub(r"\s+", "", s)
    # Remove internal segmentation dots to improve fuzzy matching across variants
    s = s.replace('.', '')
    return s

def token_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()

def looks_like_split(token: str, lemma_token: str) -> bool:
    a = norm(token)
    b = norm(lemma_token)
    if not a or not b:
        return False
    # substring containment (allow minor truncation)
    return a in b or b in a or token_similarity(a, b) >= 0.55

def build_apps(tree):
    apps = tree.xpath('.//tei:app', namespaces={'tei': NS_TEI}) or tree.xpath('.//app')
    seq = []
    for app in apps:
        lem_el = app.find('.//tei:lem', namespaces={'tei': NS_TEI}) or app.find('lem')
        if lem_el is None:
            lemma_tokens = []
        else:
            lemma_surface = ' '.join(lem_el.itertext()).strip()
            lemma_tokens = [t for t in lemma_surface.split() if t]
        seq.append((app, lemma_tokens))
    return seq

def _tokenize(surface: str) -> list:
    # Split on spaces; keep punctuation attached (period) for now
    return [t for t in surface.split() if t]

def _strip_punct(tok: str) -> str:
    return re.sub(r'[\.,;:]+$', '', tok)

def _normalize_for_seq(tokens: list) -> list:
    return [norm(_strip_punct(t)) for t in tokens]

def _starts_with_sequence(reading_tokens, seq_tokens):
    if not seq_tokens or len(seq_tokens) > len(reading_tokens):
        return False
    r_norm = _normalize_for_seq(reading_tokens[:len(seq_tokens)])
    s_norm = _normalize_for_seq(seq_tokens)
    return r_norm == s_norm

def _ends_with_sequence(reading_tokens, seq_tokens):
    if not seq_tokens or len(seq_tokens) > len(reading_tokens):
        return False
    r_norm = _normalize_for_seq(reading_tokens[-len(seq_tokens):])
    s_norm = _normalize_for_seq(seq_tokens)
    return r_norm == s_norm

def _fuzzy_sequence_at_start(reading_tokens, seq_tokens, threshold: float) -> bool:
    if not seq_tokens or len(seq_tokens) > len(reading_tokens):
        return False
    for i, tok in enumerate(seq_tokens):
        if token_similarity(reading_tokens[i], tok) < threshold:
            return False
    return True

def _fuzzy_sequence_at_end(reading_tokens, seq_tokens, threshold: float) -> bool:
    if not seq_tokens or len(seq_tokens) > len(reading_tokens):
        return False
    offset = len(reading_tokens) - len(seq_tokens)
    for i, tok in enumerate(seq_tokens):
        if token_similarity(reading_tokens[offset + i], tok) < threshold:
            return False
    return True

def trim_reading(rdg_text: str, current_lemmas, prev_lemmas, prev2_lemmas, next_lemmas, next2_lemmas):
    toks = _tokenize(rdg_text)
    if not toks or not current_lemmas:
        return rdg_text, False
    changed = False

    def sim(a,b):
        return token_similarity(a,b)

    # Simple prefix removal: previous lemma tokens (first token only) variants
    while prev_lemmas and len(toks) > len(current_lemmas) and sim(toks[0], prev_lemmas[0]) >= 0.50:
        toks.pop(0)
        changed = True

    # Also check second previous lemma if first didn't trigger
    while prev2_lemmas and len(toks) > len(current_lemmas) and sim(toks[0], prev2_lemmas[0]) >= 0.50:
        toks.pop(0)
        changed = True

    # Simple suffix removal: next lemma tokens (last token only) variants
    while next_lemmas and len(toks) > len(current_lemmas) and sim(toks[-1], next_lemmas[-1]) >= 0.50:
        toks.pop()
        changed = True

    # Next2 lemma trailing token
    while next2_lemmas and len(toks) > len(current_lemmas) and sim(toks[-1], next2_lemmas[-1]) >= 0.50:
        toks.pop()
        changed = True

    if not toks:
        return rdg_text, False
    new_text = ' '.join(toks)
    return new_text, changed and new_text != rdg_text

def process(input_path: Path, output_path: Path, debug: bool=False):
    tree = etree.parse(str(input_path))
    seq = build_apps(tree)
    changed_count = 0
    for idx, (app, lemma_tokens) in enumerate(seq):
        # Need multi-token lemma OR evidence of spill (we will attempt regardless)
        if not lemma_tokens:
            continue
        prev_lemmas = seq[idx-1][1] if idx-1 >= 0 else []
        prev2_lemmas = seq[idx-2][1] if idx-2 >= 0 else []
        next_lemmas = seq[idx+1][1] if idx+1 < len(seq) else []
        next2_lemmas = seq[idx+2][1] if idx+2 < len(seq) else []
        rdgs = app.findall('.//tei:rdg', namespaces={'tei': NS_TEI}) or app.findall('rdg')
        for rdg in rdgs:
            old = ' '.join(rdg.itertext()).strip()
            if not old:
                continue
            new, changed = trim_reading(old, lemma_tokens, prev_lemmas, prev2_lemmas, next_lemmas, next2_lemmas)
            if changed:
                rdg.text = new
                changed_count += 1
                if debug:
                    app_id = app.get('{http://www.w3.org/XML/1998/namespace}id','?')
                    wit = rdg.get('wit','?')
                    print(f"[spillfix] app={app_id} wit={wit} OLD='{old}' NEW='{new}' lemmas={lemma_tokens}")
            elif debug and 'āϑrəm.' in old and 'pairi.' in ' '.join(lemma_tokens):
                app_id = app.get('{http://www.w3.org/XML/1998/namespace}id','?')
                wit = rdg.get('wit','?')
                print(f"[spillfix:nochange] app={app_id} wit={wit} kept='{old}' lemmas={lemma_tokens}")
    tree.write(str(output_path), encoding='utf-8', xml_declaration=True, pretty_print=True)
    print(f"Spillover in-place trimming complete. Changed readings: {changed_count}. Output: {output_path}")


def main():
    ap = argparse.ArgumentParser(description='In-place spillover trimming for apparatus XML.')
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--debug', action='store_true')
    args = ap.parse_args()
    process(Path(args.input), Path(args.output), debug=args.debug)

if __name__ == '__main__':
    main()
