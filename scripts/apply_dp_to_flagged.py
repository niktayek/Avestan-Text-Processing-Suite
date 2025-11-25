#!/usr/bin/env python3
"""Apply stanza-level DP to stanzas flagged by the dry-run detector.

Reads `res/dp_dryrun_report.json`, runs DP for each flagged stanza, compares the DP
grouping to the greedy grouping, writes per-stanza JSONs under `res/dp_applied/<xml>/`
and a summary report `res/dp_report.json`.

Usage:
  PYTHONPATH="$(pwd)" python3 scripts/apply_dp_to_flagged.py --gap -0.25

"""
import os
import sys
import json
import time
import argparse
import difflib
from lxml import etree

from src.interfaces.xml_translator import match_stanzas_by_id as ms


def dp_align(canon_words, our_words, gap_penalty=-0.25):
    n = len(canon_words)
    m = len(our_words)
    S = [[0.0] * (m + 1) for _ in range(n + 1)]
    P = [[None] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        S[i][0] = S[i - 1][0] + gap_penalty
        P[i][0] = ('up', i - 1, 0)
    for j in range(1, m + 1):
        S[0][j] = S[0][j - 1] + gap_penalty
        P[0][j] = ('left', 0, j - 1)

    def normalize_tok(t):
        return ms.normalize_token(t).replace('.', '')

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            match_score = 0.0
            a = normalize_tok(canon_words[i - 1])
            b = normalize_tok(our_words[j - 1])
            if a and b:
                match_score = difflib.SequenceMatcher(None, a, b).ratio()
            diag = S[i - 1][j - 1] + match_score
            up = S[i - 1][j] + gap_penalty
            left = S[i][j - 1] + gap_penalty
            best = max((diag, 'diag', i - 1, j - 1), (up, 'up', i - 1, j), (left, 'left', i, j - 1), key=lambda x: x[0])
            S[i][j] = best[0]
            P[i][j] = (best[1], best[2], best[3])

    # backtrack
    i, j = n, m
    pairs = []
    while i > 0 or j > 0:
        p = P[i][j]
        if p is None:
            break
        dirn, pi, pj = p
        if dirn == 'diag':
            pairs.append(([i - 1], [j - 1]))
            i, j = pi, pj
        elif dirn == 'up':
            pairs.append(([i - 1], []))
            i, j = pi, pj
        else:
            pairs.append(([], [j - 1]))
            i, j = pi, pj
    pairs.reverse()

    # merge consecutive diag runs into groups
    merged = []
    cur_cis = []
    cur_ois = []
    for cis, ois in pairs:
        if cis and ois:
            if not cur_cis and not cur_ois:
                cur_cis = cis.copy()
                cur_ois = ois.copy()
            elif cur_cis and cur_ois and (cis[0] == cur_cis[-1] + 1) and (ois[0] == cur_ois[-1] + 1):
                cur_cis.extend(cis)
                cur_ois.extend(ois)
            else:
                if cur_cis or cur_ois:
                    merged.append((cur_cis.copy(), cur_ois.copy()))
                cur_cis = cis.copy()
                cur_ois = ois.copy()
        else:
            if cur_cis or cur_ois:
                merged.append((cur_cis.copy(), cur_ois.copy()))
            cur_cis = cis.copy()
            cur_ois = ois.copy()
            merged.append((cur_cis.copy(), cur_ois.copy()))
            cur_cis = []
            cur_ois = []
    if cur_cis or cur_ois:
        merged.append((cur_cis.copy(), cur_ois.copy()))

    return merged, S[n][m]


def build_greedy_groups(matches):
    # matches is list of dicts returned by ms.align_word_sequences
    groups = []
    # first use explicit merged entries
    for item in matches:
        if 'canon_indexes' in item:
            cis = item.get('canon_indexes')
            oi = item.get('our_index')
            if cis:
                groups.append((cis, [oi] if oi is not None else []))
    # then build from per-token entries (canon_index present)
    per = [m for m in matches if m.get('canon_index') is not None and m.get('our_index') is not None]
    per_sorted = sorted(per, key=lambda x: x['canon_index'])
    cur_cis = []
    cur_ois = []
    last_ci = None
    last_oi = None
    for it in per_sorted:
        ci = it['canon_index']
        oi = it['our_index']
        if last_ci is None:
            cur_cis = [ci]
            cur_ois = [oi]
        elif ci == last_ci + 1 and oi == last_oi:
            cur_cis.append(ci)
        else:
            groups.append((cur_cis.copy(), cur_ois.copy()))
            cur_cis = [ci]
            cur_ois = [oi]
        last_ci = ci
        last_oi = oi
    if cur_cis:
        groups.append((cur_cis.copy(), cur_ois.copy()))
    # normalize groups: make sure our_indexes is list and unique
    norm = []
    for cis, ois in groups:
        ois = [o for o in ois if o is not None]
        ois = sorted(set(ois))
        norm.append((sorted(cis), ois))
    return norm


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dryrun', default=os.path.join('res', 'dp_dryrun_report.json'))
    parser.add_argument('--gap', type=float, default=-0.25)
    parser.add_argument('--limit', type=int, default=None, help='Limit number of stanzas processed')
    args = parser.parse_args()

    if not os.path.exists(args.dryrun):
        print('Dry-run report not found at', args.dryrun)
        sys.exit(1)

    with open(args.dryrun, 'r', encoding='utf-8') as f:
        report = json.load(f)

    results = {'config': report.get('config', {}), 'files': {}, 'total_processed': 0, 'total_changed': 0}
    os.makedirs(os.path.join('res', 'dp_applied'), exist_ok=True)

    start_all = time.time()
    for fname, freport in report.get('files', {}).items():
        xml_path = os.path.join('data', 'CAB', 'Yasna', fname)
        if not os.path.exists(xml_path):
            print('Skipping missing', xml_path)
            continue
        dp_candidates = freport.get('dp_candidates', [])
        if not dp_candidates:
            continue
        file_out_dir = os.path.join('res', 'dp_applied', fname.replace('.xml', ''))
        os.makedirs(file_out_dir, exist_ok=True)
        # parse trees once
        parser = etree.XMLParser(recover=True, remove_blank_text=True, huge_tree=True)
        canon_tree = etree.parse(os.path.join(os.getcwd(), 'data', 'Yasna_Static.xml'), parser=parser)
        our_tree = etree.parse(xml_path, parser=parser)
        canon_divs = ms.extract_divs_by_id(canon_tree)
        our_divs = ms.extract_divs_by_id(our_tree)

        file_summary = {'processed': 0, 'changed': 0, 'stanzas': {}}
        for idx, stanza in enumerate(dp_candidates):
            if args.limit and file_summary['processed'] >= args.limit:
                break
            canon_div = canon_divs.get(stanza)
            our_div = our_divs.get(stanza)
            if canon_div is None or our_div is None:
                continue
            canon_words = ms.extract_words_from_div(canon_div, insert_space_after_period=False)
            our_words = ms.extract_words_from_div(our_div, insert_space_after_period=True)
            # greedy matches
            greedy_matches = ms.align_word_sequences(canon_words, our_words, window=ms.align_word_sequences.__defaults__[0] if hasattr(ms.align_word_sequences, '__defaults__') else 3, ratio_threshold=report.get('config', {}).get('ratio', 0.75), max_canon_span=report.get('config', {}).get('max_canon_span', 3))
            greedy_groups = build_greedy_groups(greedy_matches)

            dp_groups, dp_score = dp_align(canon_words, our_words, gap_penalty=args.gap)

            # normalize dp_groups: ensure lists and sorted
            dp_norm = [(sorted(cis), sorted(ois)) for cis, ois in dp_groups]
            # compare
            changed = dp_norm != greedy_groups

            stanza_out = {
                'stanza': stanza,
                'canon_words': canon_words,
                'our_words': our_words,
                'greedy_groups': greedy_groups,
                'dp_groups': dp_norm,
                'dp_score': dp_score,
                'changed': changed,
            }

            out_path = os.path.join(file_out_dir, f'{stanza}.json')
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(stanza_out, f, ensure_ascii=False, indent=2)

            file_summary['stanzas'][stanza] = {'changed': changed, 'dp_score': dp_score, 'canon_count': len(canon_words), 'our_count': len(our_words)}
            file_summary['processed'] += 1
            if changed:
                file_summary['changed'] += 1
                results['total_changed'] += 1
            results['total_processed'] += 1

        results['files'][fname] = file_summary

    results['elapsed_sec'] = time.time() - start_all
    # write summary
    with open(os.path.join('res', 'dp_report.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print('DP application complete')
    print('Total stanzas processed:', results['total_processed'])
    print('Total changed by DP:', results['total_changed'])
    print('Report written to res/dp_report.json')


if __name__ == '__main__':
    main()
