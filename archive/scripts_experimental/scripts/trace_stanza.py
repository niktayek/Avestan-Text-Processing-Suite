"""Trace a single stanza alignment end-to-end and print detailed debugging info.

Usage:
  PYTHONPATH="$(pwd)" poetry run python scripts/trace_stanza.py Y0.7

Defaults to Y0.7 if no stanza id provided.
"""
import sys
import os
import json
import difflib
import unicodedata
from lxml import etree
from src.interfaces.xml_translator import match_stanzas_by_id as ms

CANON = os.path.join(os.getcwd(), 'data', 'Yasna_Static.xml')
OURS = os.path.join(os.getcwd(), 'data', 'CAB', 'Yasna', '0005.xml')

stanza = sys.argv[1] if len(sys.argv) > 1 else 'Y0.7'

# helper (dup of small utilities used by the module)
def normalize_token(tok: str) -> str:
    t = unicodedata.normalize('NFC', tok)
    t = t.replace('⸳', '.')
    t = t.replace('⁛', '')
    t = t.strip()
    t = t.lower()
    return t

def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i] + [0] * lb
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            cur[j] = min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + cost)
        prev = cur
    return prev[lb]

# parse files using same forgiving parser
parser = etree.XMLParser(recover=True, remove_blank_text=True, huge_tree=True)
canon_tree = etree.parse(CANON, parser=parser)
our_tree = etree.parse(OURS, parser=parser)
canon_divs = ms.extract_divs_by_id(canon_tree)
our_divs = ms.extract_divs_by_id(our_tree)

canon_div = canon_divs.get(stanza)
our_div = our_divs.get(stanza)
if canon_div is None or our_div is None:
    print(f"Stanza {stanza} not found in one of the files")
    sys.exit(1)

canon_words = ms.extract_words_from_div(canon_div, insert_space_after_period=False)
our_words = ms.extract_words_from_div(our_div, insert_space_after_period=True)

print(f"Tracing stanza {stanza}")
print('canon_words:', canon_words)
print('our_words:', our_words)
print('\n--- Matching trace ---\n')

# We'll replay align_word_sequences logic but print details
n = len(canon_words)
m = len(our_words)
canon_matched = [None] * n
last_ci = -1
ratio_threshold = 0.60
window = 3
max_canon_span = 4

for oi, ow in enumerate(our_words):
    print(f"our[{oi}] = '{ow}'")
    best = None
    best_score = (-1.0, float('-inf'))
    best_ratio = -1.0
    search_start = last_ci + 1
    search_end = min(n, search_start + window * 3 + 1)
    print(f"  searching canon indices {search_start}..{search_end-1}")

    # single_match attempt
    for ci in range(search_start, search_end):
        if canon_matched[ci] is not None:
            continue
        try:
            ok = ms.single_match(canon_words[ci], ow)
        except Exception as e:
            ok = False
        print(f"    try single ci={ci} '{canon_words[ci]}' -> {ok}")
        if ok:
            best = (ci, 1, 1.0)
            best_ratio = 1.0
            best_score = (1.0, -0)
            print(f"      ACCEPT single_match ci={ci}")
            break

    # similarity fallback single tokens
    if best is None:
        for ci in range(search_start, search_end):
            if canon_matched[ci] is not None:
                continue
            a = normalize_token(canon_words[ci])
            b = normalize_token(ow)
            ratio = difflib.SequenceMatcher(None, a, b).ratio()
            a_alt = a.replace('ii', 'ai').replace('ə̄', 'ē')
            b_alt = b.replace('ii', 'ai').replace('ə̄', 'ē')
            ratio_alt = max(difflib.SequenceMatcher(None, a_alt, b).ratio(),
                            difflib.SequenceMatcher(None, a, b_alt).ratio(),
                            difflib.SequenceMatcher(None, a_alt, b_alt).ratio())
            ratio = max(ratio, ratio_alt)
            score = (ratio, -abs(ci - search_start))
            print(f"    single ci={ci} '{canon_words[ci]}' norm='{a}' ratio={ratio:.3f}")
            if score > best_score:
                best_score = score
                best_ratio = ratio
                best = (ci, 1, ratio)

    # try concatenating spans
    if best is None or best_ratio < ratio_threshold:
        for ci in range(search_start, min(n, search_start + window * 3)):
            if canon_matched[ci] is not None:
                continue
            for span in range(2, max_canon_span + 1):
                if ci + span > n:
                    break
                if any(canon_matched[ci + k] is not None for k in range(span)):
                    continue
                combined = [canon_words[ci + k] for k in range(span)]
                cand_variants = [".".join(combined), "".join(combined)]
                for cvar in cand_variants:
                    a = normalize_token(cvar)
                    b = normalize_token(ow)
                    ratio = difflib.SequenceMatcher(None, a, b).ratio()
                    a_alt = a.replace('ii', 'ai').replace('ə̄', 'ē')
                    b_alt = b.replace('ii', 'ai').replace('ə̄', 'ē')
                    ratio_alt = max(difflib.SequenceMatcher(None, a_alt, b).ratio(),
                                    difflib.SequenceMatcher(None, a, b_alt).ratio(),
                                    difflib.SequenceMatcher(None, a_alt, b_alt).ratio())
                    ratio = max(ratio, ratio_alt)
                    score = (ratio, -abs(ci - search_start))
                    print(f"    cand span ci={ci}..{ci+span-1} var='{cvar}' norm='{a}' ratio={ratio:.3f}")
                    if score > best_score:
                        best_score = score
                        best_ratio = ratio
                        best = (ci, span, ratio)
            if best_ratio >= 0.95:
                break

    if best is not None and best_ratio >= ratio_threshold:
        ci, span, _ = best
        print(f"  -> accepted candidate ci={ci} span={span} ratio={best_ratio:.3f}")
        for k in range(span):
            canon_matched[ci + k] = oi
        last_ci = ci + span - 1
    else:
        print(f"  -> no acceptable candidate (best_ratio={best_ratio:.3f})")

print('\n--- Post-processing (forward/reverse) ---\n')
# Forward pass (conservative) - reuse same conditions as module
for ci in range(0, n - 1):
    oi = canon_matched[ci]
    if oi is None:
        continue
    a = normalize_token(canon_words[ci]).replace('.', '')
    b = normalize_token(our_words[oi]).replace('.', '') if oi < len(our_words) else ''
    if a == b and abs(len(a) - len(b)) <= 2:
        continue
    if canon_matched[ci + 1] is not None:
        continue
    next_tok = normalize_token(canon_words[ci + 1])
    combined = (normalize_token(canon_words[ci]) + next_tok).replace('.', '')
    dist = levenshtein(combined, b)
    length_similar = abs(len(combined) - len(b)) <= 2
    contains = (combined in b or b in combined) and length_similar
    print(f"forward ci={ci} combined='{combined}' our_norm='{b}' dist={dist} contains={contains}")
    if dist <= 2 or contains:
        print(f"  -> merging next canon {ci+1} into our_index {oi}")
        canon_matched[ci + 1] = oi

# Reverse pass
for ci in range(0, n - 1):
    if canon_matched[ci] is not None:
        continue
    next_oi = canon_matched[ci + 1]
    if next_oi is None:
        continue
    cur = normalize_token(canon_words[ci]).replace('.', '')
    nxt = normalize_token(canon_words[ci + 1]).replace('.', '')
    combined = (cur + nxt)
    b_clean = normalize_token(our_words[next_oi]).replace('.', '') if next_oi < len(our_words) else ''
    dist = levenshtein(combined, b_clean)
    length_similar = abs(len(combined) - len(b_clean)) <= 2
    contains = (combined in b_clean or b_clean in combined) and length_similar
    print(f"reverse ci={ci} combined='{combined}' our_norm='{b_clean}' dist={dist} contains={contains}")
    if dist <= 2 or contains:
        print(f"  -> assigning canon {ci} to our_index {next_oi}")
        canon_matched[ci] = next_oi

print('\nFinal canon_matched mapping:')
for ci, val in enumerate(canon_matched):
    if val is not None:
        print(f"  canon[{ci}]='{canon_words[ci]}' -> our_index={val} our_word='{our_words[val]}'")
    else:
        print(f"  canon[{ci}]='{canon_words[ci]}' -> our_index=None")

# Build final matches (reuse module output formatting)
from pprint import pprint
matches = []
for ci, cw in enumerate(canon_words):
    oi = canon_matched[ci]
    if oi is None:
        matches.append({'canon_index': ci, 'our_index': None, 'canon_word': cw, 'our_word': '', 'relation': 'delete', 'matched': False})
    else:
        ow = our_words[oi]
        count = canon_matched.count(oi)
        if count > 1:
            relation = 'many-to-one'
        else:
            relation = 'equal' if normalize_token(cw) == normalize_token(ow) else 'substitution'
        matches.append({'canon_index': ci, 'our_index': oi, 'canon_word': cw, 'our_word': ow, 'relation': relation, 'matched': True})

# Emit merged summaries similar to module behavior
our_to_canons = {}
for ci, oi in enumerate(canon_matched):
    if oi is None:
        continue
    our_to_canons.setdefault(oi, []).append(ci)

for oi, cis in our_to_canons.items():
    if len(cis) <= 1:
        continue
    cis_sorted = sorted(cis)
    canon_tokens = [canon_words[i] for i in cis_sorted]
    combined_core = '.'.join([t[:-1] if t.endswith('.') else t for t in canon_tokens])
    combined_canon = combined_core + '.'
    combined_norm = normalize_token(combined_canon).replace('.', '')
    our_norm = normalize_token(our_words[oi]).replace('.', '') if oi < len(our_words) else ''
    ratio_combined = difflib.SequenceMatcher(None, combined_norm, our_norm).ratio()
    dist_combined = levenshtein(combined_norm, our_norm)
    length_similar = abs(len(combined_norm) - len(our_norm)) <= 3
    containment = combined_norm and (combined_norm in our_norm or our_norm in combined_norm) and length_similar
    if dist_combined <= 2 or ratio_combined >= 0.95 or containment:
        matches.append({'canon_indexes': cis_sorted, 'canon_word': combined_canon, 'our_index': oi, 'our_word': our_words[oi], 'relation': 'many-to-one (merged)', 'matched': True})

print('\n--- Final alignment entries ---')
pprint(matches, width=120)

# --- Our-centric aligned view: for each manuscript (our) token show which canonical tokens map to it ---
print('\n--- Our-centric alignment (manuscript order) ---')
our_to_canons = {}
for ci, oi in enumerate(canon_matched):
    if oi is None:
        continue
    our_to_canons.setdefault(oi, []).append(ci)

for oi in range(len(our_words)):
    cis = our_to_canons.get(oi, [])
    if not cis:
        print(f"our[{oi}] = '{our_words[oi]}'  <--  (no matched canon tokens)")
    else:
        canon_list = ", ".join([f"canon[{ci}]='{canon_words[ci]}'" for ci in cis])
        print(f"our[{oi}] = '{our_words[oi]}'  <--  {canon_list}")

# --- Canon-centric alignment (compact) ---
print('\n--- Canon-centric alignment (compact) ---')
for ci in range(len(canon_words)):
    oi = canon_matched[ci]
    if oi is None:
        print(f"canon[{ci}] = '{canon_words[ci]}'  <--  (unmatched)")
    else:
        print(f"canon[{ci}] = '{canon_words[ci]}'  <--  our[{oi}] = '{our_words[oi]}'")

# Optionally write the trace to a file alongside JSON for sharing
out_trace = os.path.join('res', f'trace_{stanza}.txt')
with open(out_trace, 'w', encoding='utf-8') as f:
    f.write(f"Stanza {stanza}\n\ncanon_words: {canon_words}\nour_words: {our_words}\n\nTrace output saved to this file.\n")

print(f"\nTrace saved to {out_trace}")
