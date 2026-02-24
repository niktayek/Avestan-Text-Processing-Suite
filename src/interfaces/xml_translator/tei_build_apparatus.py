import argparse
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from lxml import etree
import unicodedata
import difflib

NS_TEI = 'http://www.tei-c.org/ns/1.0'
NS_XML = 'http://www.w3.org/XML/1998/namespace'
NS = {'tei': NS_TEI, 'xml': NS_XML}


def _text_with_no_break_lb(el: etree._Element) -> str:
    NB = '§NB§'
    LB = '§LB§'
    parts: List[str] = []
    def rec(node: etree._Element):
        txt = node.text or ''
        if txt:
            parts.append(txt)
        for child in node:
            try:
                lname = etree.QName(child.tag).localname
            except Exception:
                lname = ''
            if lname == 'lb':
                br = (child.get('break') or child.get(f'{{{NS_XML}}}break') or '').lower()
                parts.append(NB if br == 'no' else LB)
            elif lname == 'note':
                pass
            elif lname == 'seg':
                rec(child)
            elif lname == 'app':
                rdgs = [c for c in child if etree.QName(c.tag).localname == 'rdg']
                chosen = None
                for r in rdgs:
                    if (r.get('type') or '').lower() == 'orig':
                        chosen = r
                        break
                if chosen is None:
                    for r in rdgs:
                        if (r.get('type') or '').lower() == 'mod':
                            chosen = r
                            break
                if chosen is None and rdgs:
                    chosen = rdgs[0]
                if chosen is not None:
                    rec(chosen)
            else:
                rec(child)
            tail = child.tail or ''
            if tail:
                parts.append(tail)
    rec(el)
    s = ''.join(parts)
    s = unicodedata.normalize('NFC', s)
    s = re.sub(r"\s*" + re.escape(NB) + r"\s*", "", s)
    s = re.sub(r"\s*" + re.escape(LB) + r"\s*", " ", s)
    return s

def nfc_text(el: etree._Element) -> str:
    return _text_with_no_break_lb(el)

def normalize_canonical_dots(text: str) -> str:
    text = re.sub(r'([a-zāēīōūąą̇ṇŋϑδγšṣśṣ̌žə̄ə̨ŋ́hᵛ]{1,2})\.([a-zāēīōūąą̇ṇŋϑδγšṣśṣ̌žə̄ə̨ŋ́hᵛ])', r'\1. \2', text)
    text = re.sub(r'(^|\s)([a-zāēīōūąą̇ṇŋϑδγšṣśṣ̌žə̄ə̨ŋ́hᵛ]{1,2})\.\s+(?=[a-zāēīōūąą̇ṇŋϑδγšṣśṣ̌žə̄ə̨ŋ́hᵛ])', r'\1\2.', text)
    return text

def normalize_token(token: str) -> str:
    return unicodedata.normalize('NFC', token.lstrip('.'))

def tokenize(text: str) -> List[str]:
    return [t for t in re.split(r'\s+', text) if t]

def normalized_sequence_matcher(lem_toks: List[str], wit_toks: List[str]) -> difflib.SequenceMatcher:
    lem_norm = [normalize_token(t) for t in lem_toks]
    wit_norm = [normalize_token(t) for t in wit_toks]
    return difflib.SequenceMatcher(None, lem_norm, wit_norm)

def _parser():
    return etree.XMLParser(recover=True, remove_blank_text=True, resolve_entities=False, load_dtd=False, no_network=True, huge_tree=True)

def gather_lemma_ab(lemma_path: Path, part_prefixes: List[str]) -> List[Tuple[str, str]]:
    tree = etree.parse(str(lemma_path), parser=_parser())
    ab_list: List[Tuple[str, str]] = []
    divs = tree.xpath('//tei:div[@xml:id]', namespaces=NS) or tree.xpath('//div[@xml:id]')
    for div in divs:
        div_id = div.get(f'{{{NS_XML}}}id', '')
        if not any(div_id.startswith(p) for p in part_prefixes):
            continue
        abs_nodes = div.xpath('.//tei:ab[@xml:id]', namespaces=NS) or div.xpath('.//ab[@xml:id]')
        for ab in abs_nodes:
            ab_id = ab.get(f'{{{NS_XML}}}id', '')
            keep = False
            if ab_id:
                for p in part_prefixes:
                    if ab_id.startswith(p):
                        keep = True
                        break
                if not keep and ab_id.lower().startswith('head') and any(p in ab_id for p in part_prefixes):
                    keep = True
            if not keep:
                continue
            text = nfc_text(ab).strip()
            text = normalize_canonical_dots(text)
            if ab_id and text:
                ab_list.append((ab_id, text))
    return ab_list

def _load_ab_id_remap(path: Optional[Path]) -> Dict[str, Dict[str, str]]:
    try:
        import yaml
        with open(str(path), 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        out: Dict[str, Dict[str, str]] = {}
        for wid, mp in (data.get('witnesses') or {}).items():
            out[str(wid).strip()] = {str(k): str(v) for k, v in (mp or {}).items()}
        return out
    except Exception:
        return {}

def load_witness_ab_texts(wit_path: Path, ab_ids: List[str], remap_for_witness: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    try:
        tree = etree.parse(str(wit_path), parser=_parser())
    except Exception:
        return {}
    result = {}
    for aid in ab_ids:
        lookup_id = remap_for_witness.get(aid, aid) if remap_for_witness else aid
        cand = tree.xpath(f".//*[@xml:id='{lookup_id}']", namespaces=NS)
        el = cand[0] if cand else None
        if el is None:
            cand = tree.xpath(f".//*[@id='{lookup_id}']")
            el = cand[0] if cand else None
        if el is None:
            cand = tree.xpath(f".//*[@n='{lookup_id}' or @corresp='{lookup_id}'][1]")
            el = cand[0] if cand else None
        if el is None:
            cand = tree.xpath(f"(.//tei:ab[contains(@xml:id, '{lookup_id}') or contains(@id, '{lookup_id}')] | .//ab[contains(@xml:id, '{lookup_id}') or contains(@id, '{lookup_id}')])[1]", namespaces=NS)
            el = cand[0] if cand else None
        if el is not None:
            txt = _text_with_no_break_lb(el).strip()
            txt = normalize_canonical_dots(txt)
            if txt:
                result[aid] = txt
    return result

def ms_id_from_filename(path: Path) -> str:
    stem = path.stem
    code = stem.zfill(4) if stem.isdigit() else re.sub(r'[^0-9A-Za-z]+', '', stem)[:16]
    return f"#ms{code}"

def differing_token_indices(lem_toks: List[str], wit_toks_map: Dict[str, List[str]]) -> List[int]:
    n = len(lem_toks)
    mask = [False] * n
    for wtoks in wit_toks_map.values():
        sm = normalized_sequence_matcher(lem_toks, wtoks)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                continue
            for i in range(i1, i2):
                if 0 <= i < n:
                    mask[i] = True
    return [i for i, v in enumerate(mask) if v]

def extract_reading_for_span(lem_toks: List[str], wit_toks: List[str], span: Tuple[int,int]) -> str:
    a, b = span
    sm = normalized_sequence_matcher(lem_toks, wit_toks)
    parts: List[str] = []
    one_token = (b == a + 1)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if i2 <= a or i1 >= b:
            continue
        if one_token:
            i = a
            if tag == 'equal':
                off = i - i1
                if 0 <= off < (i2 - i1) and (j1 + off) < j2:
                    parts.append(wit_toks[j1 + off])
            elif tag == 'replace':
                L_len = i2 - i1
                W_len = j2 - j1
                off = i - i1
                if L_len == W_len and W_len > 0:
                    parts.append(wit_toks[j1 + off])
                elif W_len == 1 and W_len > 0:
                    parts.append(wit_toks[j1])
                elif W_len > 1 and L_len > 0:
                    rel = off / L_len
                    w_index = j1 + int(rel * W_len)
                    if w_index >= j2:
                        w_index = j2 - 1
                    parts.append(wit_toks[w_index])
            elif tag == 'delete':
                pass
            break
        else:
            if tag == 'equal':
                ia = max(i1, a)
                ib = min(i2, b)
                off = ia - i1
                parts.extend(wit_toks[j1 + off: j1 + off + (ib - ia)])
            else:
                parts.extend(wit_toks[j1:j2])
    return ' '.join(parts).strip()

def build_witness_span_map(lem_toks: List[str], wit_toks: List[str]) -> Dict[Tuple[int, int], str]:
    sm = normalized_sequence_matcher(lem_toks, wit_toks)
    span_map: Dict[Tuple[int, int], str] = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        lemma_len = i2 - i1
        wit_len = j2 - j1
        if tag == 'equal':
            for li in range(i1, i2):
                span_map[(li, li+1)] = wit_toks[j1 + (li - i1)]
        elif tag == 'replace':
            if lemma_len > 1 and wit_len == 1:
                span_map[(i1, i2)] = wit_toks[j1]
            elif lemma_len == 1 and wit_len > 1:
                span_map[(i1, i2)] = ' '.join(wit_toks[j1:j2])
            else:
                L = min(lemma_len, wit_len)
                for k in range(L):
                    span_map[(i1 + k, i1 + k + 1)] = wit_toks[j1 + k]
                for k in range(L, lemma_len):
                    span_map[(i1 + k, i1 + k + 1)] = ''
        elif tag == 'delete':
            for li in range(i1, i2):
                span_map[(li, li+1)] = ''
        elif tag == 'insert':
            continue
    return span_map

def build_witness_span_map_greedy(lem_toks: List[str], wit_toks: List[str], max_run: int = 4, thresh: float = 0.75) -> Dict[Tuple[int,int], str]:
    """Greedy left-to-right alignment producing span -> reading mapping.

    Handles:
      - Compounds: one witness token covers multiple lemma tokens
      - Splits: multiple witness tokens cover one lemma token
    Uses normalized token concatenations and similarity threshold.
    """
    def norm(t: str) -> str:
        t = unicodedata.normalize('NFC', t)
        t = t.replace(' ', '')
        t = re.sub(r'[\.,;:·⸳]', '', t)
        return t.lower()
    span_map: Dict[Tuple[int,int], str] = {}
    i = 0
    j = 0
    while i < len(lem_toks) and j < len(wit_toks):
        lem_norm = norm(lem_toks[i])
        wit_norm = norm(wit_toks[j])
        # Try compound (witness token vs multiple lemma tokens)
        best_m = 0
        for m in range(2, min(max_run, len(lem_toks) - i) + 1):
            lem_concat = norm(''.join(lem_toks[i:i+m]))
            score = difflib.SequenceMatcher(None, wit_norm, lem_concat).ratio()
            if score >= thresh:
                best_m = m
        if best_m:
            span_map[(i, i+best_m)] = wit_toks[j]
            i += best_m
            j += 1
            continue
        # Try split (lemma token vs multiple witness tokens)
        best_k = 0
        for k in range(2, min(max_run, len(wit_toks) - j) + 1):
            wit_concat = norm(''.join(wit_toks[j:j+k]))
            score = difflib.SequenceMatcher(None, lem_norm, wit_concat).ratio()
            if score >= thresh:
                best_k = k
        if best_k:
            span_map[(i, i+1)] = ' '.join(wit_toks[j:j+best_k])
            i += 1
            j += best_k
            continue
        # One-to-one if similar enough
        if difflib.SequenceMatcher(None, lem_norm, wit_norm).ratio() >= 0.5:
            span_map[(i, i+1)] = wit_toks[j]
            i += 1
            j += 1
            continue
        # Fallback: treat as differing but still consume both
        span_map[(i, i+1)] = wit_toks[j]
        i += 1
        j += 1
    # Remaining lemma tokens with no witness coverage
    while i < len(lem_toks):
        span_map[(i, i+1)] = ''
        i += 1
    return span_map

def dp_align_span_map(lem_toks: List[str], wit_toks: List[str], max_run: int = 4) -> Dict[Tuple[int,int], str]:
    """(Legacy) Return simple span surface mapping without index metadata."""
    def norm(t: str) -> str:
        t = unicodedata.normalize('NFC', t)
        t = t.replace(' ', '')
        t = re.sub(r'[\.,;:·⸳]', '', t)
        return t.lower()

    n = len(lem_toks)
    m = len(wit_toks)
    # DP table: score[i][j] best score aligning first i lemma tokens and first j witness tokens
    score = [[None]*(m+1) for _ in range(n+1)]
    back: Dict[Tuple[int,int], Tuple[str, int, int, int, int]] = {}
    score[0][0] = 0.0

    # Penalties
    DEL_PEN = -0.6
    INS_PEN = -0.6
    BASE_MATCH_MIN = 0.10  # minimal score for weak matches to avoid excessive deletions

    for i in range(n+1):
        for j in range(m+1):
            if score[i][j] is None:
                continue
            cur = score[i][j]
            # 1-1 match/substitute
            if i < n and j < m:
                sim = difflib.SequenceMatcher(None, norm(lem_toks[i]), norm(wit_toks[j])).ratio()
                sim = max(sim, BASE_MATCH_MIN) if sim > 0 else 0.0
                nxt = cur + sim
                if score[i+1][j+1] is None or nxt > score[i+1][j+1]:
                    score[i+1][j+1] = nxt
                    back[(i+1,j+1)] = ('match', i, j, i+1, j+1)
            # Merge (k lemma → 1 witness)
            if j < m:
                for k in range(2, max_run+1):
                    if i + k > n:
                        break
                    lem_concat = ''.join(lem_toks[i:i+k])
                    sim = difflib.SequenceMatcher(None, norm(lem_concat), norm(wit_toks[j])).ratio()
                    if sim < 0.5:
                        continue
                    # Slight bonus for larger successful merges to encourage single apparatus entry
                    sim += 0.05 * (k-1)
                    nxt = cur + sim
                    if score[i+k][j+1] is None or nxt > score[i+k][j+1]:
                        score[i+k][j+1] = nxt
                        back[(i+k,j+1)] = ('merge', i, j, i+k, j+1)
            # Split (1 lemma → k witness)
            if i < n:
                for k in range(2, max_run+1):
                    if j + k > m:
                        break
                    wit_concat = ''.join(wit_toks[j:j+k])
                    sim = difflib.SequenceMatcher(None, norm(lem_toks[i]), norm(wit_concat)).ratio()
                    if sim < 0.5:
                        continue
                    sim += 0.05 * (k-1)
                    nxt = cur + sim
                    if score[i+1][j+k] is None or nxt > score[i+1][j+k]:
                        score[i+1][j+k] = nxt
                        back[(i+1,j+k)] = ('split', i, j, i+1, j+k)
            # Delete lemma token
            if i < n:
                nxt = cur + DEL_PEN
                if score[i+1][j] is None or nxt > score[i+1][j]:
                    score[i+1][j] = nxt
                    back[(i+1,j)] = ('delete', i, j, i+1, j)
            # Insert witness token
            if j < m:
                nxt = cur + INS_PEN
                if score[i][j+1] is None or nxt > score[i][j+1]:
                    score[i][j+1] = nxt
                    back[(i,j+1)] = ('insert', i, j, i, j+1)

    # Backtrace
    span_map: Dict[Tuple[int,int], str] = {}
    i, j = n, m
    while (i, j) != (0, 0):
        if (i, j) not in back:
            # Fallback: break to avoid infinite loop
            break
        op, pi, pj, ni, nj = back[(i, j)]  # ni,nj should equal current i,j
        assert (ni, nj) == (i, j)
        if op == 'match':
            span_map[(pi, pi+1)] = wit_toks[pj]
        elif op == 'merge':
            # k lemma tokens to single witness token
            span_map[(pi, ni)] = wit_toks[pj]
        elif op == 'split':
            # single lemma token to multiple witness tokens
            span_map[(pi, pi+1)] = ' '.join(wit_toks[pj:nj])
        elif op == 'delete':
            span_map[(pi, pi+1)] = ''
        elif op == 'insert':
            # insertion unanchored to lemma token; ignore for span_map
            pass
        i, j = pi, pj

    return span_map

def dp_align_struct(lem_toks: List[str], wit_toks: List[str], max_run: int = 4):
    """Structured DP alignment.

    Returns:
      span_surface: (lemma_start, lemma_end) -> surface string assembled strictly
        from witness token indices aligned to lemma tokens within that span.
      lemma_to_witness: lemma_index -> list of witness token indices (empty list if deletion).
      witness_tokens: original witness tokens list reference.
      op_records: list of (op, lemma_start, lemma_end, wit_start, wit_end)
    """
    def norm(t: str) -> str:
        t = unicodedata.normalize('NFC', t)
        t = t.replace(' ', '')
        t = re.sub(r'[\.,;:·⸳]', '', t)
        return t.lower()

    n = len(lem_toks)
    m = len(wit_toks)
    score = [[None]*(m+1) for _ in range(n+1)]
    back: Dict[Tuple[int,int], Tuple[str,int,int,int,int]] = {}
    score[0][0] = 0.0
    DEL_PEN = -0.6
    INS_PEN = -0.6
    BASE_MATCH_MIN = 0.10

    for i in range(n+1):
        for j in range(m+1):
            if score[i][j] is None:
                continue
            cur = score[i][j]
            if i < n and j < m:
                sim = difflib.SequenceMatcher(None, norm(lem_toks[i]), norm(wit_toks[j])).ratio()
                sim = max(sim, BASE_MATCH_MIN) if sim > 0 else 0.0
                nxt = cur + sim
                if score[i+1][j+1] is None or nxt > score[i+1][j+1]:
                    score[i+1][j+1] = nxt
                    back[(i+1,j+1)] = ('match', i, j, i+1, j+1)
            if j < m:
                for k in range(2, max_run+1):
                    if i + k > n:
                        break
                    lem_concat = ''.join(lem_toks[i:i+k])
                    sim = difflib.SequenceMatcher(None, norm(lem_concat), norm(wit_toks[j])).ratio()
                    if sim < 0.5:
                        continue
                    sim += 0.05 * (k-1)
                    nxt = cur + sim
                    if score[i+k][j+1] is None or nxt > score[i+k][j+1]:
                        score[i+k][j+1] = nxt
                        back[(i+k,j+1)] = ('merge', i, j, i+k, j+1)
            if i < n:
                for k in range(2, max_run+1):
                    if j + k > m:
                        break
                    wit_concat = ''.join(wit_toks[j:j+k])
                    sim = difflib.SequenceMatcher(None, norm(lem_toks[i]), norm(wit_concat)).ratio()
                    if sim < 0.5:
                        continue
                    sim += 0.05 * (k-1)
                    nxt = cur + sim
                    if score[i+1][j+k] is None or nxt > score[i+1][j+k]:
                        score[i+1][j+k] = nxt
                        back[(i+1,j+k)] = ('split', i, j, i+1, j+k)
            if i < n:
                nxt = cur + DEL_PEN
                if score[i+1][j] is None or nxt > score[i+1][j]:
                    score[i+1][j] = nxt
                    back[(i+1,j)] = ('delete', i, j, i+1, j)
            if j < m:
                nxt = cur + INS_PEN
                if score[i][j+1] is None or nxt > score[i][j+1]:
                    score[i][j+1] = nxt
                    back[(i,j+1)] = ('insert', i, j, i, j+1)

    i, j = n, m
    lemma_to_witness: Dict[int, List[int]] = {idx: [] for idx in range(n)}
    op_records: List[Tuple[str,int,int,int,int]] = []
    while (i, j) != (0, 0):
        if (i, j) not in back:
            break
        op, pi, pj, ni, nj = back[(i, j)]
        if op == 'match':
            lemma_to_witness[pi].append(pj)
            op_records.append((op, pi, pi+1, pj, pj+1))
        elif op == 'merge':
            for li in range(pi, ni):
                lemma_to_witness[li].append(pj)
            op_records.append((op, pi, ni, pj, pj+1))
        elif op == 'split':
            for wi in range(pj, nj):
                lemma_to_witness[pi].append(wi)
            op_records.append((op, pi, pi+1, pj, nj))
        elif op == 'delete':
            op_records.append((op, pi, pi+1, pj, pj))
        elif op == 'insert':
            # insertion not tied to lemma tokens
            op_records.append((op, pi, pi, pj, pj+1))
        i, j = pi, pj

    # Build span surfaces strictly from witness index sets
    span_surface: Dict[Tuple[int,int], str] = {}
    # Collect contiguous lemma ranges where any operation spans >1 lemma tokens (merge) or single lemma token has >1 witness indices (split)
    for op, ls, le, ws, we in op_records:
        if op == 'merge':
            span_surface[(ls, le)] = wit_toks[ws]
        elif op == 'split':
            span_surface[(ls, le)] = ' '.join(wit_toks[ws:we])
        elif op == 'match':
            span_surface[(ls, le)] = wit_toks[ws]
        elif op == 'delete':
            span_surface[(ls, le)] = ''
    # Ensure single-token matches present
    for li in range(n):
        if (li, li+1) not in span_surface:
            w_idxs = sorted(set(lemma_to_witness.get(li, [])))
            if not w_idxs:
                span_surface[(li, li+1)] = ''
            else:
                span_surface[(li, li+1)] = ' '.join(wit_toks[w] for w in w_idxs)

    return span_surface, lemma_to_witness, wit_toks, op_records

def ensure_header(root: etree._Element, title: str):
    header = etree.SubElement(root, f'{{{NS_TEI}}}teiHeader')
    fileDesc = etree.SubElement(header, f'{{{NS_TEI}}}fileDesc')
    titleStmt = etree.SubElement(fileDesc, f'{{{NS_TEI}}}titleStmt')
    etree.SubElement(titleStmt, f'{{{NS_TEI}}}title').text = title
    pubStmt = etree.SubElement(fileDesc, f'{{{NS_TEI}}}publicationStmt')
    etree.SubElement(pubStmt, f'{{{NS_TEI}}}p').text = 'Generated automatically from selected witnesses'
    sourceDesc = etree.SubElement(fileDesc, f'{{{NS_TEI}}}sourceDesc')
    etree.SubElement(sourceDesc, f'{{{NS_TEI}}}p').text = 'Lemma: Yasna_Static.xml; Witnesses: user-provided TEI files'
    enc = etree.SubElement(header, f'{{{NS_TEI}}}encodingDesc')
    tax = etree.SubElement(enc, f'{{{NS_TEI}}}taxonomy')
    tax.set(f'{{{NS_XML}}}id', 'varClass')
    for cat in ['meaningful', 'trivial', 'unknown']:
        c = etree.SubElement(tax, f'{{{NS_TEI}}}category')
        c.set(f'{{{NS_XML}}}id', cat)
        c.text = cat.capitalize()

def build_apparatus(lemma_path: Path, parts: List[str], witness_paths: List[Path], out_path: Path, per_ms_rdg: bool = False, per_word_apps: bool = False):
    ab_list = gather_lemma_ab(lemma_path, parts)
    print(f"[debug] gathered {len(ab_list)} ab segments for parts {parts}")
    if any((p or '').upper().startswith('Y9') for p in parts):
        if not per_ms_rdg:
            per_ms_rdg = True
        if not per_word_apps:
            per_word_apps = True
    ab_ids = [aid for aid, _ in ab_list]
    remap_path = Path('res/Yasna/meta/ab_id_remap.yaml')
    ab_remap_all = _load_ab_id_remap(remap_path) if remap_path.exists() else {}
    witnesses_by_ab: Dict[str, Dict[str, str]] = {aid: {} for aid in ab_ids}
    ms_ids: Dict[Path, str] = {wp: ms_id_from_filename(wp) for wp in witness_paths}
    ms_list = sorted(ms_ids.values())
    for wp in witness_paths:
        ms_code = ms_ids[wp].lstrip('#')
        wt_map = load_witness_ab_texts(wp, ab_ids, remap_for_witness=ab_remap_all.get(ms_code))
        ms_id = ms_ids[wp]
        for aid, txt in wt_map.items():
            witnesses_by_ab[aid][ms_id] = txt

    root = etree.Element(f'{{{NS_TEI}}}TEI', nsmap={None: NS_TEI, 'xml': NS_XML})
    ensure_header(root, f"Yasna {'+'.join(parts)} — apparatus (selected witnesses)")
    text = etree.SubElement(root, f'{{{NS_TEI}}}text')
    body = etree.SubElement(text, f'{{{NS_TEI}}}body')
    div = etree.SubElement(body, f'{{{NS_TEI}}}div')
    div.set(f'{{{NS_XML}}}id', f"apparatus_{'_'.join(parts)}")

    apps_created = 0
    for aid, lem_text in ab_list:
        wit_txts = witnesses_by_ab.get(aid, {})
        if not wit_txts:
            print(f"[debug] skipping ab {aid} (no witness text)")
        if not wit_txts:
            continue
        lem_toks = tokenize(lem_text)
        wit_toks_map = {ms: tokenize(txt) for ms, txt in wit_txts.items()}
        # Structured alignment per witness
        witness_span_maps: Dict[str, Dict[Tuple[int,int], str]] = {}
        witness_lemma_maps: Dict[str, Dict[int, List[int]]] = {}
        witness_ops: Dict[str, List[Tuple[str,int,int,int,int]]] = {}
        for ms, wtoks in wit_toks_map.items():
            span_surface, lemma_to_witness, wt_list, ops_rec = dp_align_struct(lem_toks, wtoks)
            witness_span_maps[ms] = span_surface
            witness_lemma_maps[ms] = lemma_to_witness
            witness_ops[ms] = ops_rec
        spans_set = set()
        differing_idxs = set(differing_token_indices(lem_toks, wit_toks_map))
        for ms, span_map in witness_span_maps.items():
            for (s, e), reading in span_map.items():
                # True merge if multiple lemma tokens map to single witness token index across all those lemma tokens.
                if (e - s) > 1:
                    # verify at least one witness merge or split op covers this span strictly
                    lemma_token_sets = [set(witness_lemma_maps[ms].get(li, [])) for li in range(s, e)]
                    union = set().union(*lemma_token_sets)
                    # merge: all lemma tokens share the same single witness index
                    is_merge = len(union) == 1 and all(lemma_token_sets[0] == st for st in lemma_token_sets)
                    # split chain: at least one lemma token maps to >1 witness indices
                    is_split_chain = any(len(st) > 1 for st in lemma_token_sets)
                    if is_merge or is_split_chain:
                        spans_set.add((s, e))
                else:
                    if s in differing_idxs or (' ' in reading.strip()):
                        spans_set.add((s, e))
        multi_spans = [sp for sp in spans_set if (sp[1] - sp[0]) > 1]
        suppressed = set()
        for (a, b) in multi_spans:
            for i in range(a, b):
                suppressed.add((i, i+1))
        filtered_spans: List[Tuple[int,int]] = []
        for sp in sorted(spans_set):
            if (sp[1] - sp[0]) == 1 and sp in suppressed:
                continue
            filtered_spans.append(sp)
        # Fallback: if no spans selected, default to per-token spans
        if not filtered_spans:
            filtered_spans = [(i, i+1) for i in range(len(lem_toks))]

        for (a, b) in filtered_spans:
            app = etree.SubElement(div, f'{{{NS_TEI}}}app')
            app.set(f'{{{NS_XML}}}id', f"app-{aid}-{a}-{b}")
            lem_el = etree.SubElement(app, f'{{{NS_TEI}}}lem')
            lem_el.text = ' '.join(lem_toks[a:b])
            if per_ms_rdg:
                for ms in ms_list:
                    # Boundary-enforcing: collect witness indices strictly from lemma tokens [a, b)
                    # Ignore witness indices aligned to lemma tokens outside this span
                    if ms not in witness_lemma_maps:
                        # Witness missing alignment for this ab
                        rdg = etree.SubElement(app, f'{{{NS_TEI}}}rdg')
                        rdg.set('wit', ms)
                        rdg.text = ''
                        continue
                    witness_indices_set = set()
                    for li in range(a, b):
                        for wi in witness_lemma_maps[ms].get(li, []):
                            witness_indices_set.add(wi)
                    # Build contiguous reading: sort indices and ensure no gaps from previous/next lemma alignment
                    # To prevent spillover, clip to the minimal contiguous block
                    if witness_indices_set:
                        witness_indices_sorted = sorted(witness_indices_set)
                        # Take only contiguous block from min to max (filling gaps)
                        # BUT: verify no index belongs to adjacent lemma alignment ops outside [a,b)
                        # Simplest approach: use ONLY the indices directly mapped to [a,b)
                        witness_indices = witness_indices_sorted
                    else:
                        witness_indices = []
                    wtoks_full = wit_toks_map.get(ms, [])
                    rdg_txt = ' '.join(wtoks_full[wi] for wi in witness_indices if 0 <= wi < len(wtoks_full)) if witness_indices else ''
                    rdg = etree.SubElement(app, f'{{{NS_TEI}}}rdg')
                    rdg.set('wit', ms)
                    rdg.text = rdg_txt
            else:
                surf_to_wits: Dict[str, List[str]] = defaultdict(list)
                for ms in ms_list:
                    if ms not in witness_lemma_maps:
                        surf_to_wits[''].append(ms)
                        continue
                    witness_indices_set = set()
                    for li in range(a, b):
                        for wi in witness_lemma_maps[ms].get(li, []):
                            witness_indices_set.add(wi)
                    if witness_indices_set:
                        witness_indices = sorted(witness_indices_set)
                    else:
                        witness_indices = []
                    wtoks_full = wit_toks_map.get(ms, [])
                    rdg_txt = ' '.join(wtoks_full[wi] for wi in witness_indices if 0 <= wi < len(wtoks_full)) if witness_indices else ''
                    surf_to_wits[rdg_txt or ''].append(ms)
                for surf, wit_list in surf_to_wits.items():
                    rdg = etree.SubElement(app, f'{{{NS_TEI}}}rdg')
                    rdg.set('wit', ' '.join(sorted(wit_list)))
                    rdg.text = surf
            apps_created += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    etree.ElementTree(root).write(str(out_path), encoding='utf-8', pretty_print=True, xml_declaration=True)
    print(f"Built apparatus with {apps_created} app entries for parts {parts} into {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lemma', default='data/Yasna_Static.xml')
    ap.add_argument('--parts', required=True)
    ap.add_argument('--witness-files', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--per-ms-rdg', dest='per_ms_rdg', action='store_true')
    ap.add_argument('--no-per-ms-rdg', dest='per_ms_rdg', action='store_false')
    ap.set_defaults(per_ms_rdg=True)
    ap.add_argument('--per-word-apps', dest='per_word_apps', action='store_true')
    ap.add_argument('--no-per-word-apps', dest='per_word_apps', action='store_false')
    ap.set_defaults(per_word_apps=True)
    args = ap.parse_args()
    parts = [p.strip() for p in args.parts.split(',') if p.strip()]
    witnesses = [Path(p.strip()) for p in args.witness_files.split(',') if p.strip()]
    build_apparatus(Path(args.lemma), parts, witnesses, Path(args.out), per_ms_rdg=bool(args.per_ms_rdg), per_word_apps=bool(args.per_word_apps))

if __name__ == '__main__':
    main()
