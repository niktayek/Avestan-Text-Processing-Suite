import csv
import difflib
from collections import Counter

IN = 'res/stanza_word_matches_0005_by_our.csv'
THRESH = 0.75
probs = []
counts = Counter()
with open(IN, encoding='utf-8') as fh:
    r = csv.DictReader(fh)
    for row in r:
        rel = row.get('relation','')
        counts[rel] += 1
        if rel == 'substitution' and row.get('canon_words') and row.get('our_word'):
            a = row['canon_words'].strip()
            b = row['our_word'].strip()
            ratio = difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()
            if ratio < THRESH:
                probs.append((row['xml_id'], row['our_index'], b, a, ratio))

print('Relation counts:', counts)
print(f'Found {len(probs)} substitution rows with ratio < {THRESH}:')
for p in probs[:200]:
    print(p[0], p[1], p[2], '<->', p[3], f' ratio={p[4]:.3f}')

# also summary per stanza
from collections import defaultdict
per_stanza = defaultdict(int)
for st, oi, b, a, r in probs:
    per_stanza[st] += 1
print('\nPer-stanza low-confidence substitution counts:')
for st, c in sorted(per_stanza.items()):
    print(st, c)
