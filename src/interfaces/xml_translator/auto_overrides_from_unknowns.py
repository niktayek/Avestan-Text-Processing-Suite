import argparse
from pathlib import Path
import pandas as pd

try:
    from .feature_utils import canonical_feature
except Exception:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from src.interfaces.xml_translator.feature_utils import canonical_feature

UNKNOWN_IN = Path('res/Yasna/meta/unknown_review_after_overrides.csv')
FEATURES_CSV = Path('res/Yasna/meta/feature_scored.csv')
OUT_FEATURES = Path('res/Yasna/meta/label_overrides_features.csv')
OUT_READINGS = Path('res/Yasna/meta/label_overrides_readings.csv')

# Simple heuristic: if variant_likelihood >= 0.78 and doc_freq >= 2 and not punct_penalty, propose meaningful; if orthography_guess or punct_penalty, propose trivial.

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--unknown-in', default=str(UNKNOWN_IN))
    ap.add_argument('--features', default=str(FEATURES_CSV))
    ap.add_argument('--out-features', default=str(OUT_FEATURES))
    ap.add_argument('--out-readings', default=str(OUT_READINGS))
    args = ap.parse_args()

    # Load unknowns and features
    try:
        du = pd.read_csv(args.unknown_in)
    except FileNotFoundError:
        print(f"No unknowns at {args.unknown_in}")
        return
    try:
        df = pd.read_csv(args.features)
    except FileNotFoundError:
        print(f"No features at {args.features}")
        return

    feat_meta = {canonical_feature(str(r.get('feature',''))): r for _, r in df.iterrows()}

    # Load existing outputs to union
    try:
        outf = pd.read_csv(args.out_features)
    except Exception:
        outf = pd.DataFrame(columns=['feature','label_override'])
    try:
        outr = pd.read_csv(args.out_readings)
    except Exception:
        outr = pd.DataFrame(columns=['app_id','rdg_text','label_override'])

    feat_map = {str(r['feature']): str(r['label_override']) for _, r in outf.iterrows() if 'feature' in r and 'label_override' in r}
    read_map = {(str(r['app_id']), str(r['rdg_text'])): str(r['label_override']) for _, r in outr.iterrows() if 'app_id' in r and 'rdg_text' in r and 'label_override' in r}

    meaningful_over_trivial = {'trivial': 0, 'meaningful': 1}

    added_feat = added_read = 0

    for _, r in du.iterrows():
        feat = canonical_feature(str(r.get('feature','')))
        app_id = str(r.get('app_id','') or '')
        rdg_text = str(r.get('rdg_text','') or '')
        meta = feat_meta.get(feat, {})
        vlik = float(meta.get('variant_likelihood', r.get('variant_likelihood', 0) or 0))
        dfreq = int(meta.get('doc_freq', 0) or 0)
        punct = bool(meta.get('punct_penalty_applied', False))
        ortho = bool(r.get('orthography_guess', False))

        decision = ''
        if not punct and vlik >= 0.78 and dfreq >= 2:
            decision = 'meaningful'
        elif punct or ortho:
            decision = 'trivial'
        else:
            continue

        # feature-level
        prev = feat_map.get(feat)
        if prev is None or meaningful_over_trivial.get(decision, 0) > meaningful_over_trivial.get(prev, 0):
            feat_map[feat] = decision
            added_feat += 1
        # reading-level when available
        if app_id and rdg_text:
            key = (app_id, rdg_text)
            prevr = read_map.get(key)
            if prevr is None or meaningful_over_trivial.get(decision, 0) > meaningful_over_trivial.get(prevr, 0):
                read_map[key] = decision
                added_read += 1

    # Write back
    pd.DataFrame([{'feature': k, 'label_override': v} for k, v in sorted(feat_map.items())]).to_csv(args.out_features, index=False)
    pd.DataFrame([{'app_id': k[0], 'rdg_text': k[1], 'label_override': v} for k, v in sorted(read_map.items())]).to_csv(args.out_readings, index=False)

    print(f"Merged auto-overrides from unknowns: +features={added_feat}, +readings={added_read}")

if __name__ == '__main__':
    main()
