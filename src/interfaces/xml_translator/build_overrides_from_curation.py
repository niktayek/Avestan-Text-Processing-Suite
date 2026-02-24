import argparse
import pandas as pd
from pathlib import Path

CURATOR_IN = Path('res/Yasna/meta/unknown_review_for_curator.csv')
OUT_FEATURES = Path('res/Yasna/meta/label_overrides_features.csv')
OUT_READINGS = Path('res/Yasna/meta/label_overrides_readings.csv')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--curator-in', default=str(CURATOR_IN))
    p.add_argument('--out-features', default=str(OUT_FEATURES))
    p.add_argument('--out-readings', default=str(OUT_READINGS))
    args = p.parse_args()

    try:
        df = pd.read_csv(args.curator_in)
    except FileNotFoundError:
        # Create empty override files with headers
        pd.DataFrame(columns=['feature','label_override']).to_csv(args.out_features, index=False)
        pd.DataFrame(columns=['app_id','rdg_text','label_override']).to_csv(args.out_readings, index=False)
        print(f"Created empty overrides: {args.out_features}, {args.out_readings}")
        return

    # Normalize curator_label
    df['curator_label'] = (df.get('curator_label','').astype(str).str.strip().str.lower())

    # Feature-level overrides: group by feature when curator_label is set to meaningful/trivial consistently
    feat_overrides = []
    for feature, sub in df.groupby('feature'):
        labels = set([l for l in sub['curator_label'] if l in ('meaningful','trivial')])
        if len(labels) == 1:
            feat_overrides.append({'feature': feature, 'label_override': labels.pop()})
    pd.DataFrame(feat_overrides).to_csv(args.out_features, index=False)

    # Reading-level overrides: rows where curator_label is set and possibly conflicts with feature-level
    read_overrides = []
    feat_map = {r['feature']: r['label_override'] for r in feat_overrides}
    for _, r in df.iterrows():
        lab = r.get('curator_label','')
        if lab in ('meaningful','trivial'):
            f = r.get('feature','')
            if not f or f not in feat_map or feat_map[f] != lab:
                read_overrides.append({
                    'app_id': r.get('app_id',''),
                    'rdg_text': r.get('rdg_text',''),
                    'label_override': lab
                })
    pd.DataFrame(read_overrides).to_csv(args.out_readings, index=False)

    print(f"Wrote overrides: {args.out_features} ({len(feat_overrides)}) and {args.out_readings} ({len(read_overrides)})")

if __name__ == '__main__':
    main()
