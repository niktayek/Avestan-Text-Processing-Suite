import argparse
from pathlib import Path
import pandas as pd
import unicodedata


def nfc(s: str) -> str:
    return unicodedata.normalize('NFC', str(s))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--unknowns', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--min-count', type=int, default=2)
    p.add_argument('--min-likelihood', type=float, default=0.75)
    args = p.parse_args()

    u_path = Path(args.unknowns)
    if not u_path.exists():
        print(f"No unknowns file at {u_path}")
        return

    df = pd.read_csv(u_path)
    # Normalize expected columns
    df['feature'] = df.get('feature', '').astype(str).fillna('').map(nfc).str.strip()
    df['variant_likelihood'] = pd.to_numeric(df.get('variant_likelihood', 0.5), errors='coerce').fillna(0.5)

    # Filter: keep meaningful-looking unknowns by likelihood; feature must look like a change (subst/insert/delete canonical)
    cand = df[(df['feature'] != '') & (df['variant_likelihood'] >= args.min_likelihood)]

    # Aggregate by feature
    grp = cand.groupby('feature', as_index=False).agg(
        doc_freq=('feature', 'count'),
        variant_likelihood=('variant_likelihood', 'mean'),
    )
    # Threshold on count
    grp = grp[grp['doc_freq'] >= args.min_count]

    # Shape to feature_scored-like schema expected by annotator
    if grp.empty:
        pd.DataFrame(columns=['feature','label','variant_likelihood','doc_freq','orthography_match?','punct_penalty_applied?','singleton_demoted?','lexical_whitelist_applied?']).to_csv(args.out, index=False)
        print(f"No candidates met thresholds; wrote empty {args.out}")
        return

    grp['label'] = 'variant'
    grp['orthography_match?'] = False
    grp['punct_penalty_applied?'] = False
    grp['singleton_demoted?'] = False
    grp['lexical_whitelist_applied?'] = False

    # Order columns
    cols = ['feature','label','variant_likelihood','doc_freq','orthography_match?','punct_penalty_applied?','singleton_demoted?','lexical_whitelist_applied?']
    grp[cols].to_csv(args.out, index=False)
    print(f"Learned features: {len(grp)} → {args.out}")


if __name__ == '__main__':
    main()
