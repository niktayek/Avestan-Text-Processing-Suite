import argparse
import pandas as pd
import unicodedata
import re
import difflib
import yaml
from lxml import etree
from pathlib import Path
from typing import List, Tuple

# Try to import grapheme utils from our helper module (fallback to absolute when run as script)
try:
    from .feature_utils import tokenize_graphemes, canonical_feature
except Exception:
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from src.interfaces.xml_translator.feature_utils import tokenize_graphemes, canonical_feature

NS = {'tei': 'http://www.tei-c.org/ns/1.0', 'xml': 'http://www.w3.org/XML/1998/namespace'}

# --- Utilities ---
PUNCT_CLASS = r"[.,;:·⸳]"

def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", str(s))

def to_base(s: str) -> str:
    # remove combining, lowercase
    s = unicodedata.normalize("NFKD", str(s))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.lower()

def strip_decopunct(s: str) -> str:
    s = re.sub(PUNCT_CLASS, '', s)
    return s.rstrip('.')

def collapse_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def _punct_norm_full(s: str) -> str:
    # remove decorative punctuation, collapse spaces (compare-only)
    return collapse_ws(strip_decopunct(nfc(s)))

def _punct_norm_tokens(s: str) -> list[str]:
    # split on [\.\s]+ and compare token base-forms (diacritic-insensitive)
    return [to_base(t) for t in re.split(r'[\.\s]+', nfc(s)) if t]

def class_equiv(s: str) -> str:
    s = s.replace('aē', 'ae').replace('aō', 'ao')
    s = s.replace('ē', 'e').replace('ō','o').replace('ā','a').replace('ī','i').replace('ū','u')
    # sibilants and n variants
    s = s.replace('ṣ̌','s').replace('š','s').replace('ś','s').replace('ṣ','s')
    s = s.replace('ṇ','n')
    s = s.replace('ϑ','t')
    # NEW: drop word-initial y- before vowels (compare-only equivalence)
    s = re.sub(r'\b[yY](?=[aāeēiīoōuū])', '', s)
    return s

def comp_norm(s: str) -> str:
    # for comparison only
    s = nfc(s)
    s = strip_decopunct(s)
    s = collapse_ws(s)
    s = to_base(s)
    s = class_equiv(s)
    return s

def norm_text(s):
    s = unicodedata.normalize("NFC", str(s))
    s = re.sub(r'\s+', ' ', s)
    return s.strip().rstrip('.')

def compile_orthography_families(path: str|None):
    """Load orthography families config with optional flags.

    Expected schema per family:
      patterns: [regex, ...]
      compare_only_regex: [regex, ...]   # additional compare-only normalizers
      diacritic_insensitive: bool
      punctuation_insensitive: bool
    """
    if not path:
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f) or {}
        fams = {}
        for name, body in (cfg.get('families') or {}).items():
            pats = body.get('patterns', []) or []
            cmp_only = body.get('compare_only_regex', []) or []
            fams[name] = {
                'patterns': [re.compile(p, flags=re.IGNORECASE|re.UNICODE) for p in pats],
                'compare_only': [re.compile(p, flags=re.IGNORECASE|re.UNICODE) for p in cmp_only],
                'diacritic': bool(body.get('diacritic_insensitive', False)),
                'punct': bool(body.get('punctuation_insensitive', False)),
            }
        return fams
    except Exception:
        return {}

def load_whitelist(path: str|None):
    wl = set()
    if not path:
        return wl
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                t = line.strip()
                if t and not t.startswith('#'):
                    wl.add(t)
    except Exception:
        pass
    return wl

def family_normalize(text: str, families: dict) -> tuple[bool, str, str]:
    """Return whether any family normalization hit, the first family name hit, and normalized text.

    Applies both 'patterns' and 'compare_only' substitutions across all families (compositional),
    so multiple neutralizations can take effect before comparison.
    """
    tmp = text
    hit_any = False
    fam_name = ''
    for name, spec in families.items():
        local = False
        for p in spec.get('patterns', []):
            tmp2, n = p.subn('§', tmp)
            if n > 0:
                local = True
            tmp = tmp2
        for p in spec.get('compare_only', []):
            tmp2, n = p.subn('§', tmp)
            if n > 0:
                local = True
            tmp = tmp2
        if local and not fam_name:
            fam_name = name
        hit_any = hit_any or local
    return hit_any, fam_name, tmp

def token_diff_feature(lem: str, rdg: str):
    # Ignore punctuation-only tokens
    def tok_clean(t):
        t = collapse_ws(nfc(t))
        return re.sub(PUNCT_CLASS, '', t)
    lt = [t for t in collapse_ws(nfc(lem)).split(' ') if tok_clean(t)]
    rt = [t for t in collapse_ws(nfc(rdg)).split(' ') if tok_clean(t)]
    if lt == rt:
        return 'no_change'
    if abs(len(lt) - len(rt)) > 1:
        return 'subst'
    # single token insert/delete
    if len(rt) == len(lt) + 1:
        # inserted token in rdg
        for i in range(len(rt)):
            cand = rt[:i] + rt[i+1:]
            if cand == lt:
                return f"{rt[i]} inserted"
    if len(lt) == len(rt) + 1:
        for i in range(len(lt)):
            cand = lt[:i] + lt[i+1:]
            if cand == rt:
                return f"{lt[i]} deleted"
    # single token substitution
    if len(lt) == len(rt):
        diffs = [(a,b) for a,b in zip(lt,rt) if comp_norm(a) != comp_norm(b)]
        if len(diffs) == 1:
            a,b = diffs[0]
            return f"{b} for {a}"
    return 'subst'


# --- Atomic diff helpers ---
def _split_tokens_compare_only(text: str) -> List[str]:
    """Split text into tokens for comparison-only.
    - Do NOT split on '.'; treat punctuation as ignorable within tokens.
    - Strip decorative punctuation from tokens.
    Keeps order; drops empty tokens after punctuation stripping.
    """
    text = collapse_ws(nfc(text))
    # Split only on whitespace; avoid creating spurious tokens due to '.' inside words
    parts = re.split(r"\s+", text)
    # Remove decorative punctuation from each token so '.' doesn't contribute to atomics
    cleaned = []
    for p in parts:
        cp = re.sub(PUNCT_CLASS, '', p)
        if cp:
            cleaned.append(cp)
    return cleaned


def _diff_graphemes_atomic(lem_tok: str, rdg_tok: str) -> List[str]:
    """Return atomic ops between two tokens at grapheme level: A→B, X inserted, X deleted."""
    lt = tokenize_graphemes(lem_tok)
    rt = tokenize_graphemes(rdg_tok)
    sm = difflib.SequenceMatcher(None, lt, rt)
    ops: List[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        lpart = lt[i1:i2]
        rpart = rt[j1:j2]
        if tag == 'replace' and len(lpart) == len(rpart):
            for a, b in zip(lpart, rpart):
                if a != b:
                    ops.append(f"{b}→{a}")
        else:
            if tag in ('delete', 'replace'):
                for a in lpart:
                    ops.append(f"{a} deleted")
            if tag in ('insert', 'replace'):
                for b in rpart:
                    ops.append(f"{b} inserted")
    return ops


def diff_tokens_to_atomic_features(lem_text: str, rdg_text: str) -> List[str]:
    """Token-align lem vs rdg, then produce grapheme-level atomic ops across differing tokens."""
    ltoks = _split_tokens_compare_only(lem_text)
    rtoks = _split_tokens_compare_only(rdg_text)
    sm = difflib.SequenceMatcher(None, ltoks, rtoks)
    atomics: List[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        lseg = ltoks[i1:i2]
        rseg = rtoks[j1:j2]
        if tag == 'replace' and len(lseg) == len(rseg):
            for ltok, rtok in zip(lseg, rseg):
                if comp_norm(ltok) != comp_norm(rtok):
                    atomics.extend(_diff_graphemes_atomic(ltok, rtok))
        else:
            if tag in ('delete', 'replace'):
                for ltok in lseg:
                    # expand to grapheme-level deletes
                    for g in tokenize_graphemes(ltok):
                        atomics.append(f"{g} deleted")
            if tag in ('insert', 'replace'):
                for rtok in rseg:
                    for g in tokenize_graphemes(rtok):
                        atomics.append(f"{g} inserted")
    # canonicalize 'A for B' → 'A→B' if any such strings leaked in
    canon = []
    for op in atomics:
        if ' for ' in op:
            canon.append(canonical_feature(op))
        else:
            canon.append(op)
    return canon


def build_feature_catalog(features_df: pd.DataFrame) -> Tuple[dict, List[str]]:
    """Build a catalog map for feature lookup; also allow reversed keys and fuzzy fallback."""
    fmap = {}
    keys: List[str] = []
    for feat, row in features_df.iterrows():
        key = canonical_feature(feat)
        if key not in fmap:
            fmap[key] = row
            keys.append(key)
        # Also keep the textual 'A for B' variant for matching if present
        if '→' in key:
            a, b = key.split('→', 1)
            alt = f"{a} for {b}"
            if alt not in fmap:
                fmap[alt] = row
                keys.append(alt)
    return fmap, keys


def lookup_feature_score(key: str, fmap: dict, keys: List[str]) -> Tuple[dict, float]:
    """Return (row, confidence) for a feature key; try exact, reversed, then fuzzy."""
    # Exact
    if key in fmap:
        return fmap[key], 1.0
    # Try reversed orientation
    if '→' in key:
        a, b = key.split('→', 1)
        rev = f"{b}→{a}"
        if rev in fmap:
            return fmap[rev], 0.95
    # Try textual variant
    if '→' in key:
        a, b = key.split('→', 1)
        txt = f"{a} for {b}"
        if txt in fmap:
            return fmap[txt], 0.9
    # Fuzzy
    best = None
    best_r = 0.0
    for fk in keys:
        r = difflib.SequenceMatcher(None, key, fk).ratio()
        if r > best_r:
            best_r = r
            best = fk
    if best is not None and best_r >= 0.6:
        return fmap[best], best_r
    return {}, 0.0

def map_to_known_feature(canon: str, index_set: set[str]) -> tuple[str, float]:
    if canon in index_set:
        return canon, 1.0
    # fallback: fuzzy across index (could be large but manageable)
    best_feat, best = None, 0.0
    for feat in index_set:
        r = difflib.SequenceMatcher(None, canon, feat).ratio()
        if r > best:
            best, best_feat = r, feat
    return (best_feat if best_feat else canon), best

def feature_infer(lem, rdg, aggressive=False, index_set=None):
    lem = norm_text(lem)
    rdg = norm_text(rdg)
    if not rdg:
        return "deleted"
    if not lem and rdg:
        tokens = rdg.split()
        if len(tokens) == 1:
            return f"{tokens[0]} inserted"
        return "inserted"
    if lem != rdg:
        if aggressive:
            # Try token-level first
            feat = token_diff_feature(lem, rdg)
            canon = feat.replace(' for ', '→')
            if index_set is not None and feat not in ('subst','no_change'):
                mapped, conf = map_to_known_feature(canon, index_set)
                if conf >= 0.6:
                    return mapped
            # Try char-level with class equivalence
            lc = comp_norm(lem)
            rc = comp_norm(rdg)
            if lc != rc and len(lc) == len(rc):
                diffs = [(a,b) for a,b in zip(lc,rc) if a!=b]
                if len(diffs) == 1:
                    return canon
            # fallback
            return canon if canon in (index_set or set()) else 'subst'
        else:
            # Char-level diff
            if len(lem) == len(rdg):
                diffs = [(a, b) for a, b in zip(lem, rdg) if a != b]
                if len(diffs) == 1:
                    return f"{rdg} for {lem}"
            # Token-level diff
            lem_tokens = lem.split()
            rdg_tokens = rdg.split()
            if len(lem_tokens) == len(rdg_tokens):
                diffs = [(a, b) for a, b in zip(lem_tokens, rdg_tokens) if a != b]
                if len(diffs) == 1:
                    return f"{rdg_tokens[0]}→{lem_tokens[0]}"
            return "subst"
    return "no_change"

def round_cert(val):
    try:
        return f"{float(val):.3f}"
    except:
        return "0.500"

def load_label_changes(path):
    try:
        df = pd.read_csv(path)
        changed = set(df['feature'].astype(str))
        return changed
    except Exception:
        return set()

def ensure_taxonomy(tree):
    root = tree.getroot()
    header = root.find('.//tei:teiHeader', namespaces=NS)
    if header is None:
        return False
    enc = header.find('.//tei:encodingDesc', namespaces=NS)
    if enc is None:
        enc = etree.SubElement(header, '{http://www.tei-c.org/ns/1.0}encodingDesc')
    tax = enc.find('.//tei:taxonomy[@xml:id="varClass"]', namespaces=NS)
    if tax is None:
        tax = etree.SubElement(enc, '{http://www.tei-c.org/ns/1.0}taxonomy')
        tax.set('{http://www.w3.org/XML/1998/namespace}id', 'varClass')
        # Default categories for this project use 'variants' (meaningful), 'readings' (trivial), and 'missing'
        for cat in ['variants', 'readings', 'missing', 'unknown']:
            cat_elem = etree.SubElement(tax, '{http://www.tei-c.org/ns/1.0}category')
            cat_elem.set('{http://www.w3.org/XML/1998/namespace}id', cat)
            cat_elem.text = cat.capitalize()
    else:
        # Ensure the expected categories exist even if taxonomy already present
        existing = {c.get('{http://www.w3.org/XML/1998/namespace}id') for c in tax.findall('./tei:category', namespaces=NS)}
        for cat in ['variants', 'readings', 'missing', 'unknown']:
            if cat not in existing:
                cat_elem = etree.SubElement(tax, '{http://www.tei-c.org/ns/1.0}category')
                cat_elem.set('{http://www.w3.org/XML/1998/namespace}id', cat)
                cat_elem.text = cat.capitalize()
    return True

def classify(feature_row, label_changes):
    vlik = feature_row.get('variant_likelihood', 0.5)
    label = feature_row.get('label', '')
    doc_freq = feature_row.get('doc_freq', 0)
    orthography = feature_row.get('orthography_match?', False)
    punct = feature_row.get('punct_penalty_applied?', False)
    singleton = feature_row.get('singleton_demoted?', False)
    whitelist = feature_row.get('lexical_whitelist_applied?', False)
    unstable = feature_row.get('feature') in label_changes
    # UNKNOWN
    if (0.70 <= vlik < 0.75) or unstable or (orthography and doc_freq >= 3 and vlik >= 0.72):
        return 'unknown'
    # MEANINGFUL
    if (label == 'variant' and not orthography and not punct) or whitelist or (vlik >= 0.75 and doc_freq >= 3):
        return 'meaningful'
    # TRIVIAL
    return 'trivial'

def load_overrides(features_path: str|None, readings_path: str|None):
    feat_over = {}
    rdg_over = {}
    if features_path:
        try:
            df = pd.read_csv(features_path)
            for _, r in df.iterrows():
                f = str(r.get('feature','')).strip()
                lab = str(r.get('label_override','')).strip().lower()
                if f and lab in ('meaningful','trivial'):
                    feat_over[f] = lab
        except Exception:
            # handle empty/missing
            pass
    if readings_path:
        try:
            dr = pd.read_csv(readings_path)
            for _, r in dr.iterrows():
                app = str(r.get('app_id','')).strip()
                txt = norm_text(r.get('rdg_text',''))
                lab = str(r.get('label_override','')).strip().lower()
                if app and txt and lab in ('meaningful','trivial'):
                    rdg_over[(app, txt)] = lab
        except Exception:
            # handle empty/missing
            pass
    return feat_over, rdg_over

def load_classification_policy(path: str|None) -> dict:
    """Load classification policy rules from YAML.

        Schema (example):
      rules:
        - match: "ī→ū"           # exact atomic op
          label: "trivial"        # 'trivial' or 'meaningful'
          direction: "either"     # 'either'|'forward'|'reverse'
          notes: ""
                    groups: ["Iranian", "Indian"]  # optional: restrict rule to specific witness groups
                    exclude_groups: ["Indian"]       # optional: apply when NOT in these groups
        - match_regex: "i→e|e→i"  # regex over atomic op text
          label: "trivial"
          direction: "either"
    """
    if not path:
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        rules = data.get('rules') or []
        # normalize
        for r in rules:
            if 'direction' not in r:
                r['direction'] = 'either'
        data['rules'] = rules
        # normalize defaults
        dflt = (data.get('default_nontrivial_label') or '').strip().lower()
        if dflt not in ('', 'trivial', 'meaningful'):
            dflt = ''
        data['default_nontrivial_label'] = dflt
        return data
    except Exception:
        return {}

def _op_match_rule(op: str, rule: dict) -> bool:
    # Handle direction on exact 'match' with arrow
    m = rule.get('match', '')
    if m:
        direction = (rule.get('direction') or 'either').lower()
        if '→' in m and '→' in op:
            if direction == 'either':
                if op == m:
                    return True
                a, b = m.split('→', 1)
                ra = b + '→' + a
                return op == ra
            elif direction == 'forward':
                return op == m
            elif direction == 'reverse':
                a, b = m.split('→', 1)
                ra = b + '→' + a
                return op == ra
        else:
            return op == m
    rx = rule.get('match_regex', '')
    if rx:
        try:
            return re.search(rx, op) is not None
        except re.error:
            return False
    return False

def _rule_applies_to_groups(rule: dict, rdg_groups: set[str]) -> bool:
    gs = set((rule.get('groups') or []) or [])
    ex = set((rule.get('exclude_groups') or []) or [])
    if gs and not (rdg_groups & gs):
        return False
    if ex and (rdg_groups & ex):
        return False
    return True

def classify_by_policy(op: str, policy: dict, rdg_groups: set[str] | None = None) -> str:
    """Return 'trivial' or 'meaningful' if a policy rule matches this atomic op under group context; else ''"""
    if not policy:
        return ''
    rdg_groups = rdg_groups or set()
    for r in policy.get('rules', []) or []:
        if _op_match_rule(op, r) and _rule_applies_to_groups(r, rdg_groups):
            lab = (r.get('label') or '').strip().lower()
            if lab in ('trivial', 'meaningful'):
                return lab
    return ''

def load_witness_groups(path: str|None) -> dict[str, set[str]]:
    """Load mapping from witness id (e.g., ms0005) to set of group names.

    YAML schema:
      groups:
        Iranian: [ms0005, ms0006]
        Indian: [ms0677]
    """
    mapping: dict[str, set[str]] = {}
    if not path:
        return mapping
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        groups = data.get('groups') or {}
        for gname, ids in groups.items():
            for wid in ids or []:
                mapping.setdefault(str(wid).strip(), set()).add(gname)
    except Exception:
        return {}
    return mapping

def _concise_diphthong_n(lem_text: str, rdg_text: str) -> str:
    """Return a concise lemma→reading n for common diphthong/pseudo-diphthong ops.

    Looks for minimal graphemic swaps within the first differing token pair.
    Examples returned: 'ō→aō', 'aē→ē', 'ai→aē', 'ōi→ō', 'ou→ōu'.
    """
    try:
        l_tokens = _split_tokens_compare_only(lem_text)
        r_tokens = _split_tokens_compare_only(rdg_text)
        # Find first differing token by comp_norm
        pairs = [(l, r) for l, r in zip(l_tokens, r_tokens) if comp_norm(l) != comp_norm(r)]
        if not pairs:
            return ''
        lt, rt = pairs[0]
        lt_n = nfc(lt)
        rt_n = nfc(rt)
        # Known diph/pseudo pairs to test in lemma→reading orientation
        pairs_lr = [
            ('ō', 'aō'), ('aō', 'ō'),
            ('ē', 'aē'), ('aē', 'ē'),
            ('ai', 'aē'), ('aē', 'ai'),
            ('ōi', 'ō'), ('ō', 'ōi'),
            ('ou', 'ōu'), ('ōu', 'ou'),
        ]
        for a, b in pairs_lr:
            if a in lt_n and b in rt_n:
                return f"{a}→{b}"
        # Fallback: if only one side has leading 'a' before a long vowel (aē/aō), report that
        if 'aē' in lt_n and 'ē' in rt_n:
            return 'aē→ē'
        if 'ē' in lt_n and 'aē' in rt_n:
            return 'ē→aē'
        if 'aō' in lt_n and 'ō' in rt_n:
            return 'aō→ō'
        if 'ō' in lt_n and 'aō' in rt_n:
            return 'ō→aō'
    except Exception:
        return ''
    return ''

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tei', required=True)
    parser.add_argument('--features', required=True, help='CSV path or comma-separated list of CSVs')
    parser.add_argument('--label-changes', required=False)
    parser.add_argument('--unknown-out', required=True)
    parser.add_argument('--overrides-features', required=False)
    parser.add_argument('--overrides-readings', required=False)
    parser.add_argument('--aggressive-infer', action='store_true')
    parser.add_argument('--orthography-families', required=False)
    parser.add_argument('--lexical-whitelist', required=False)
    parser.add_argument('--classification-policy', required=False, help='YAML with explicit per-feature label rules (directional/contextual)')
    parser.add_argument('--witness-groups', required=False, help='YAML mapping witness ids to manuscript groups/schools for group-aware policy rules')
    args = parser.parse_args()

    tei_dir = Path(args.tei)
    # Load one or more feature CSVs (comma-separated). Earlier files take precedence on duplicates.
    feature_paths = [p.strip() for p in str(args.features).split(',') if p.strip()]
    frames = []
    for fp in feature_paths:
        try:
            dfp = pd.read_csv(fp)
            if 'feature' not in dfp.columns:
                continue
            dfp['feature'] = dfp['feature'].astype(str)
            frames.append(dfp)
        except Exception:
            continue
    if not frames:
        raise SystemExit(f"Could not load any features from {args.features}")
    # Concatenate, keeping first occurrence of each feature
    combined = pd.concat(frames, ignore_index=True)
    combined = combined[~combined['feature'].duplicated(keep='first')]
    features_df = combined.set_index('feature')
    # Build catalog index for atomic lookup
    catalog_map, catalog_keys = build_feature_catalog(features_df)
    label_changes = load_label_changes(args.label_changes) if args.label_changes else set()

    unknowns = []
    feat_over, rdg_over = load_overrides(args.overrides_features, args.overrides_readings)
    families = compile_orthography_families(args.orthography_families)
    whitelist = load_whitelist(args.lexical_whitelist)
    policy = load_classification_policy(args.classification_policy) if args.classification_policy else {}
    wit_groups_map = load_witness_groups(args.witness_groups)

    def output_label_map(internal: str) -> str:
        # Map internal 'meaningful'/'trivial'/'missing' to TEI categories 'variants'/'readings'/'missing'
        if internal == 'meaningful':
            return 'variants'
        if internal == 'trivial':
            return 'readings'
        if internal == 'missing':
            return 'missing'
        return 'unknown'

    for tei_path in tei_dir.glob('*.xml'):
        # Skip already annotated outputs
        if str(tei_path).endswith('.v3.xml'):
            continue
        tree = etree.parse(str(tei_path))
        ensure_taxonomy(tree)
        root = tree.getroot()
        feature_index = set(features_df.index.tolist())
        for div in root.xpath('.//tei:div[@xml:id]', namespaces=NS):
            for app in div.xpath('.//tei:app[@xml:id]', namespaces=NS):
                app_id = app.get('{http://www.w3.org/XML/1998/namespace}id')
                lem_elem = app.find('./tei:lem', namespaces=NS)
                lem_text = ''.join(lem_elem.xpath('.//text()', namespaces=NS)) if lem_elem is not None else ''
                for rdg in app.xpath('./tei:rdg', namespaces=NS):
                    wit_list = rdg.get('wit', '')
                    rdg_text = ''.join(rdg.xpath('.//text()', namespaces=NS))
                    
                    # Early detection: if witness is missing this word entirely, classify as "missing"
                    if not rdg_text.strip():
                        rdg.set('resp', 'score-v3')
                        rdg.set('cert', '0.000')
                        rdg.set('ana', '#missing')
                        rdg.set('n', 'word missing')
                        continue
                    
                    # Determine group context for this reading
                    rdg_wits = [w.strip().lstrip('#') for w in wit_list.split() if w.strip()]
                    rdg_group_set: set[str] = set()
                    for wid in rdg_wits:
                        if wid in wit_groups_map:
                            rdg_group_set |= wit_groups_map[wid]
                    # Pre-compute helpers
                    punct_equal = _punct_norm_full(lem_text) == _punct_norm_full(rdg_text)
                    base_equal = to_base(nfc(lem_text)) == to_base(nfc(rdg_text))
                    token_base_equal = _punct_norm_tokens(lem_text) == _punct_norm_tokens(rdg_text)
                    lem_tok_list = _split_tokens_compare_only(lem_text)
                    rdg_tok_list = _split_tokens_compare_only(rdg_text)
                    token_comp_equal = [comp_norm(t) for t in lem_tok_list] == [comp_norm(t) for t in rdg_tok_list]
                    # Spacing-only equality: if equal after removing ALL whitespace (post punct-normalization)
                    import re as _re
                    lem_no_space = _re.sub(r"\s+", "", collapse_ws(strip_decopunct(nfc(lem_text))))
                    rdg_no_space = _re.sub(r"\s+", "", collapse_ws(strip_decopunct(nfc(rdg_text))))
                    spacing_only_equal = (lem_no_space == rdg_no_space) and (lem_text != rdg_text)
                    n_override = None
                    if spacing_only_equal:
                        lsc = len(_re.findall(r"\s", lem_text))
                        rsc = len(_re.findall(r"\s", rdg_text))
                        if rsc > lsc:
                            n_override = 'space inserted'
                        elif rsc < lsc:
                            n_override = 'space deleted'
                        else:
                            n_override = 'space moved'
                    # Family normalization on compare-only normalized text
                    lem_cmp = collapse_ws(strip_decopunct(nfc(lem_text)))
                    rdg_cmp = collapse_ws(strip_decopunct(nfc(rdg_text)))
                    lh, lname, lfam = family_normalize(lem_cmp, families)
                    rh, rname, rfam = family_normalize(rdg_cmp, families)
                    fam_name = rname or lname
                    family_equal = (lfam == rfam) and (lh or rh)

                    # Diff-derived feature and aggressive inference
                    feat_from_tokens = token_diff_feature(lem_text, rdg_text)
                    feature = feature_infer(lem_text, rdg_text, aggressive=args.aggressive_infer, index_set=feature_index)
                    feature_canon = feature.replace(' for ', '→')
                    frow = features_df.loc[feature_canon] if feature_canon in features_df.index else {}
                    vlik = frow.get('variant_likelihood', 0.5)
                    cert = round_cert(vlik)
                    # Apply overrides: reading-level first, then feature-level
                    ana_val = None
                    inference_rule = 'none'
                    allow_atomic_upgrade = False  # allow atomic analysis to upgrade some trivialities to meaningful
                    key = (app_id, norm_text(rdg_text))
                    if key in rdg_over:
                        ana_val = rdg_over[key]
                        inference_rule = 'override-reading'
                    elif feature_canon in feat_over:
                        ana_val = feat_over[feature_canon]
                        inference_rule = 'override-feature'
                    # Automatic trivial conditions
                    elif base_equal:
                        ana_val = 'trivial'
                        inference_rule = 'diacritic'
                    elif punct_equal:
                        ana_val = 'trivial'
                        inference_rule = 'punct'
                    elif spacing_only_equal:
                        ana_val = 'trivial'
                        inference_rule = 'space-only'
                    elif token_base_equal:
                        ana_val = 'trivial'
                        inference_rule = 'token-base-equal'
                    elif token_comp_equal:
                        ana_val = 'trivial'
                        inference_rule = 'token-comp-equal'
                    elif family_equal:
                        # Treat as orthography-driven trivial variant
                        ana_val = 'trivial'
                        inference_rule = f'family:{fam_name}'
                        # For certain broad orthographic families, do NOT allow atomic upgrade
                        # to avoid re-classifying as meaningful due to incidental 'h/u inserted' etc.
                        strict_family_context = False
                        try:
                            # Detect hallmark graphemes for strict families in either side
                            strict_markers = r"(ŋᵛh|ŋhu|ŋuh|ŋᵛ|x́|xᵛ)"
                            # Also treat diphthong clusters as strict: aō, ōi, aē, ae, ī, ē, ai, ōu, ou
                            diphthong_markers = r"(aōi|ōi|aō|ō|aē|ae|ī|ē|ai|ōu|ou)"
                            if re.search(strict_markers, lem_cmp) or re.search(strict_markers, rdg_cmp) \
                               or re.search(diphthong_markers, lem_cmp) or re.search(diphthong_markers, rdg_cmp):
                                strict_family_context = True
                        except Exception:
                            strict_family_context = False
                        allow_atomic_upgrade = not strict_family_context
                        # Prefer concise lemma→reading n when in strict diphthong/pseudo-diph context
                        if strict_family_context:
                            conc = _concise_diphthong_n(lem_text, rdg_text)
                            if conc:
                                n_override = conc
                    elif frow is not None and len(frow)!=0 and frow.get('orthography_match?', False):
                        ana_val = 'trivial'
                        inference_rule = 'catalog-orthography'
                        allow_atomic_upgrade = True
                    # Automatic meaningful conditions
                    if ana_val is None:
                        # whitelist insertions/deletions of ≥2 letters
                        ft = feat_from_tokens
                        if isinstance(ft, str) and (' inserted' in ft or ' deleted' in ft):
                            tok = ft.replace(' inserted','').replace(' deleted','').strip()
                            base_tok = to_base(tok)
                            if len(base_tok) >= 2 and tok in whitelist:
                                ana_val = 'meaningful'
                                inference_rule = 'whitelist-change'
                    if ana_val is None and frow is not None and len(frow)!=0:
                        if frow.get('label','') == 'variant' and not frow.get('punct_penalty_applied?', False) and vlik >= 0.75:
                            ana_val = 'meaningful'
                            inference_rule = 'catalog-variant-strong'
                    # Atomic decomposition path replaces whole-word 'subst'
                    atomic_used = False
                    atomic_ops: List[str] = []
                    if ana_val is None or allow_atomic_upgrade:
                        # If not already decided, or feature inferred as 'subst', try atomic mapping
                        if feature_canon == 'subst' or True:
                            atomic_ops = diff_tokens_to_atomic_features(lem_text, rdg_text)
                            
                            # Special case: detect ɱ ↔ hm orthographic pattern
                            # Pattern: "ɱ deleted; h inserted; m inserted" or reverse
                            ops_str = '; '.join(atomic_ops)
                            if ops_str in ['ɱ deleted; h inserted; m inserted', 'h deleted; m deleted; ɱ inserted']:
                                # This is the trivial ɱ ↔ hm orthographic alternation
                                ana_val = 'trivial'
                                cert = round_cert(0.85)
                                inference_rule = 'orthography:ɱ-hm'
                                # Don't run atomic analysis for this case
                                atomic_ops = []
                            
                            # Per-token family trivialization fast-lane
                            try:
                                lem_tok = _split_tokens_compare_only(lem_text)
                                rdg_tok = _split_tokens_compare_only(rdg_text)
                                token_pairs = [(l, r) for l, r in zip(lem_tok, rdg_tok) if comp_norm(l) != comp_norm(r)]

                                def _tokens_equal_under_families(l: str, r: str) -> bool:
                                    l_hit, _, lnorm = family_normalize(collapse_ws(strip_decopunct(nfc(l))), families)
                                    r_hit, _, rnorm = family_normalize(collapse_ws(strip_decopunct(nfc(r))), families)
                                    return (l_hit or r_hit) and (lnorm == rnorm)

                                if token_pairs and all(_tokens_equal_under_families(l, r) for l, r in token_pairs):
                                    ana_val = 'trivial'
                                    cert = round_cert(0.85)  # heuristic confidence for family-trivial
                                    inference_rule = 'family:token'
                            except Exception:
                                # Safety: never fail the annotator due to fast-lane
                                pass
                            if atomic_ops and (ana_val is None or allow_atomic_upgrade):
                                atomic_used = True
                                atomic_labels = []  # ('meaningful'/'trivial'/'' , vlik)
                                for op in atomic_ops:
                                    # trivial if equal after normalization or family
                                    lab = ''
                                    v = 0.5
                                    # policy-based override (directional/contextual rules)
                                    pol_lab = classify_by_policy(op, policy, rdg_group_set)
                                    if pol_lab:
                                        lab = pol_lab
                                    if '→' in op:
                                        a, b = op.split('→', 1)
                                        # diacritic/punct equality
                                        if comp_norm(a) == comp_norm(b):
                                            lab = 'trivial'
                                        else:
                                            # family equality
                                            ah, aname, anorm = family_normalize(a, families)
                                            bh, bname, bnorm = family_normalize(b, families)
                                            if (ah or bh) and anorm == bnorm:
                                                lab = 'trivial'
                                    # Lookup catalog
                                    if not lab:
                                        row, conf = lookup_feature_score(op, catalog_map, catalog_keys)
                                        has_row = (isinstance(row, dict) and bool(row)) or (hasattr(row, 'empty') and not row.empty)
                                        if has_row:
                                            rvlik = row.get('variant_likelihood', 0.5)
                                            rlab = row.get('label', '')
                                            rpunct = bool(row.get('punct_penalty_applied?', False))
                                            rdoc = int(row.get('doc_freq', 0) or 0)
                                            rortho = bool(row.get('orthography_match?', False))
                                            rwhite = bool(row.get('lexical_whitelist_applied?', False))
                                            # decide per-atomic label by v3-ish rules
                                            if rlab == 'variant' and rvlik >= 0.75 and not rpunct:
                                                lab = 'meaningful'
                                            elif rortho or rpunct or (rdoc >= 3 and rvlik < 0.72):
                                                lab = 'trivial'
                                            v = rvlik
                                    # Apply default non-trivial fallback if configured
                                    if not lab and policy.get('default_nontrivial_label') in ('trivial', 'meaningful'):
                                        lab = policy['default_nontrivial_label']
                                    atomic_labels.append((lab, v))

                                # Aggregate decision
                                def _aggregate(labels: list[tuple[str, float]]):
                                    any_mean = any(l == 'meaningful' for l, _ in labels)
                                    has_lab = any(bool(l) for l, _ in labels)
                                    all_triv = has_lab and all(l == 'trivial' for l, _ in labels if l)
                                    return any_mean, all_triv

                                any_meaningful, all_trivial = _aggregate(atomic_labels)
                                decided_here = False
                                if ana_val is None:
                                    if any_meaningful:
                                        ana_val = 'meaningful'
                                        mv = max(v for l, v in atomic_labels if l == 'meaningful')
                                        cert = round_cert(mv)
                                        inference_rule = 'atomic-meaningful'
                                        decided_here = True
                                    elif all_trivial and atomic_labels:
                                        ana_val = 'trivial'
                                        triv_vals = [v for l, v in atomic_labels if l == 'trivial']
                                        tv = min(triv_vals) if triv_vals else 0.5
                                        cert = round_cert(max(0.5, 1.0 - tv))
                                        inference_rule = 'atomic-trivial'
                                        decided_here = True
                                elif allow_atomic_upgrade and any_meaningful:
                                    # Upgrade previously trivial (catalog/family) to meaningful if any atomic op is meaningful
                                    ana_val = 'meaningful'
                                    mv = max(v for l, v in atomic_labels if l == 'meaningful')
                                    cert = round_cert(mv)
                                    inference_rule = 'atomic-upgrade-meaningful'
                                    decided_here = True

                                # Space-collapsed rescue to reduce 'mixed': if undecided or too many ops, retry without spaces
                                if not decided_here or len(atomic_ops) > 3:
                                    import re as _re
                                    lem_nospace = _re.sub(r"\s+", "", nfc(lem_text))
                                    rdg_nospace = _re.sub(r"\s+", "", nfc(rdg_text))
                                    atomic_ops_ns = diff_tokens_to_atomic_features(lem_nospace, rdg_nospace)
                                    # If equal after removing spaces, classify as spacing-only trivial
                                    if spacing_only_equal:
                                        ana_val = 'trivial'
                                        inference_rule = 'atomic-space-equal'
                                        atomic_ops = []
                                        decided_here = True
                                        if n_override is None:
                                            lsc2 = len(_re.findall(r"\s", lem_text))
                                            rsc2 = len(_re.findall(r"\s", rdg_text))
                                            if rsc2 > lsc2:
                                                n_override = 'space inserted'
                                            elif rsc2 < lsc2:
                                                n_override = 'space deleted'
                                            else:
                                                n_override = 'space moved'
                                    atomic_labels_ns = []
                                    for op in atomic_ops_ns:
                                        lab = ''
                                        v = 0.5
                                        pol_lab = classify_by_policy(op, policy, rdg_group_set)
                                        if pol_lab:
                                            lab = pol_lab
                                        if '→' in op:
                                            a, b = op.split('→', 1)
                                            if comp_norm(a) == comp_norm(b):
                                                lab = 'trivial'
                                            else:
                                                ah, aname, anorm = family_normalize(a, families)
                                                bh, bname, bnorm = family_normalize(b, families)
                                                if (ah or bh) and anorm == bnorm:
                                                    lab = 'trivial'
                                        if not lab:
                                            row, conf = lookup_feature_score(op, catalog_map, catalog_keys)
                                            has_row = (isinstance(row, dict) and bool(row)) or (hasattr(row, 'empty') and not row.empty)
                                            if has_row:
                                                rvlik = row.get('variant_likelihood', 0.5)
                                                rlab = row.get('label', '')
                                                rpunct = bool(row.get('punct_penalty_applied?', False))
                                                rdoc = int(row.get('doc_freq', 0) or 0)
                                                rortho = bool(row.get('orthography_match?', False))
                                                if rlab == 'variant' and rvlik >= 0.75 and not rpunct:
                                                    lab = 'meaningful'
                                                elif rortho or rpunct or (rdoc >= 3 and rvlik < 0.72):
                                                    lab = 'trivial'
                                                v = rvlik
                                        # Apply default non-trivial fallback if configured
                                        if not lab and policy.get('default_nontrivial_label') in ('trivial', 'meaningful'):
                                            lab = policy['default_nontrivial_label']
                                        atomic_labels_ns.append((lab, v))
                                    any_meaningful_ns, all_trivial_ns = _aggregate(atomic_labels_ns)
                                    # Prefer concise non-mixed result if nospace ops are few and not already decided as spacing-only
                                    if (not spacing_only_equal) and len(atomic_ops_ns) <= 3 and (any_meaningful_ns or all_trivial_ns):
                                        if any_meaningful_ns:
                                            ana_val = 'meaningful'
                                            mv = max(v for l, v in atomic_labels_ns if l == 'meaningful')
                                            cert = round_cert(mv)
                                            inference_rule = 'atomic-space-collapsed-meaningful'
                                        else:
                                            ana_val = 'trivial'
                                            triv_vals = [v for l, v in atomic_labels_ns if l == 'trivial']
                                            tv = min(triv_vals) if triv_vals else 0.5
                                            cert = round_cert(max(0.5, 1.0 - tv))
                                            inference_rule = 'atomic-space-collapsed-trivial'
                                        # Override atomic_ops to the nospace ones so n can be concise
                                        atomic_ops = atomic_ops_ns
                                        atomic_labels = atomic_labels_ns
                                        decided_here = True
                    if ana_val is None:
                        ana_val = classify(frow, label_changes) if frow is not None and len(frow)!=0 else 'unknown'
                    # Set n attribute based on overrides/atomics when used; else use single feature_canon
                    if n_override is not None:
                        n_val = n_override
                    elif atomic_used and atomic_ops:
                        subs = [op for op in atomic_ops if '→' in op]
                        insdel = [op for op in atomic_ops if op.endswith(' inserted') or op.endswith(' deleted')]
                        if len(atomic_ops) == 1:
                            n_val = atomic_ops[0]
                        elif len(subs) == 1 and not insdel:
                            n_val = subs[0]
                        elif len(insdel) == 1 and not subs:
                            n_val = insdel[0]
                        else:
                            # concise join up to 3
                            n_val = '; '.join(atomic_ops[:3]) if len(atomic_ops) <= 3 else 'mixed'
                    else:
                        n_val = feature_canon
                    # Map to output category names
                    out_lab = output_label_map(ana_val)
                    # Idempotency: update resp="score-v3" if present
                    if rdg.get('resp') == 'score-v3':
                        rdg.set('cert', cert)
                        rdg.set('ana', f'#{out_lab}')
                        rdg.set('n', n_val)
                    else:
                        rdg.set('resp', 'score-v3')
                        rdg.set('cert', cert)
                        rdg.set('ana', f'#{out_lab}')
                        rdg.set('n', n_val)
                    if ana_val == 'unknown':
                        unknowns.append({
                            'app_id': app_id,
                            'wit_list': wit_list,
                            'rdg_text': rdg_text,
                            'lem_text': lem_text,
                            'feature': feature_canon,
                            'variant_likelihood': vlik,
                            'reason': 'borderline/unstable or unmapped',
                            'inference_rule': inference_rule
                        })
        out_path = tei_path.with_suffix('.v3.xml')
        tree.write(str(out_path), encoding='utf-8', pretty_print=True)
    # Write unknowns
    if unknowns:
        unknown_df = pd.DataFrame(unknowns)
        unknown_df.to_csv(args.unknown_out, index=False)
    print(f"Done. Annotated TEI files written with .v3.xml suffix. Unknowns: {len(unknowns)}")

if __name__ == '__main__':
    main()
