import json
import pprint
from pathlib import Path

p = Path('res/stanza_word_matches_Y0.7-Y0.10.json')
if not p.exists():
    raise SystemExit(f'File not found: {p}')

data = json.loads(p.read_text(encoding='utf-8'))

total = 0
per = {}
examples = []

for stanza in data:
    xml = stanza.get('xml_id', '')
    for item in stanza.get('alignment', []):
        rel = item.get('relation', '')
        # consider merged markers or explicit merged keys
        if '(merged)' in rel or 'canon_indexes' in item or 'our_indexes' in item:
            total += 1
            per[xml] = per.get(xml, 0) + 1
            if len(examples) < 12:
                examples.append({'xml': xml, 'item': item})

print('total_merged:', total)
print('per_stanza:')
pp = pprint.PrettyPrinter(indent=2, width=120)
pp.pprint(per)
print('\nexamples (up to 12):')
pp.pprint(examples)
