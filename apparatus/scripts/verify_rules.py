import csv
import argparse
from pathlib import Path
from src.interfaces.xml_translator.tei_annotate_v3_direct import (
    diff_tokens_to_atomic_features,
    comp_norm,
    family_normalize,
    compile_orthography_families,
    load_classification_policy,
    classify_by_policy,
)

def classify_pair(lem: str, rdg: str, families: dict, policy: dict, rdg_groups: set[str] | None = None) -> tuple[str, str]:
    ops = diff_tokens_to_atomic_features(lem, rdg)
    labels = []
    for op in ops:
        lab = classify_by_policy(op, policy, rdg_groups or set()) or ''
        if '→' in op and not lab:
            a, b = op.split('→', 1)
            if comp_norm(a) == comp_norm(b):
                lab = 'trivial'
            else:
                ah, _, an = family_normalize(a, families)
                bh, _, bn = family_normalize(b, families)
                if (ah or bh) and an == bn:
                    lab = 'trivial'
        labels.append(lab)
    if any(l == 'meaningful' for l in labels):
        return 'meaningful', '; '.join(ops[:3]) if len(ops) > 1 else (ops[0] if ops else 'no_change')
    if any(l == 'trivial' for l in labels) or not ops:
        return 'trivial', '; '.join(ops[:3]) if ops else 'no_change'
    return 'unknown', 'mixed'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tests', default='res/Yasna/meta/rule_tests.csv')
    ap.add_argument('--families', default='res/Yasna/meta/orthography_families_v4.yaml')
    ap.add_argument('--policy', default='res/Yasna/meta/classification_policy.yaml')
    args = ap.parse_args()

    fam = compile_orthography_families(args.families)
    pol = load_classification_policy(args.policy)

    rows = list(csv.DictReader(open(args.tests, 'r', encoding='utf-8')))
    ok = 0
    for r in rows:
        lab, n = classify_pair(r['lem'], r['rdg'], fam, pol, rdg_groups=set())
        exp = r.get('expected_label','').strip()
        if lab == exp:
            ok += 1
        print(f"{r['lem']} | {r['rdg']} => {lab} ({n}) [exp={exp}]")
    print(f"Passed {ok}/{len(rows)}")

if __name__ == '__main__':
    main()
