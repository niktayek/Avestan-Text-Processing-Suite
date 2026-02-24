"""
Normalize old-format tei_snippets_v3.csv to app-level format for v3 annotation.

Inputs:
- tei_snippets_v3.csv (locus, feature, ms_list, app_xml_stub)
- feature_scored.csv (feature, variant_likelihood, ...)
- TEI XML files in res/Yasna/apparatus/multi/*.xml (for app_id lookup)

Outputs:
- tei_snippets_v3_normalized.csv (app_id, rdg_text, wit_list, variant_likelihood, feature)
- snippets_unresolved.csv (rows where app_id could not be resolved)

Logic:
- Extract app_id from app_xml_stub if present (xml:id="app-…")
- If missing, try to match locus to <div xml:id="…"> and rdg_text to <rdg> in TEI files
- If multiple or no candidates, leave app_id empty and log to unresolved
- Normalize wit_list to #msXXXX tokens
- Left-join feature_scored.csv by feature to fill variant_likelihood
"""


# --- Imports ---
import re, csv, unicodedata, difflib
from pathlib import Path
import pandas as pd
from lxml import etree

# --- Namespace ---
NS = {'t': 'http://www.tei-c.org/ns/1.0'}

# --- Paths ---
TEI_DIR = Path("res/Yasna/apparatus/multi")
SNIPPETS_CSV = Path("res/Yasna/meta/tei_snippets_v3.csv")
FEATURES_CSV = Path("res/Yasna/meta/feature_scored.csv")
OUT_CSV = Path("res/Yasna/meta/tei_snippets_v3_normalized.csv")
UNRESOLVED_CSV = Path("res/Yasna/meta/snippets_unresolved.csv")

# --- Utilities ---
def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r'[\[\],.;:·⸳]', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def fuzzy_eq(a, b, thresh=0.92):
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return ratio >= thresh

def extract_app_id_from_stub(stub: str) -> str:
    m = re.search(r'xml:id\s*=\s*"(app-[^"\s]+)"', stub)
    if m:
        return m.group(1)
    m = re.search(r'<app[^>]*id\s*=\s*"(app-[^"\s]+)"', stub)
    if m:
        return m.group(1)
    return ""

def normalize_wit_list(ms_list: str) -> str:
    tokens = re.split(r'[ ,]+', ms_list.strip())
    out = []
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        if t.startswith("#ms"):
            out.append(t)
        elif t.isdigit():
            out.append(f"#ms{int(t):04d}")
        else:
            out.append(t)
    return " ".join(out)

# --- TEI Index ---
def build_tei_index():
    index = []
    for tei_path in TEI_DIR.glob("*.xml"):
        try:
            tree = etree.parse(str(tei_path))
            root = tree.getroot()
            for div in root.xpath('.//t:div[@xml:id]', namespaces=NS):
                div_id = div.get('{http://www.w3.org/XML/1998/namespace}id')
                for app in div.xpath('.//t:app[@xml:id]', namespaces=NS):
                    app_id = app.get('{http://www.w3.org/XML/1998/namespace}id')
                    lem_raw = ''.join(app.xpath('./t:lem//text()', namespaces=NS)) or ''
                    lem_norm = norm(lem_raw)
                    rdgs = []
                    for r in app.xpath('./t:rdg', namespaces=NS):
                        r_text = ''.join(r.xpath('.//text()', namespaces=NS)) or ''
                        r_norm = norm(r_text)
                        r_wits = (r.get('wit') or '').split()
                        rdgs.append({'raw': r_text, 'norm': r_norm, 'wits': r_wits})
                    index.append({
                        'file': str(tei_path),
                        'div_id': div_id,
                        'app_id': app_id,
                        'lem_raw': lem_raw,
                        'lem_norm': lem_norm,
                        'rdgs': rdgs
                    })
        except Exception:
            continue
    return index

# --- Main ---
def main():
    tei_index = build_tei_index()
    snippets = pd.read_csv(SNIPPETS_CSV)
    features = pd.read_csv(FEATURES_CSV)
    feat_likelihood = dict(zip(features["feature"].astype(str), features["variant_likelihood"]))

    out_rows = []
    unresolved_rows = []

    for idx, row in snippets.iterrows():
        locus = str(row.get("locus", "")).strip()
        feature = str(row.get("feature", "")).strip()
        ms_list = str(row.get("ms_list", "")).strip()
        stub = str(row.get("app_xml_stub", "")).strip()
        rdg_text = str(row.get("rdg_text", "")).strip()
        variant_likelihood = row.get("variant_likelihood", "")
        if variant_likelihood == "" or pd.isna(variant_likelihood):
            variant_likelihood = feat_likelihood.get(feature, "")

        # Try to extract app_id from stub
        app_id = extract_app_id_from_stub(stub)
        # Try to extract rdg_text from stub if not present
        if not rdg_text:
            m = re.search(r'<rdg[^>]*>(.*?)</rdg>', stub)
            if m:
                rdg_text = m.group(1).strip()

        wit_list = normalize_wit_list(ms_list)

        # If no app_id, try to infer from TEI index
        reason = ""
        candidate_app_ids = []
        if not app_id and locus:
            candidates = []
            for rec in tei_index:
                if rec['div_id'] == locus:
                    # Tier 1: exact normalized match to rdg or lem
                    for r in rec['rdgs']:
                        if norm(rdg_text) and norm(rdg_text) == r['norm']:
                            candidates.append((rec['app_id'], 'rdg_exact'))
                        elif norm(rdg_text) and norm(rdg_text) == rec['lem_norm']:
                            candidates.append((rec['app_id'], 'lem_exact'))
                    # Tier 2: fuzzy match
                    for r in rec['rdgs']:
                        if norm(rdg_text) and fuzzy_eq(rdg_text, r['raw']):
                            candidates.append((rec['app_id'], 'rdg_fuzzy'))
                        elif norm(rdg_text) and fuzzy_eq(rdg_text, rec['lem_raw']):
                            candidates.append((rec['app_id'], 'lem_fuzzy'))
            # Accept best candidate
            if candidates:
                # Prefer exact, then fuzzy
                tier_order = ['rdg_exact', 'lem_exact', 'rdg_fuzzy', 'lem_fuzzy']
                for tier in tier_order:
                    tier_cands = [c for c in candidates if c[1] == tier]
                    if len(tier_cands) == 1:
                        app_id = tier_cands[0][0]
                        break
                    elif len(tier_cands) > 1:
                        candidate_app_ids = [c[0] for c in tier_cands]
                        reason = f"ambiguous ({tier})"
                        break
                if not app_id and not candidate_app_ids:
                    # Fallback: take first fuzzy
                    app_id = candidates[0][0]
            else:
                reason = "no match in div"

        out_row = {
            "app_id": app_id,
            "rdg_text": rdg_text,
            "wit_list": wit_list,
            "variant_likelihood": variant_likelihood,
            "feature": feature,
        }
        if not app_id:
            unresolved_rows.append({
                **out_row,
                "locus": locus,
                "reason": reason,
                "candidate_app_ids": ",".join(candidate_app_ids)
            })
        out_rows.append(out_row)

    # Write normalized CSV
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["app_id", "rdg_text", "wit_list", "variant_likelihood", "feature"])
        writer.writeheader()
        writer.writerows([r for r in out_rows if r["app_id"]])

    # Write unresolved CSV
    if unresolved_rows:
        with UNRESOLVED_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["app_id", "rdg_text", "wit_list", "variant_likelihood", "feature", "locus", "reason", "candidate_app_ids"])
            writer.writeheader()
            writer.writerows(unresolved_rows)

    print(f"Wrote {OUT_CSV} ({sum(1 for r in out_rows if r['app_id'])} rows)")
    print(f"Wrote {UNRESOLVED_CSV} ({len(unresolved_rows)} unresolved)")

if __name__ == "__main__":
    main()