"""Dry-run to detect which stanzas should be reprocessed with DP.

Scans all XMLs in data/CAB/Yasna/, runs the existing greedy aligner (using defaults tuned
for the "tight" run), and flags stanzas that meet any trigger. Writes a JSON report to
res/dp_dryrun_report.json and prints a concise summary.

Usage:
  PYTHONPATH="$(pwd)" poetry run python scripts/dp_dryrun.py

Defaults (configurable at top of file):
  ratio_threshold = 0.75
  window = 2
  max_canon_span = 3
  low_conf_ratio = 0.75
  low_conf_count_trigger = 6
  stanza_error_rate_trigger = 0.20
  short_token_len = 3
  short_token_count_trigger = 6
"""
import os
import json
import glob
import difflib
from collections import defaultdict, Counter

from src.interfaces.xml_translator import match_stanzas_by_id as ms

# Configurable defaults
RATIO = 0.75
WINDOW = 2
MAX_CANON_SPAN = 3
LOW_CONF_RATIO = 0.75
LOW_CONF_COUNT_TRIGGER = 6
STANZA_ERROR_RATE_TRIGGER = 0.20
SHORT_TOKEN_LEN = 3
SHORT_TOKEN_COUNT_TRIGGER = 6

XML_DIR = os.path.join('data', 'CAB', 'Yasna')
OUT_PATH = os.path.join('res', 'dp_dryrun_report.json')

os.makedirs('res', exist_ok=True)

report = {
    'config': {
        'ratio': RATIO,
        'window': WINDOW,
        'max_canon_span': MAX_CANON_SPAN,
        'low_conf_ratio': LOW_CONF_RATIO,
        'low_conf_count_trigger': LOW_CONF_COUNT_TRIGGER,
        'stanza_error_rate_trigger': STANZA_ERROR_RATE_TRIGGER,
        'short_token_len': SHORT_TOKEN_LEN,
        'short_token_count_trigger': SHORT_TOKEN_COUNT_TRIGGER,
    },
    'files': {},
    'total_stanzas': 0,
    'stanzas_to_dp': 0,
}

xmls = sorted(glob.glob(os.path.join(XML_DIR, '*.xml')))
if not xmls:
    print('No XML files found in', XML_DIR)
    raise SystemExit(1)

for xml_path in xmls:
    fname = os.path.basename(xml_path)
    print('Processing', fname)
    results = ms.match_stanzas(os.path.join(os.getcwd(), os.path.join('data', 'Yasna_Static.xml')), xml_path,
                               out_path=None, limit=None, window=WINDOW, ratio_threshold=RATIO, max_canon_span=MAX_CANON_SPAN)
    file_report = {'stanzas': {}, 'stanza_count': len(results), 'dp_candidates': []}
    report['total_stanzas'] += len(results)

    for stanza_res in results:
        xml_id = stanza_res['xml_id']
        alignment = stanza_res['alignment']
        canon_count = stanza_res['canon_word_count']
        our_count = stanza_res['our_word_count']
        # compute diagnostics
        subs_low = 0
        subs_total = 0
        unmatched = 0
        short_tokens = 0
        # helper to normalize
        normalize = ms.normalize_token
        for row in alignment:
            # skip merged/summary rows which include 'canon_indexes' etc.
            if 'canon_index' not in row:
                continue
            if row.get('canon_index') is None and row.get('our_index') is not None:
                # insertion (our word unmatched)
                unmatched += 1
                tok = row.get('our_word','')
                if tok and len(normalize(tok).replace('.', '')) <= SHORT_TOKEN_LEN:
                    short_tokens += 1
                continue
            if row.get('our_index') is None:
                # deletion on our side
                continue
            # matched pair
            if row.get('relation') == 'substitution':
                subs_total += 1
                a = normalize(row.get('canon_word',''))
                b = normalize(row.get('our_word',''))
                a_norm = a.replace('.', '')
                b_norm = b.replace('.', '')
                ratio = difflib.SequenceMatcher(None, a_norm, b_norm).ratio()
                if ratio < LOW_CONF_RATIO:
                    subs_low += 1
            # short token check on our side
            tok = row.get('our_word','')
            if tok and len(normalize(tok).replace('.', '')) <= SHORT_TOKEN_LEN:
                short_tokens += 1

        # error rate
        error_rate = (unmatched + subs_total) / max(1, (canon_count))
        triggers = []
        if subs_low >= LOW_CONF_COUNT_TRIGGER:
            triggers.append({'type': 'low_conf_subs', 'count': subs_low})
        if error_rate >= STANZA_ERROR_RATE_TRIGGER:
            triggers.append({'type': 'high_error_rate', 'error_rate': error_rate})
        if short_tokens >= SHORT_TOKEN_COUNT_TRIGGER:
            triggers.append({'type': 'short_token_cluster', 'short_tokens': short_tokens})

        file_report['stanzas'][xml_id] = {
            'canon_count': canon_count,
            'our_count': our_count,
            'subs_total': subs_total,
            'subs_low': subs_low,
            'unmatched': unmatched,
            'short_tokens': short_tokens,
            'error_rate': error_rate,
            'triggers': triggers,
        }
        if triggers:
            file_report['dp_candidates'].append(xml_id)
            report['stanzas_to_dp'] += 1

    report['files'][fname] = file_report

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

# Summarize
print('\nDry-run complete')
print('Total stanzas processed:', report['total_stanzas'])
print('Stanzas flagged for DP:', report['stanzas_to_dp'])
print('Report written to', OUT_PATH)
