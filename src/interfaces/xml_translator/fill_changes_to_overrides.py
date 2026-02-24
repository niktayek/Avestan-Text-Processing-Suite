import argparse
import csv
import difflib
from collections import defaultdict, Counter
from pathlib import Path
import pandas as pd
import unicodedata
from typing import Dict, List, Tuple

try:
    from .feature_utils import (
        normalize_text,
        strip_decorative_punct,
        strip_combining,
        tokenize_graphemes,
        canonical_feature,
        canonicalize_token_for_feature,
        is_avestan_token,
    )
except Exception:
    # Fallback when executed as a script (no package context)
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from src.interfaces.xml_translator.feature_utils import (
        normalize_text,
        strip_decorative_punct,
        strip_combining,
        tokenize_graphemes,
        canonical_feature,
        canonicalize_token_for_feature,
        is_avestan_token,
    )

DEFAULT_MATCHES = Path('res/Yasna/meta/yasna_matches.csv')
FEATURES_CSV = Path('res/Yasna/meta/feature_scored.csv')
OUT_FEATURES = Path('res/Yasna/meta/label_overrides_features.csv')
OUT_READINGS = Path('res/Yasna/meta/label_overrides_readings.csv')


def build_feature_index(path: Path) -> Dict[str, dict]:
    df = pd.read_csv(path)
    idx = {}
    for _, r in df.iterrows():
        key = canonical_feature(str(r.get('feature', '')))
        if not key:
            continue
        idx[key] = {
            'label': str(r.get('label', '')).strip().lower(),
            'variant_likelihood': float(r.get('variant_likelihood', 0) or 0),
            'doc_freq': int(r.get('doc_freq', 0) or 0),
            'punct_penalty_applied': bool(r.get('punct_penalty_applied', False)),
            'lexical_whitelist_applied': bool(r.get('lexical_whitelist_applied', False)),
            'orthography_match': bool(r.get('orthography_match', False)),
            'singleton_demoted': bool(r.get('singleton_demoted', False)),
        }
    return idx


def diff_graphemes(manual: str, ocr: str) -> List[Tuple[str, str]]:
    """Return list of atomic change tuples: (kind, value) or ("subst", "A→B")."""
    m = tokenize_graphemes(strip_decorative_punct(manual))
    o = tokenize_graphemes(strip_decorative_punct(ocr))
    sm = difflib.SequenceMatcher(None, m, o)
    changes: List[Tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        m_part = m[i1:i2]
        o_part = o[j1:j2]
        if tag == 'replace' and len(m_part) == len(o_part):
            for mt, ot in zip(m_part, o_part):
                if mt != ot:
                    A = canonicalize_token_for_feature(ot)
                    B = canonicalize_token_for_feature(mt)
                    changes.append(('subst', f"{A}→{B}"))
        else:
            # expand insert/delete as individual graphemes
            if tag in ('delete', 'replace'):
                for mt in m_part:
                    changes.append(('delete', canonicalize_token_for_feature(mt)))
            if tag in ('insert', 'replace'):
                for ot in o_part:
                    changes.append(('insert', canonicalize_token_for_feature(ot)))
    return changes


def decide_label(feature_meta: dict, change_kind: str, change_val: str) -> str:
    # Defaults
    label = feature_meta.get('label', '')
    variant_likelihood = feature_meta.get('variant_likelihood', 0.0)
    doc_freq = feature_meta.get('doc_freq', 0)
    punct_penalty_applied = bool(feature_meta.get('punct_penalty_applied', False))
    lexical_whitelist_applied = bool(feature_meta.get('lexical_whitelist_applied', False))
    orthography_match = bool(feature_meta.get('orthography_match', False))
    singleton_demoted = bool(feature_meta.get('singleton_demoted', False))

    # meaningful rules
    if label == 'variant' and doc_freq >= 2 and variant_likelihood >= 0.75 and not punct_penalty_applied:
        return 'meaningful'
    if change_kind in ('insert', 'delete') and is_avestan_token(change_val) and len(change_val) >= 2:
        return 'meaningful'
    if lexical_whitelist_applied:
        return 'meaningful'

    # trivial rules
    if label == 'reading' or orthography_match or punct_penalty_applied or singleton_demoted:
        return 'trivial'
    if doc_freq >= 3 and variant_likelihood < 0.72:
        return 'trivial'

    return ''


def normalized_equal(a: str, b: str) -> bool:
    a1 = strip_decorative_punct(strip_combining(a))
    b1 = strip_decorative_punct(strip_combining(b))
    return normalize_text(a1) == normalize_text(b1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--matches', default=str(DEFAULT_MATCHES))
    ap.add_argument('--features', default=str(FEATURES_CSV))
    ap.add_argument('--out-features', default=str(OUT_FEATURES))
    ap.add_argument('--out-readings', default=str(OUT_READINGS))
    ap.add_argument('--dry-run', action='store_true', help='Write *_preview.csv instead of outputs')
    args = ap.parse_args()

    matches_path = Path(args.matches)
    feat_idx = build_feature_index(Path(args.features))

    if not matches_path.exists():
        print(f"No matches at {matches_path}")
        return

    df = pd.read_csv(matches_path)
    ocr_col = 'ocr_word'
    manual_col = 'manual_word'

    if ocr_col not in df.columns or manual_col not in df.columns:
        raise SystemExit(f"Matches CSV must contain columns '{ocr_col}', '{manual_col}'")

    feat_overrides: Dict[str, str] = {}  # feature -> label
    read_overrides: Dict[Tuple[str, str], str] = {}  # (app_id, rdg_text) -> label

    unmapped_counter = Counter()
    counts = Counter()

    keys_list = list(feat_idx.keys())

    for _, r in df.iterrows():
        ocr = normalize_text(r.get(ocr_col, ''))
        manual = normalize_text(r.get(manual_col, ''))
        if not ocr or not manual:
            continue

        # Grapheme diffs to atomic changes
        changes = diff_graphemes(manual, ocr)
        # If nothing changed under normalized comparison, trivial and skip
        if normalized_equal(ocr, manual):
            continue

        # Build decisions per change, first match wins meaningful over trivial
        row_app_id = str(r.get('app_id', '') or '')
        # prefer observed reading text (ocr) for reading-level override when present
        rdg_text = ocr

        for kind, val in changes:
            if kind == 'subst':
                feat_key = canonical_feature(val)
            elif kind == 'insert':
                feat_key = f"{val} inserted"
            elif kind == 'delete':
                feat_key = f"{val} deleted"
            else:
                continue

            meta = feat_idx.get(feat_key)
            chosen_key = feat_key
            if meta is None:
                # fuzzy to nearest feature key
                close = difflib.get_close_matches(feat_key, keys_list, n=1, cutoff=0.6)
                if close:
                    chosen_key = close[0]
                    meta = feat_idx.get(chosen_key)
            if meta is None:
                unmapped_counter[feat_key] += 1
                continue

            decision = decide_label(meta, kind, val)
            if not decision:
                continue

            # Feature-level override preferred; de-dupe with priority meaningful > trivial
            prev = feat_overrides.get(chosen_key)
            if prev is None or (prev == 'trivial' and decision == 'meaningful'):
                feat_overrides[chosen_key] = decision
            # Reading-level if we have app_id + rdg_text
            if row_app_id and rdg_text:
                rk = (row_app_id, rdg_text)
                prev_r = read_overrides.get(rk)
                if prev_r is None or (prev_r == 'trivial' and decision == 'meaningful'):
                    read_overrides[rk] = decision

            counts[decision] += 1

    # Output
    out_feat = Path(args.out_features)
    out_read = Path(args.out_readings)
    if args.dry_run:
        out_feat = out_feat.with_name(out_feat.stem + '_preview.csv')
        out_read = out_read.with_name(out_read.stem + '_preview.csv')

    pd.DataFrame(
        [{'feature': k, 'label_override': v} for k, v in sorted(feat_overrides.items())]
    ).to_csv(out_feat, index=False)

    pd.DataFrame(
        [{'app_id': k[0], 'rdg_text': k[1], 'label_override': v} for k, v in sorted(read_overrides.items())]
    ).to_csv(out_read, index=False)

    # Summary
    meaningful = counts['meaningful']
    trivial = counts['trivial']
    unknown = sum(unmapped_counter.values())
    print(f"Overrides written: features={len(feat_overrides)}, readings={len(read_overrides)}")
    print(f"Decisions: meaningful={meaningful}, trivial={trivial}, unknown={unknown}")
    if unmapped_counter:
        print("Top unmapped (suggestions):")
        for feat, c in unmapped_counter.most_common(10):
            sugg = difflib.get_close_matches(feat, keys_list, n=1, cutoff=0.0)
            print(f"  {feat}  (count={c})  → nearest: {sugg[0] if sugg else '-'}")


if __name__ == '__main__':
    main()
