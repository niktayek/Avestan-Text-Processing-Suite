#!/usr/bin/env python3
"""Produce a single CSV/JSON with per-manuscript-token rows that contain both
the greedy alignment and the DP alignment for easy comparison.

Outputs:
  res/stanza_word_matches_0005_greedy_vs_dp.csv
  res/stanza_word_matches_0005_greedy_vs_dp.json

Usage:
  PYTHONPATH="$(pwd)" poetry run python3 scripts/compare_greedy_dp_word_matches.py
"""
import os
import json
import csv
from lxml import etree
from src.interfaces.xml_translator import match_stanzas_by_id as ms

CANON = os.path.join(os.getcwd(), 'data', 'Yasna_Static.xml')
OURS = os.path.join(os.getcwd(), 'data', 'CAB', 'Yasna', '0005.xml')
DP_DIR = os.path.join('res', 'dp_applied', '0005')
CSV_OUT = os.path.join('res', 'stanza_word_matches_0005_greedy_vs_dp.csv')
JSON_OUT = os.path.join('res', 'stanza_word_matches_0005_greedy_vs_dp.json')

os.makedirs('res', exist_ok=True)

def build_mapping_from_greedy(alignment, canon_words, our_words):
    # build our_index -> list of canon indexes
    our_to_canons = {i: [] for i in range(len(our_words))}
    for ent in alignment:
        # merged entries
        if 'canon_indexes' in ent and ent.get('our_index') is not None:
            for ci in ent['canon_indexes']:
                our_to_canons.setdefault(ent['our_index'], []).append(ci)
        elif ent.get('canon_index') is not None and ent.get('our_index') is not None:
            our_to_canons.setdefault(ent['our_index'], []).append(ent['canon_index'])
    return our_to_canons

def build_mapping_from_dp(dp_groups, canon_words, our_words, pair_threshold=0.90):
    """Build our_index -> canon_indexes mapping from dp_groups.

    For many-to-many groups try to extract high-confidence one-to-one pairings inside the
    group (greedy by highest difflib ratio) using pair_threshold. Remaining tokens are
    assigned as many-to-one (if group has single our index) or left grouped.
    """
    our_to_canons = {i: [] for i in range(len(our_words))}
    import difflib

    for cis, ois in dp_groups:
        cis = list(cis)
        ois = list(ois)
        if not cis and not ois:
            continue
        # simple cases
        if cis and ois and len(cis) == 1 and len(ois) >= 1:
            # single canonical maps to one or more our tokens -> assign that canon to all our tokens in group
            for oi in ois:
                our_to_canons.setdefault(oi, []).append(cis[0])
            continue
        if cis and ois and len(ois) == 1:
            # many canonical -> single our: assign all cis to that oi
            our_to_canons.setdefault(ois[0], []).extend(cis)
            continue

        # many-to-many: try to pair using similarity
        if cis and ois:
            # build candidate list of (ratio, ci, oi)
            cand = []
            for ci in cis:
                a = ms.normalize_token(canon_words[ci]).replace('.', '')
                for oi in ois:
                    b = ms.normalize_token(our_words[oi]).replace('.', '')
                    if not a or not b:
                        continue
                    r = difflib.SequenceMatcher(None, a, b).ratio()
                    cand.append((r, ci, oi))
            cand.sort(reverse=True, key=lambda x: x[0])
            used_ci = set()
            used_oi = set()
            for r, ci, oi in cand:
                if r < pair_threshold:
                    break
                if ci in used_ci or oi in used_oi:
                    continue
                our_to_canons.setdefault(oi, []).append(ci)
                used_ci.add(ci)
                used_oi.add(oi)
            # if there are remaining cis and only one oi in group, assign remaining cis to that oi
            remaining_cis = [ci for ci in cis if ci not in used_ci]
            remaining_ois = [oi for oi in ois if oi not in used_oi]
            if remaining_cis and len(remaining_ois) == 1:
                our_to_canons.setdefault(remaining_ois[0], []).extend(remaining_cis)
            else:
                # for remaining our indexes that have no assigned cis, leave them with empty list
                for oi in remaining_ois:
                    our_to_canons.setdefault(oi, [])
            continue

        # fallback: if group had only cis or only ois
        for oi in ois:
            our_to_canons.setdefault(oi, []).extend(cis)
    return our_to_canons

def canon_tokens_from_indexes(canon_words, cis):
    return [canon_words[i] for i in cis]

def relation_label(cis, our_word, canon_words):
    if not cis:
        return 'unmatched'
    if len(cis) > 1:
        return 'many-to-one'
    ci = cis[0]
    return 'equal' if ms.normalize_token(canon_words[ci]) == ms.normalize_token(our_word) else 'substitution'

def main():
    # greedy alignments (use same params as dry-run: ratio 0.75, window 2, max_canon_span 3)
    greedy_results = ms.match_stanzas(CANON, OURS, out_path=None, limit=None, window=2, ratio_threshold=0.75, max_canon_span=3)

    # parse trees to extract token lists per stanza
    parser = etree.XMLParser(recover=True, remove_blank_text=True, huge_tree=True)
    canon_tree = etree.parse(CANON, parser=parser)
    our_tree = etree.parse(OURS, parser=parser)
    canon_divs = ms.extract_divs_by_id(canon_tree)
    our_divs = ms.extract_divs_by_id(our_tree)

    rows = []
    json_out = []

    for stanza_res in greedy_results:
        xml_id = stanza_res['xml_id']
        alignment = stanza_res['alignment']
        canon_div = canon_divs.get(xml_id)
        our_div = our_divs.get(xml_id)
        canon_words = ms.extract_words_from_div(canon_div, insert_space_after_period=False) if canon_div is not None else []
        our_words = ms.extract_words_from_div(our_div, insert_space_after_period=True) if our_div is not None else []

        greedy_map = build_mapping_from_greedy(alignment, canon_words, our_words)

        # load dp groups if available
        dp_file = os.path.join(DP_DIR, f'{xml_id}.json')
        if os.path.exists(dp_file):
            dp_data = json.load(open(dp_file, 'r', encoding='utf-8'))
            dp_groups = dp_data.get('dp_groups', [])
            dp_map = build_mapping_from_dp(dp_groups, canon_words, our_words)
        else:
            dp_map = {i: [] for i in range(len(our_words))}

        # Build quick lookup: our_index -> the dp group (cis, ois) that contains it (for context)
        dp_group_lookup = {}
        for cis, ois in (dp_data.get('dp_groups', []) if os.path.exists(dp_file) else []):
            cis = list(cis)
            ois = list(ois)
            for oi in ois:
                dp_group_lookup[oi] = cis
        # (we'll discover greedy group context by scanning alignment per token below)

        for oi, ow in enumerate(our_words):
            greedy_cis = sorted(set(greedy_map.get(oi, [])))
            dp_cis = sorted(set(dp_map.get(oi, [])))

            greedy_canon_words = ' '.join(canon_tokens_from_indexes(canon_words, greedy_cis)) if greedy_cis else ''
            dp_canon_words = ' '.join(canon_tokens_from_indexes(canon_words, dp_cis)) if dp_cis else ''

            greedy_rel = relation_label(greedy_cis, ow, canon_words) if canon_words else 'unmatched'
            dp_rel = relation_label(dp_cis, ow, canon_words) if canon_words else 'unmatched'

            # greedy group context: find the merged canonical group that contains this our token
            greedy_group_cis = []
            # scan alignment for merged entries with 'canon_indexes' or token entries matching this our index
            for ent in alignment:
                if 'canon_indexes' in ent and ent.get('our_index') is not None:
                    if ent.get('our_index') == oi:
                        greedy_group_cis = ent.get('canon_indexes') or []
                        break
                if ent.get('canon_index') is not None and ent.get('our_index') == oi:
                    greedy_group_cis = [ent.get('canon_index')]
                    break

            greedy_group_canon_words = ' '.join(canon_tokens_from_indexes(canon_words, greedy_group_cis)) if greedy_group_cis else ''
            dp_group_cis = dp_group_lookup.get(oi, [])
            dp_group_canon_words = ' '.join(canon_tokens_from_indexes(canon_words, dp_group_cis)) if dp_group_cis else ''

            row = {
                'xml_id': xml_id,
                'our_index': oi,
                'our_word': ow,
                'greedy_canon_indexes': ';'.join(str(i) for i in greedy_cis),
                'greedy_canon_words': greedy_canon_words,
                'greedy_relation': greedy_rel,
                'dp_canon_indexes': ';'.join(str(i) for i in dp_cis),
                'dp_canon_words': dp_canon_words,
                'dp_relation': dp_rel,
                'greedy_group_canon_words': greedy_group_canon_words,
                'dp_group_canon_words': dp_group_canon_words,
            }
            rows.append([row['xml_id'], row['our_index'], row['our_word'], row['greedy_canon_indexes'], row['greedy_canon_words'], row['greedy_relation'], row['dp_canon_indexes'], row['dp_canon_words'], row['dp_relation'], row['greedy_group_canon_words'], row['dp_group_canon_words']])
            json_out.append(row)

    # write CSV
    with open(CSV_OUT, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['xml_id','our_index','our_word','greedy_canon_indexes','greedy_canon_words','greedy_relation','dp_canon_indexes','dp_canon_words','dp_relation','greedy_group_canon_words','dp_group_canon_words'])
        for r in rows:
            writer.writerow(r)

    with open(JSON_OUT, 'w', encoding='utf-8') as f:
        json.dump(json_out, f, ensure_ascii=False, indent=2)

    print('Wrote:', CSV_OUT, 'and', JSON_OUT)


if __name__ == '__main__':
    main()
