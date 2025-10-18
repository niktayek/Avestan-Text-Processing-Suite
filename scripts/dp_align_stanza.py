"""Run a stanza-level DP alignment (Needleman-Wunsch style) on a single stanza.

Usage:
  PYTHONPATH="$(pwd)" poetry run python scripts/dp_align_stanza.py Y1.1

This produces a compact canon-centric and our-centric alignment and writes a small JSON in res/ for inspection.
"""
import os
import sys
import json
import difflib
import unicodedata
from lxml import etree
from src.interfaces.xml_translator import match_stanzas_by_id as ms

CANON = os.path.join(os.getcwd(), 'data', 'Yasna_Static.xml')
OURS = os.path.join(os.getcwd(), 'data', 'CAB', 'Yasna', '0005.xml')

stanza = sys.argv[1] if len(sys.argv) > 1 else 'Y1.1'

# helper normalization (same as module)
def normalize_token(tok: str) -> str:
    t = unicodedata.normalize('NFC', tok)
    t = t.replace('⸳', '.')
    t = t.replace('⁛', '')
    t = t.strip()
    t = t.lower()
    return t


def token_similarity(a_tok: str, b_tok: str) -> float:
    a = normalize_token(a_tok).replace('.', '')
    b = normalize_token(b_tok).replace('.', '')
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def dp_align(canon_words, our_words, gap_penalty=-0.25):
    # DP over canon (i) and our (j); maximize total score where match score = similarity
    n = len(canon_words)
    m = len(our_words)
    # score and backpointer matrices
    S = [[0.0] * (m+1) for _ in range(n+1)]
    P = [[None] * (m+1) for _ in range(n+1)]

    # initialize with gap penalties
    for i in range(1, n+1):
        S[i][0] = S[i-1][0] + gap_penalty
        P[i][0] = ('up', i-1, 0)
    for j in range(1, m+1):
        S[0][j] = S[0][j-1] + gap_penalty
        P[0][j] = ('left', 0, j-1)

    for i in range(1, n+1):
        for j in range(1, m+1):
            # match/mismatch (align canon[i-1] with our[j-1])
            match_score = token_similarity(canon_words[i-1], our_words[j-1])
            diag = S[i-1][j-1] + match_score
            up = S[i-1][j] + gap_penalty  # canon aligned to gap
            left = S[i][j-1] + gap_penalty  # our aligned to gap
            best = max((diag, 'diag', i-1, j-1), (up, 'up', i-1, j), (left, 'left', i, j-1), key=lambda x: x[0])
            S[i][j] = best[0]
            P[i][j] = (best[1], best[2], best[3])

    # backtrack
    i, j = n, m
    canon_to_our = []  # list of (canon_indices_list, our_indices_list)
    while i > 0 or j > 0:
        p = P[i][j]
        if p is None:
            break
        dirn, pi, pj = p
        if dirn == 'diag':
            # pair canon[i-1] with our[j-1]
            canon_to_our.append(([i-1], [j-1]))
            i, j = pi, pj
        elif dirn == 'up':
            # canon[i-1] aligned to gap
            canon_to_our.append(([i-1], []))
            i, j = pi, pj
        else:  # left
            # our[j-1] aligned to gap (we'll add as empty canon)
            canon_to_our.append(([], [j-1]))
            i, j = pi, pj
    canon_to_our.reverse()

    # merge adjacent diag entries when they align consecutively to produce many-to-one or one-to-many groups
    merged = []
    cur_cis = []
    cur_ois = []
    for cis, ois in canon_to_our:
        if cis and ois:
            # both non-empty => a diag pairing
            if cur_cis == [] and cur_ois == []:
                cur_cis = cis.copy()
                cur_ois = ois.copy()
            elif cur_cis and cur_ois and (cis[0] == cur_cis[-1] + 1) and (ois[0] == cur_ois[-1] + 1):
                # consecutive; extend
                cur_cis.extend(cis)
                cur_ois.extend(ois)
            else:
                merged.append((cur_cis.copy(), cur_ois.copy())) if cur_cis or cur_ois else None
                cur_cis = cis.copy()
                cur_ois = ois.copy()
        else:
            # either insertion or deletion: flush current run then add the gap entry
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


if __name__ == '__main__':
    # parse files using forgiving parser as in the project
    parser = etree.XMLParser(recover=True, remove_blank_text=True, huge_tree=True)
    canon_tree = etree.parse(CANON, parser=parser)
    our_tree = etree.parse(OURS, parser=parser)

    canon_divs = ms.extract_divs_by_id(canon_tree)
    our_divs = ms.extract_divs_by_id(our_tree)

    canon_div = canon_divs.get(stanza)
    our_div = our_divs.get(stanza)
    if canon_div is None or our_div is None:
        print(f'Stanza {stanza} not found')
        sys.exit(1)

    canon_words = ms.extract_words_from_div(canon_div, insert_space_after_period=False)
    our_words = ms.extract_words_from_div(our_div, insert_space_after_period=True)

    merged, score = dp_align(canon_words, our_words, gap_penalty=-0.25)

    out = {
        'stanza': stanza,
        'canon_words': canon_words,
        'our_words': our_words,
        'alignment_groups': [],
        'score': score
    }

    # produce readable groups
    for cis, ois in merged:
        group = {
            'canon_indexes': cis if cis else None,
            'canon_words': [canon_words[i] for i in cis] if cis else None,
            'our_indexes': ois if ois else None,
            'our_words': [our_words[j] for j in ois] if ois else None
        }
        out['alignment_groups'].append(group)

    os.makedirs('res', exist_ok=True)
    out_path = os.path.join('res', f'dp_alignment_{stanza}.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f'Wrote DP alignment for {stanza} to {out_path}; total score={score:.3f}')
    # print a concise our-centric view
    print('\nOur-centric view:')
    for idx, w in enumerate(our_words):
        matched = [g for g in out['alignment_groups'] if g['our_indexes'] and idx in g['our_indexes']]
        if matched:
            print(f"our[{idx}]='{w}' -> canon idxs {[g['canon_indexes'] for g in matched]} words {[g['canon_words'] for g in matched]}")
        else:
            print(f"our[{idx}]='{w}' -> (no canon)")

    print('\nCanon-centric view:')
    for idx, w in enumerate(canon_words):
        matched = [g for g in out['alignment_groups'] if g['canon_indexes'] and idx in g['canon_indexes']]
        if matched:
            print(f"canon[{idx}]='{w}' -> our idxs {[g['our_indexes'] for g in matched]} words {[g['our_words'] for g in matched]}")
        else:
            print(f"canon[{idx}]='{w}' -> (no our)")
