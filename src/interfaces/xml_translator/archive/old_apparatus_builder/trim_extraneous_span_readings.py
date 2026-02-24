#!/usr/bin/env python3
"""
Trim extraneous witness tokens included in multi-token lemma span readings.

Scenario: A multi-token lemma <lem> has N tokens, but some <rdg> text
contains tokens belonging to previous or subsequent lemma spans (spillover),
producing over-extended readings (e.g., previous lemma token prepended,
next lemma tokens appended).

Approach (non-invasive): For each multi-token lemma app, and each reading:
  - Tokenize lemma (L tokens) and reading (R tokens, R >= 1).
  - If R <= L: leave unchanged.
  - If R > L: slide a window of length L across reading tokens and compute
    alignment score: sum of per-position normalized similarity + bonus if
    punctuation/dot structure matches.
  - Choose best scoring window; replace reading text with original surface
    tokens from that window joined by space.
  - Preserve existing @type attribute (no reclassification logic change).

Normalization: lowercase, NFC, remove spaces; punctuation kept for dot-match bonus.

Outputs a new apparatus XML with trimmed readings.
"""
import argparse
import unicodedata
import re
from pathlib import Path
from lxml import etree
from difflib import SequenceMatcher

NS_TEI = 'http://www.tei-c.org/ns/1.0'

def norm_token(t: str) -> str:
    t = unicodedata.normalize('NFC', t.strip().lower())
    # retain trailing dots for dot structure matching separately
    return re.sub(r'\s+', '', t)

def dot_pattern(t: str) -> str:
    return ''.join(ch for ch in t if ch == '.')

def score_alignment(lem_tokens, rdg_window):
    score = 0.0
    for lt, rt in zip(lem_tokens, rdg_window):
        lt_n = norm_token(lt)
        rt_n = norm_token(rt)
        sim = SequenceMatcher(None, lt_n, rt_n).ratio()
        # Ensure minimal contribution for faint similarity to avoid zeroing
        sim = max(sim, 0.05) if sim > 0 else 0.0
        score += sim
        # dot pattern bonus
        if dot_pattern(lt) == dot_pattern(rt):
            score += 0.05
    return score

def tokenize_surface(t: str):
    return [tok for tok in t.split() if tok]

def process(input_path: Path, output_path: Path):
    tree = etree.parse(str(input_path))
    root = tree.getroot()
    apps = root.xpath('.//tei:app', namespaces={'tei': NS_TEI}) or root.xpath('.//app')
    trimmed_count = 0
    affected_witnesses = 0
    for app in apps:
        lem_el = app.find('.//tei:lem', namespaces={'tei': NS_TEI}) or app.find('lem')
        if lem_el is None:
            continue
        lem_surface = ' '.join(lem_el.itertext()).strip()
        lem_tokens = tokenize_surface(lem_surface)
        L = len(lem_tokens)
        if L <= 1:
            continue  # single-token lemma not processed
        rdgs = app.findall('.//tei:rdg', namespaces={'tei': NS_TEI}) or app.findall('rdg')
        for rdg in rdgs:
            txt = ' '.join(rdg.itertext()).strip()
            if not txt:
                continue
            rdg_tokens = tokenize_surface(txt)
            R = len(rdg_tokens)
            if R <= L:
                continue
            # Slide window
            best_score = -1.0
            best_window = rdg_tokens[:L]
            for start in range(0, R - L + 1):
                window = rdg_tokens[start:start+L]
                s = score_alignment(lem_tokens, window)
                if s > best_score:
                    best_score = s
                    best_window = window
            if best_window != rdg_tokens[:L] or R != L:
                # Replace reading text surface with best window
                rdg.text = ' '.join(best_window)
                trimmed_count += 1
                affected_witnesses += 1
    tree.write(str(output_path), encoding='utf-8', xml_declaration=True, pretty_print=True)
    print(f"Trimmed readings: {trimmed_count}\nAffected witnesses (rdg entries): {affected_witnesses}\nOutput: {output_path}")

def main():
    ap = argparse.ArgumentParser(description='Trim spillover tokens in multi-token lemma readings.')
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    process(Path(args.input), Path(args.output))

if __name__ == '__main__':
    main()
