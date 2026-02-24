#!/usr/bin/env python3
"""
Enhanced spillover trimming for multi-token lemma apparatus entries.

Detect and remove tokens from readings that belong to adjacent lemma spans:
Example:
  Lemma: pairi. yaōždaϑəṇtəm.
  Reading: āϑrəm. pairi.ẏaoždaϑəṇ. təm. gāϑā̊.šca. srāuuaṇtəm.
Remove prefix 'āϑrəm.' (previous lemma) and suffix 'gāϑā̊.šca. srāuuaṇtəm.' (next lemmas),
producing reading: pairi.ẏaoždaϑəṇ. təm.

Heuristic steps:
 1. Build linear sequence of lemma tokens across all <app> in doc.
 2. For each multi-token lemma app with L tokens:
      - Segment reading into subtokens using spaces and internal dot boundaries (token ends with '.').
      - Left trim: remove leading subtokens while first subtoken NOT similar to first lemma token.
                 Similarity: normalized (lower, NFC) prefix match >= 0.5 SequenceMatcher ratio
                 OR direct startswith (e.g., 'pairi.ẏaož' startswith 'pairi.').
      - Right trim: after achieving alignment for last lemma token position, remove remaining trailing subtokens.
 3. Preserve original @type attribute, only update rdg text surface.

We do not reclassify; optional logging prints affected rdgs.
"""
import argparse
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from lxml import etree

NS_TEI = 'http://www.tei-c.org/ns/1.0'

AVESTAN_CHARS = "a-zāēīōūąą̇ṇŋϑδγšṣśṣ̌žə̄ə̨ŋ́hᵛ"
DOT_SPLIT_REGEX = re.compile(rf"((?:[{AVESTAN_CHARS}]+\.)+)")

def normalize(t: str) -> str:
    return unicodedata.normalize('NFC', t.strip().lower())

def segment_reading(text: str):
    # First split by spaces, then further split tokens that contain internal dot boundaries
    parts = []
    for tok in text.strip().split():
        # Insert spaces before internal dot boundaries (letter.letter)
        # We'll split where a '.' is followed by a letter without intervening space
        subtoks = re.split(r'(?<=[\.])(?=[^\.])', tok)
        # Each subtok may still contain multiple boundaries; ensure they end with '.'
        expanded = []
        buf = ''
        for s in subtoks:
            buf += s
            if buf.endswith('.'):
                expanded.append(buf)
                buf = ''
        if buf:
            expanded.append(buf)
        for e in expanded:
            if e:
                parts.append(e)
    return parts

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()

def collapse(tokens):
    return ''.join(normalize(t).replace(' ', ''))

def trim_reading(lem_tokens, rdg_text):
    """Trim spillover by windowing over segmented tokens, allowing splits:
    Keep minimal contiguous window whose collapsed surface has >=0.6 similarity
    to collapsed lemma string and begins with token similar to first lemma token.
    """
    if not rdg_text:
        return rdg_text, False
    rdg_subtoks = segment_reading(rdg_text)
    if not rdg_subtoks:
        return rdg_text, False
    lem_collapse = collapse(lem_tokens)
    L = len(lem_tokens)
    # Require first lemma token similarity threshold
    best = None
    best_score = -1.0
    for start in range(len(rdg_subtoks)):
        if similarity(rdg_subtoks[start], lem_tokens[0]) < 0.5 and not normalize(rdg_subtoks[start]).startswith(normalize(lem_tokens[0])[:3]):
            continue
        acc = []
        for end in range(start, len(rdg_subtoks)):
            acc.append(rdg_subtoks[end])
            acc_collapse = collapse(acc)
            seq_sim = SequenceMatcher(None, acc_collapse, lem_collapse).ratio()
            # Penalize overly long windows: subtract small length penalty
            length_penalty = 0.02 * max(0, (len(acc) - L))
            score = seq_sim - length_penalty
            if seq_sim >= 0.6 and score > best_score:
                # Ensure we have covered at least last lemma token similarity somewhere
                last_tok_sim = max(similarity(t, lem_tokens[-1]) for t in acc)
                if last_tok_sim >= 0.5:
                    best = (start, end + 1)
                    best_score = score
            # Early break if sequence similarity begins to drop after surpassing lemma length +2
            if len(acc) > L + 2 and seq_sim < 0.5:
                break
    if best is None:
        # Fallback greedy coverage based on length accumulation
        # Find first token matching start lemma token
        start_idx = None
        for idx, tok in enumerate(rdg_subtoks):
            if similarity(tok, lem_tokens[0]) >= 0.5 or normalize(tok).startswith(normalize(lem_tokens[0])[:3]):
                start_idx = idx
                break
        if start_idx is None:
            return rdg_text, False
        acc = []
        for tok in rdg_subtoks[start_idx:]:
            acc.append(tok)
            if len(collapse(acc)) >= len(lem_collapse) - 2:  # allow slight deficit
                break
        new_text = ' '.join(acc)
        if new_text != rdg_text.strip():
            return new_text, True
        return rdg_text, False
    start, end = best
    new_tokens = rdg_subtoks[start:end]
    new_text = ' '.join(new_tokens)
    changed = new_text != rdg_text.strip()
    return new_text, changed


def process(input_path: Path, output_path: Path):
    tree = etree.parse(str(input_path))
    root = tree.getroot()
    apps = root.xpath('.//tei:app', namespaces={'tei': NS_TEI}) or root.xpath('.//app')
    changed_count = 0
    for app in apps:
        lem_el = app.find('.//tei:lem', namespaces={'tei': NS_TEI}) or app.find('lem')
        if lem_el is None:
            continue
        lem_surface = ' '.join(lem_el.itertext()).strip()
        lem_tokens = [t for t in lem_surface.split() if t]
        if len(lem_tokens) <= 1:
            continue
        rdgs = app.findall('.//tei:rdg', namespaces={'tei': NS_TEI}) or app.findall('rdg')
        for rdg in rdgs:
            old = ' '.join(rdg.itertext()).strip()
            new, changed = trim_reading(lem_tokens, old)
            if changed:
                rdg.text = new
                changed_count += 1
    tree.write(str(output_path), encoding='utf-8', xml_declaration=True, pretty_print=True)
    print(f"Spillover trimming complete. Changed readings: {changed_count}. Output: {output_path}")


def main():
    ap = argparse.ArgumentParser(description='Enhanced spillover trimming using dot segmentation.')
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    process(Path(args.input), Path(args.output))

if __name__ == '__main__':
    main()
