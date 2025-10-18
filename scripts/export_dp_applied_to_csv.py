import os
import csv
import json
from src.interfaces.xml_translator import match_stanzas_by_id as ms

DP_DIR = os.path.join('res', 'dp_applied', '0005')
CSV_OUT = os.path.join('res', 'stanza_word_matches_0005_by_dp.csv')

if not os.path.isdir(DP_DIR):
    print('DP-applied folder not found:', DP_DIR)
    raise SystemExit(1)

rows = []

files = sorted([f for f in os.listdir(DP_DIR) if f.endswith('.json')])
for fname in files:
    path = os.path.join(DP_DIR, fname)
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    stanza = data.get('stanza')
    canon_words = data.get('canon_words', [])
    our_words = data.get('our_words', [])
    groups = data.get('dp_groups') or []

    # Keep track of which our indexes are covered by groups
    our_covered = set()

    def join_canon(cis):
        # join canon tokens into a readable combined string, similar to previous code
        def strip_trailing_dot(s):
            return s[:-1] if s.endswith('.') else s
        canon_tokens = [canon_words[i] for i in cis]
        combined_core = '.'.join([strip_trailing_dot(t) for t in canon_tokens])
        return combined_core + '.'

    for cis, ois in groups:
        if not cis and not ois:
            continue
        cis = sorted(cis) if cis else []
        ois = sorted(ois) if ois else []

        # Case 1: pairwise mapping when lengths equal -> emit per-pair rows
        if cis and ois and len(cis) == len(ois):
            for k in range(len(cis)):
                ci = cis[k]
                oi = ois[k]
                if oi < 0 or oi >= len(our_words) or ci < 0 or ci >= len(canon_words):
                    continue
                rows.append([stanza, oi, our_words[oi], str(ci), canon_words[ci], 'equal' if ms.normalize_token(canon_words[ci]) == ms.normalize_token(our_words[oi]) else 'substitution', True])
                our_covered.add(oi)
            continue

        # Case 2: many-to-one (multiple canon -> single our)
        if cis and ois and len(cis) > 1 and len(ois) == 1:
            oi = ois[0]
            if 0 <= oi < len(our_words):
                canon_indexes_str = ";".join(str(ci) for ci in cis)
                canon_words_str = join_canon(cis)
                rows.append([stanza, oi, our_words[oi], canon_indexes_str, canon_words_str, 'many-to-one', True])
                our_covered.add(oi)
            continue

        # Case 3: one-to-many (single canon -> multiple our) -> emit a merged our_words row
        if cis and ois and len(cis) == 1 and len(ois) > 1:
            ci = cis[0]
            our_indexes_str = ";".join(str(oi) for oi in ois)
            our_words_str = " ".join(our_words[oi] for oi in ois if 0 <= oi < len(our_words))
            rows.append([stanza, our_indexes_str, our_words_str, str(ci), canon_words[ci], 'one-to-many', True])
            for oi in ois:
                our_covered.add(oi)
            continue

        # Case 4: mixed many-to-many or other shapes -> emit one grouped row to avoid repetition
        # Represent our_indexes and canon_indexes as semicolon lists and put combined tokens
        our_indexes_str = ";".join(str(oi) for oi in ois) if ois else ''
        canon_indexes_str = ";".join(str(ci) for ci in cis) if cis else ''
        our_words_str = " ".join(our_words[oi] for oi in ois if 0 <= oi < len(our_words))
        canon_words_str = join_canon(cis) if cis else ''
        rows.append([stanza, our_indexes_str, our_words_str, canon_indexes_str, canon_words_str, 'grouped', True])
        for oi in ois:
            our_covered.add(oi)

    # Finally, emit unmatched our tokens not covered by any group
    for oi, ow in enumerate(our_words):
        if oi in our_covered:
            continue
        rows.append([stanza, oi, ow, '', '', 'unmatched', False])

os.makedirs(os.path.dirname(CSV_OUT), exist_ok=True)
with open(CSV_OUT, 'w', encoding='utf-8', newline='') as csvf:
    writer = csv.writer(csvf)
    writer.writerow(['xml_id','our_index','our_word','canon_indexes','canon_words','relation','matched'])
    for r in rows:
        writer.writerow(r)

print('Wrote:', CSV_OUT)
