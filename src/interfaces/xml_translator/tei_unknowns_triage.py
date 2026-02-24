import argparse
import pandas as pd
import re
import unicodedata
from pathlib import Path

UNKNOWN_IN = Path('res/Yasna/meta/unknown_review.csv')
CURATOR_OUT = Path('res/Yasna/meta/unknown_review_for_curator.csv')
SUGGEST_OUT = Path('res/Yasna/meta/unknown_quick_suggestions.csv')

VOWEL_MAP = str.maketrans({'ā':'a','ī':'i','ū':'u','ē':'e','ō':'o'})
SIBILANTS = {'s','š','ṣ','ś'}
DIPH_PAIRS = {('ao','ō'), ('ae','ē'), ('aē','ē'), ('ao','ā'), ('ao','o'), ('ae','e')}


def nfc(s: str) -> str:
    return unicodedata.normalize('NFC', str(s))


def strip_periods_spaces(s: str) -> str:
    s = nfc(s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s.rstrip('.')


def parse_feature_tokens(feature: str):
    if not isinstance(feature, str):
        return '', ''
    f = strip_periods_spaces(feature.lower())
    if '→' in f:
        a, b = f.split('→', 1)
    elif ' for ' in f:
        b, a = f.split(' for ', 1)
    else:
        return '', ''
    return a.strip(), b.strip()


def is_vowel_quantity(x: str, y: str) -> bool:
    if not x or not y:
        return False
    xb = x.translate(VOWEL_MAP)
    yb = y.translate(VOWEL_MAP)
    return xb == yb and (x != xb or y != yb)


def is_sibilant_swap(x: str, y: str) -> bool:
    if not x or not y:
        return False
    return (x in SIBILANTS or y in SIBILANTS) and x != y and x.translate(VOWEL_MAP) == y.translate(VOWEL_MAP)


def is_diphthong_monoph(x: str, y: str) -> bool:
    pair = (x, y)
    return pair in DIPH_PAIRS or pair[::-1] in DIPH_PAIRS


def orthography_guess_from_feature(feature: str) -> bool:
    x, y = parse_feature_tokens(feature)
    if not x and not y:
        return False
    if is_vowel_quantity(x, y):
        return True
    if is_sibilant_swap(x, y):
        return True
    if is_diphthong_monoph(x, y):
        return True
    return False


def make_band(vlik):
    try:
        v = float(vlik)
    except Exception:
        return ''
    if 0.73 <= v < 0.75:
        return 'hi'
    if 0.70 <= v < 0.73:
        return 'mid'
    return ''


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--unknown-in', default=str(UNKNOWN_IN))
    p.add_argument('--curator-out', default=str(CURATOR_OUT))
    p.add_argument('--suggest-out', default=str(SUGGEST_OUT))
    args = p.parse_args()

    df = pd.read_csv(args.unknown_in)
    # Add helper columns
    df['variant_likelihood'] = pd.to_numeric(df.get('variant_likelihood', 0.5), errors='coerce').fillna(0.5)
    df['band'] = df['variant_likelihood'].apply(make_band)
    df['orthography_guess'] = df['feature'].apply(orthography_guess_from_feature)
    # Curator columns
    df['curator_label'] = ''
    df['curator_note'] = ''

    # Save curator workbook
    df.to_csv(args.curator_out, index=False)

    # Suggestions
    sugg_rows = []
    for _, r in df.iterrows():
        suggestion = ''
        if 0.73 <= r['variant_likelihood'] < 0.75 and not r['orthography_guess']:
            suggestion = 'meaningful?'
        elif r['orthography_guess']:
            suggestion = 'trivial?'
        sugg_rows.append({
            'app_id': r.get('app_id', ''),
            'feature': r.get('feature', ''),
            'variant_likelihood': r.get('variant_likelihood', ''),
            'suggestion': suggestion
        })
    pd.DataFrame(sugg_rows).to_csv(args.suggest_out, index=False)

    print(f"Wrote {args.curator_out} and {args.suggest_out}")

if __name__ == '__main__':
    main()
