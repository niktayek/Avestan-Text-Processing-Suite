"""
Annotate TEI apparatus <rdg> elements with v3 scores and classifications.

Inputs
- tei_snippets_v3.csv with columns:
  app_id, rdg_text, wit_list, variant_likelihood, feature
- feature_scored.csv with columns:
  feature, variant_likelihood, label, doc_freq, total_freq,
  orthography_match (optional), punct_penalty_applied, singleton_demoted,
  lexical_whitelist_applied, unstable (optional)
- Optional feature_label_changes.csv (for unstable inference via changed_label)

Outputs
- Annotated TEI XML files saved as sibling .v3.xml
- Adds/ensures <taxonomy xml:id="varClass"> in <teiHeader>
- Writes unknown_review.csv with all @ana="#unknown" rows

Usage
  python src/interfaces/xml_translator/annotate_variants_v3.py \
    --tei /abs/path/res/Yasna/apparatus/multi/apparatus_multi_Y1_4ms_spans.xml \
    --snippets /abs/path/res/Yasna/meta/tei_snippets_v3.csv \
    --features /abs/path/res/Yasna/meta/feature_scored.csv \
    --label-changes /abs/path/res/Yasna/meta/feature_label_changes.csv \
    --unknown-out /abs/path/res/Yasna/meta/unknown_review.csv

Notes
- If tei_snippets_v3.csv lacks required columns, the script will stop with a
  helpful error. The repository currently contains an older format
  (locus, feature, ms_list, app_xml_stub). That file cannot support per-app
  insertion because it does not provide app_id or rdg_text.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from lxml import etree

TEI_NS = "http://www.tei-c.org/ns/1.0"
NSMAP = {None: TEI_NS}


@dataclass
class FeatureScore:
    feature: str
    variant_likelihood: float
    label: str
    doc_freq: int
    total_freq: int
    orthography_match: bool
    punct_penalty_applied: bool
    singleton_demoted: bool
    lexical_whitelist_applied: bool
    unstable: bool


def load_feature_scores(features_csv: Path, label_changes_csv: Optional[Path]) -> Dict[str, FeatureScore]:
    df = pd.read_csv(features_csv)

    # Normalize expected columns
    def get_bool(col: str, default: bool = False) -> List[bool]:
        return list(df[col].astype(bool)) if col in df.columns else [default] * len(df)

    unstable_map: Dict[str, bool] = {}
    if label_changes_csv and label_changes_csv.exists():
        ch = pd.read_csv(label_changes_csv)
        if "feature" in ch.columns and "changed_label" in ch.columns:
            unstable_map = dict(zip(ch["feature"], ch["changed_label"].astype(bool)))

    scores: Dict[str, FeatureScore] = {}
    for _, row in df.iterrows():
        feat = str(row["feature"]).strip()
        scores[feat] = FeatureScore(
            feature=feat,
            variant_likelihood=float(row.get("variant_likelihood", 0.0) or 0.0),
            label=str(row.get("label", "")).strip(),
            doc_freq=int(row.get("doc_freq", 0) or 0),
            total_freq=int(row.get("total_freq", 0) or 0),
            orthography_match=bool(row.get("orthography_match", False)),
            punct_penalty_applied=bool(row.get("punct_penalty_applied", False)),
            singleton_demoted=bool(row.get("singleton_demoted", False)),
            lexical_whitelist_applied=bool(row.get("lexical_whitelist_applied", False)),
            unstable=bool(row.get("unstable", unstable_map.get(feat, False))),
        )
    return scores


def classify(score: FeatureScore) -> Tuple[str, str]:
    """Return (ana_value, reason) following the policy with precedence:
    unknown > meaningful > trivial. cert comes from score.variant_likelihood.
    """
    vl = score.variant_likelihood
    # Unknown
    if (0.70 <= vl < 0.75) or score.unstable or (
        score.orthography_match and score.doc_freq >= 3 and vl >= 0.72
    ):
        return ("#unknown", "borderline/unstable")
    # Meaningful
    if (
        (score.label == "variant" and not (score.orthography_match or score.punct_penalty_applied))
        or score.lexical_whitelist_applied
        or (vl >= 0.75 and score.doc_freq >= 3)
    ):
        return ("#meaningful", "meets-meaningful-policy")
    # Trivial
    if (
        score.label == "reading"
        or score.orthography_match
        or score.punct_penalty_applied
        or score.singleton_demoted
    ):
        return ("#trivial", "meets-trivial-policy")
    # Default conservative
    return ("#unknown", "fallback")


def ensure_taxonomy(root: etree._Element) -> None:
    teiHeader = root.find(".{%s}teiHeader" % TEI_NS)
    if teiHeader is None:
        teiHeader = etree.Element("teiHeader", nsmap=NSMAP)
        root.insert(0, teiHeader)
    encodingDesc = teiHeader.find(".{%s}encodingDesc" % TEI_NS)
    if encodingDesc is None:
        encodingDesc = etree.SubElement(teiHeader, "encodingDesc")
    taxonomy = encodingDesc.find(".{%s}taxonomy[@xml:id='varClass']" % TEI_NS)
    if taxonomy is None:
        taxonomy = etree.SubElement(encodingDesc, "taxonomy")
        taxonomy.set("{http://www.w3.org/XML/1998/namespace}id", "varClass")
        for cat_id, desc in (
            ("meaningful", "Meaningful variant (philologically significant)"),
            ("trivial", "Trivial or orthographic/diacritic/punctuation reading"),
            ("unknown", "Borderline or unstable; requires review"),
        ):
            cat = etree.SubElement(taxonomy, "category")
            cat.set("{http://www.w3.org/XML/1998/namespace}id", cat_id)
            cd = etree.SubElement(cat, "catDesc")
            cd.text = desc


def find_app_by_id(root: etree._Element, app_id: str) -> Optional[etree._Element]:
    return root.find(".//{%s}app[@xml:id='%s']" % (TEI_NS, app_id))


def derive_n_from_feature(feature: str) -> str:
    # Turn "xᵛ for x" into "xᵛ→x"; otherwise return feature
    if " for " in feature:
        a, b = feature.split(" for ", 1)
        return f"{a}→{b}"
    return feature


def annotate_file(
    tei_path: Path,
    snippets: pd.DataFrame,
    feature_scores: Dict[str, FeatureScore],
    unknown_rows: List[Dict[str, str]],
) -> Tuple[int, int]:
    tree = etree.parse(str(tei_path))
    root = tree.getroot()
    ensure_taxonomy(root)

    added = 0
    missing_app = 0

    # Select rows for which app_id exists in this TEI
    for _, r in snippets.iterrows():
        app_id = str(r["app_id"]).strip()
        rdg_text = str(r["rdg_text"]) if not pd.isna(r["rdg_text"]) else ""
        wit_list = str(r["wit_list"]).strip()
        feature = str(r["feature"]).strip()
        vl = r.get("variant_likelihood")
        try:
            vl = float(vl)
        except Exception:
            vl = float(feature_scores.get(feature, FeatureScore(feature, 0.0, "", 0, 0, False, False, False, False, False)).variant_likelihood)

        app = find_app_by_id(root, app_id)
        if app is None:
            missing_app += 1
            continue

        score = feature_scores.get(feature)
        if score is None:
            # Create a minimal placeholder score with available info
            score = FeatureScore(
                feature=feature,
                variant_likelihood=vl,
                label="",
                doc_freq=0,
                total_freq=0,
                orthography_match=False,
                punct_penalty_applied=False,
                singleton_demoted=False,
                lexical_whitelist_applied=False,
                unstable=False,
            )
        ana, reason = classify(score)

        # Idempotency: avoid duplicate score-v3 rdgs with same wit and n
        n_val = derive_n_from_feature(feature)
        existing = app.findall(".{%s}rdg[@resp='score-v3']" % TEI_NS)
        if any((rdg.get("wit", "").strip() == wit_list and rdg.get("n", "") == n_val) for rdg in existing):
            continue

        rdg = etree.SubElement(app, "rdg")
        rdg.set("wit", wit_list)
        rdg.set("type", "var")
        rdg.set("resp", "score-v3")
        rdg.set("cert", f"{vl:.3f}")
        rdg.set("ana", ana)
        rdg.set("n", n_val)
        if rdg_text:
            rdg.text = rdg_text
        added += 1

        if ana == "#unknown":
            unknown_rows.append({
                "tei_file": str(tei_path),
                "app_id": app_id,
                "feature": feature,
                "wit_list": wit_list,
                "rdg_text": rdg_text,
                "variant_likelihood": f"{vl:.3f}",
                "reason": reason,
            })

    out_path = tei_path.with_suffix(tei_path.suffix.replace(".xml", "") + ".v3.xml") if tei_path.suffix.endswith(".xml") else tei_path.with_suffix(tei_path.suffix + ".v3.xml")
    tree.write(str(out_path), encoding="UTF-8", xml_declaration=True, pretty_print=True)
    return added, missing_app


def main():
    ap = argparse.ArgumentParser(description="Annotate TEI apparatus with v3 scores and classifications")
    ap.add_argument("--tei", nargs="+", type=Path, help="TEI XML file(s) or directories (will scan *.xml in dirs)")
    ap.add_argument("--snippets", type=Path, required=True, help="Path to tei_snippets_v3.csv with app_id/rdg_text/wit_list")
    ap.add_argument("--features", type=Path, required=True, help="Path to feature_scored.csv")
    ap.add_argument("--label-changes", type=Path, help="Optional feature_label_changes.csv for unstable inference")
    ap.add_argument("--unknown-out", type=Path, default=Path("unknown_review.csv"), help="Path to write unknown_review.csv")
    args = ap.parse_args()

    # Load snippets
    snippets = pd.read_csv(args.snippets)
    required_cols = {"app_id", "rdg_text", "wit_list", "variant_likelihood", "feature"}
    missing = required_cols - set(snippets.columns)
    if missing:
        raise SystemExit(
            f"tei_snippets_v3.csv is missing columns: {missing}.\n"
            "Expected columns: app_id, rdg_text, wit_list, variant_likelihood, feature.\n"
            "The current repository contains an older format (locus, feature, ms_list, app_xml_stub)\n"
            "which cannot be used for per-<app> insertion. Please provide the updated CSV."
        )

    # Load feature scores
    scores = load_feature_scores(args.features, args.label_changes)

    # Expand TEI file arguments
    tei_files: List[Path] = []
    for p in args.tei:
        if p.is_dir():
            tei_files.extend(sorted(p.glob("*.xml")))
        elif p.suffix.lower() == ".xml" and p.exists():
            tei_files.append(p)
    if not tei_files:
        raise SystemExit("No TEI XML files found to annotate.")

    unknown_rows: List[Dict[str, str]] = []
    total_added = 0
    total_missing = 0
    for f in tei_files:
        added, missing = annotate_file(f, snippets, scores, unknown_rows)
        print(f"Annotated {f.name}: added={added}, missing_app_ids={missing}")
        total_added += added
        total_missing += missing

    # Write unknown review CSV
    if unknown_rows:
        args.unknown_out.parent.mkdir(parents=True, exist_ok=True)
        with args.unknown_out.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=[
                "tei_file", "app_id", "feature", "wit_list", "rdg_text", "variant_likelihood", "reason"
            ])
            writer.writeheader()
            writer.writerows(unknown_rows)
        print(f"Wrote unknown review CSV: {args.unknown_out} ({len(unknown_rows)} rows)")
    else:
        print("No #unknown rows; review CSV not written.")

    print(f"Done. Total added={total_added}, total missing_app_ids={total_missing}")


if __name__ == "__main__":
    main()
