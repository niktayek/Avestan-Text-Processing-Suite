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
    """Extract descendant text while honoring <lb break="no"/> as zero-width join and selecting one reading from inline <app>.

    Strategy: walk the subtree; whenever an <lb> with @break='no' is encountered, inject a
    special marker, then strip any whitespace around it. For plain <lb/> (without @break),
    collapse to a single space to prevent spurious tokenization from newlines.
    For inline <app> elements (critical apparatus), select one <rdg> (prefer type="orig" or first).
    """
    NB = '§NB§'
    LB = '§LB§'
    parts: List[str] = []

    def rec(node: etree._Element):
        txt = node.text or ''
        if txt:
            parts.append(txt)
        for child in node:
            # Identify TEI element name regardless of namespace
            try:
                lname = etree.QName(child.tag).localname
            except Exception:
                lname = ''
            if lname == 'lb':
                br = (child.get('break') or child.get(f'{{{NS_XML}}}break') or '').lower()
                if br == 'no':
                    parts.append(NB)
                else:
                    # Plain <lb/> → single space marker
                    parts.append(LB)
            elif lname == 'note':
                # Skip <note> elements (Pahlavi/Persian instructions)
                pass
            elif lname == 'seg':
                # Handle <seg> elements: recurse to collect text from ALL segments
                rec(child)
            elif lname == 'app':
                # Inline apparatus: select one <rdg> child
                # Prefer <rdg type="orig">, else <rdg type="mod">, else first <rdg>
                rdgs = [c for c in child if etree.QName(c.tag).localname == 'rdg']
                chosen = None
                for r in rdgs:
                    rtype = (r.get('type') or '').lower()
                    if rtype == 'orig':
                        chosen = r
                        break
                if chosen is None:
                    for r in rdgs:
                        rtype = (r.get('type') or '').lower()
                        if rtype == 'mod':
                            chosen = r
                            break
                if chosen is None and rdgs:
                    chosen = rdgs[0]
                if chosen is not None:
                    # Recurse into chosen reading - this will handle <seg> elements within it
                    rec(chosen)
            else:
                # Recurse into child normally
                rec(child)
            tail = child.tail or ''
            if tail:
                parts.append(tail)

    rec(el)
    s = ''.join(parts)
    s = unicodedata.normalize('NFC', s)
    # Remove any whitespace around NB markers and then drop the marker (zero-width join)
    s = re.sub(r"\s*" + re.escape(NB) + r"\s*", "", s)
    # Replace LB markers (and surrounding whitespace) with a single space
    s = re.sub(r"\s*" + re.escape(LB) + r"\s*", " ", s)
    return s


def nfc_text(el: etree._Element) -> str:
    # extract all descendant text (respecting lb@break='no')
    return _text_with_no_break_lb(el)


def normalize_canonical_dots(text: str) -> str:
    """Normalize dot-spacing by removing space after short morphemes.
    
    Removes space after dot ONLY when:
    1. At word boundary (space or start of string before the morpheme)
    2. The ENTIRE word before the dot is very short (1-2 characters)
    3. Followed by a lowercase letter
    
    This merges 'ā. mąm.' → 'ā.mąm.' but keeps 'frā. mąm.' and 'kasə.ϑβąm. bitiiō.' as separate tokens.
    
    Also splits merged short morphemes like 'kasə.ϑβąm.' → 'kasə. ϑβąm.' to ensure consistent tokenization.
    """
    # First, split any merged short morphemes (e.g., kasə.ϑβąm. → kasə. ϑβąm.)
    # Pattern: (1-2 char morpheme)(dot)(lowercase letter) where there's no space after the dot
    # Add space after the dot to split them
    text = re.sub(r'([a-zāēīōūąą̇ṇŋϑδγšṣśṣ̌žə̄ə̨ŋ́hᵛ]{1,2})\.([a-zāēīōūąą̇ṇŋϑδγšṣśṣ̌žə̄ə̨ŋ́hᵛ])', r'\1. \2', text)
    
    # Then, merge short morphemes that are separated by space
    # Pattern: (space or start)(short word 1-2 chars)(dot)(space)(lowercase)
    # Use (?:^|\s) to match word boundary (start of string or space)
    # Capture the preceding space/boundary in group 1 to preserve it
    text = re.sub(r'(^|\s)([a-zāēīōūąą̇ṇŋϑδγšṣśṣ̌žə̄ə̨ŋ́hᵛ]{1,2})\.\s+(?=[a-zāēīōūąą̇ṇŋϑδγšṣśṣ̌žə̄ə̨ŋ́hᵛ])', r'\1\2.', text)
    
    return text


def normalize_token(token: str) -> str:
    """Normalize a single token for comparison.
    
    Removes leading dots and normalizes Unicode to handle variants like:
    'ā.', '.ā.', 'ā', etc. as equivalent
    Also handles '.mąm.' vs 'mąm.' differences.
    """
    # Remove leading dots
    token = token.lstrip('.')
    # Normalize Unicode
    return unicodedata.normalize('NFC', token)


def tokenize(text: str) -> List[str]:
    # Split on whitespace to get initial tokens
    # Punctuation-preserving: keep dots attached to preserve 'ā.' as token
    return [t for t in re.split(r'\s+', text) if t]


def normalized_sequence_matcher(lem_toks: List[str], wit_toks: List[str]) -> difflib.SequenceMatcher:
    """Create SequenceMatcher with normalized tokens for comparison.
    
    Normalizes tokens to handle 'ā.' vs '.ā.' or 'mąm.' vs '.mąm.' differences.
    """
    lem_norm = [normalize_token(t) for t in lem_toks]
    wit_norm = [normalize_token(t) for t in wit_toks]
    return difflib.SequenceMatcher(None, lem_norm, wit_norm)


def _parser():
    return etree.XMLParser(recover=True, remove_blank_text=True, resolve_entities=False, load_dtd=False, no_network=True, huge_tree=True)


def gather_lemma_ab(lemma_path: Path, part_prefixes: List[str]) -> List[Tuple[str, str]]:
    """Return list of (ab_id, text) for all ab under divs whose xml:id starts with any given prefix (e.g., 'Y9')."""
    tree = etree.parse(str(lemma_path), parser=_parser())
    ab_list: List[Tuple[str, str]] = []
    # Try namespaced TEI first
    divs = tree.xpath('//tei:div[@xml:id]', namespaces=NS)
    if not divs:
        # Fallback to no-namespace TEI
        divs = tree.xpath("//div[@xml:id]")
    for div in divs:
        div_id = div.get(f'{{{NS_XML}}}id', '')
        if not any(div_id.startswith(p) for p in part_prefixes):
            continue
        # Collect ab children in document order (ns or no-ns)
        abs_nodes = div.xpath('.//tei:ab[@xml:id]', namespaces=NS)
        if not abs_nodes:
            abs_nodes = div.xpath('.//ab[@xml:id]')
        for ab in abs_nodes:
            ab_id = ab.get(f'{{{NS_XML}}}id', '')
            # Filter ABs: only keep those that belong to the requested parts, e.g., Y9.*
            # Allow a small set of known local headers like 'Head9'.
            keep = False
            if ab_id:
                for p in part_prefixes:
                    if ab_id.startswith(p):  # e.g., Y9, Y9.1a, Y9.2
                        keep = True
                        break
                if not keep and ab_id.lower().startswith('head'):
                    # e.g., Head9 within the Y9 section
                    keep = any(p in ab_id for p in part_prefixes)
            if not keep:
                continue
            text = nfc_text(ab).strip()
            # Normalize canonical dot-spacing to match witness conventions
            text = normalize_canonical_dots(text)
            if ab_id and text:
                ab_list.append((ab_id, text))
    return ab_list



def _load_ab_id_remap(path: Optional[Path]) -> Dict[str, Dict[str, str]]:
    """Load optional per-witness AB id remapping from YAML.

    YAML schema:
      witnesses:
        ms0400:
          Y9.11c: Y9.11d
          Y9.11d: Y9.11e
    """
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
    """Map ab_id -> witness text using @xml:id lookup; skip missing."""
    try:
        tree = etree.parse(str(wit_path), parser=_parser())
    except Exception:
        return {}
    result = {}
    for aid in ab_ids:
        lookup_id = remap_for_witness.get(aid, aid) if remap_for_witness else aid
        el = None
        # Exact match on xml:id (with proper namespace mapping)
        cand = tree.xpath(f".//*[@xml:id='{lookup_id}']", namespaces=NS)
        el = cand[0] if cand else None
        if el is None:
            # Exact match on plain @id
            cand = tree.xpath(f".//*[@id='{lookup_id}']")
            el = cand[0] if cand else None
        if el is None:
            # Try exact match on @n or @corresp (common in some CAB files)
            cand = tree.xpath(f".//*[@n='{lookup_id}' or @corresp='{lookup_id}'][1]")
            el = cand[0] if cand else None
        if el is None:
            # Conservative contains on @xml:id or @id but RESTRICTED to ab elements only
            cand = tree.xpath(f"(.//tei:ab[contains(@xml:id, '{lookup_id}') or contains(@id, '{lookup_id}')] | .//ab[contains(@xml:id, '{lookup_id}') or contains(@id, '{lookup_id}')])[1]", namespaces=NS)
            el = cand[0] if cand else None
        if el is not None:
            txt = _text_with_no_break_lb(el).strip()
            # Normalize witness dot-spacing to match canonical conventions
            txt = normalize_canonical_dots(txt)
            if txt:
                result[aid] = txt
    return result


def ms_id_from_filename(path: Path) -> str:
    stem = path.stem
    # Use numeric stem as ms code; prefix with ms and zero-pad to 4 if numeric.
    if stem.isdigit():
        code = stem.zfill(4)
    else:
        # fallback: keep alphanum only
        code = re.sub(r'[^0-9A-Za-z]+', '', stem)[:16]
    return f"#ms{code}"


def union_variant_spans(lem_toks: List[str], wit_toks_map: Dict[str, List[str]]) -> List[Tuple[int, int]]:
    """Compute union of differing spans over all witnesses as a list of [start, end) token index ranges in lemma tokens."""
    n = len(lem_toks)
    mask = [False] * n
    for ms, wtoks in wit_toks_map.items():
        sm = difflib.SequenceMatcher(None, lem_toks, wtoks)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                continue
            for i in range(i1, i2):
                if 0 <= i < n:
                    mask[i] = True
    # Convert mask to ranges
    ranges: List[Tuple[int,int]] = []
    i = 0
    while i < n:
        if not mask[i]:
            i += 1
            continue
        j = i
        while j < n and mask[j]:
            j += 1
        ranges.append((i, j))
        i = j
    return ranges


def differing_token_indices(lem_toks: List[str], wit_toks_map: Dict[str, List[str]]) -> List[int]:
    """Return list of lemma token indices i where at least one witness differs at that token.

    Uses token-level alignment; insertions/deletions overlapping a lemma token mark that token.
    """
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
    """Return witness reading text for a lemma span using token alignment.

    - For single-token spans (per-word), map that lemma token to the corresponding witness token(s)
      using the alignment block that covers it, avoiding spill-over from neighbouring tokens.
    - For multi-token spans (legacy mode), include overlapping witness segments.
    """
    a, b = span
    sm = normalized_sequence_matcher(lem_toks, wit_toks)
    parts: List[str] = []
    one_token = (b == a + 1)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if i2 <= a or i1 >= b:
            continue  # no overlap with span
        if one_token:
            i = a
            if tag == 'equal':
                off = i - i1
                if 0 <= off < (i2 - i1) and (j1 + off) < j2:
                    parts.append(wit_toks[j1 + off])
            elif tag == 'replace':
                # Improved mapping: distribute witness tokens across lemma tokens proportionally.
                L_len = i2 - i1
                W_len = j2 - j1
                off = i - i1
                if L_len == W_len and W_len > 0:
                    parts.append(wit_toks[j1 + off])
                elif W_len == 1 and W_len > 0:
                    # Single witness token represents multiple lemma tokens (compound).
                    parts.append(wit_toks[j1])
                elif W_len > 1 and L_len > 0:
                    rel = off / L_len
                    w_index = j1 + int(rel * W_len)
                    if w_index >= j2:
                        w_index = j2 - 1
                    parts.append(wit_toks[w_index])
                else:
                    # Fallback: no witness tokens (deletion) or unexpected empty slice.
                    pass
            elif tag == 'delete':
                pass  # deleted token → empty
            # ignore inserts
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


def extract_reading_for_span_with_compounds(lem_toks: List[str], wit_toks: List[str], 
                                           span: Tuple[int, int], 
                                           compound_map: Dict[int, Tuple[int, int]]) -> str:
    """Extract witness reading for a single-token span, considering compound token mappings.
    
    For compound tokens (witness token covering multiple canonical tokens):
    - Return the full compound witness token for ALL canonical tokens it covers
    - This shows that the witness has this reading, even though it's merged
    
    For non-compound tokens: use standard alignment-based extraction.
    """
    a, b = span
    
    # ONLY handle single-token spans (b == a+1)
    if b != a + 1:
        # For multi-token spans, fall back to standard extraction
        return extract_reading_for_span(lem_toks, wit_toks, span)
    
    canonical_idx = a
    
    # Check if this canonical token is part of a compound witness token
    for wit_idx, (lem_start, lem_end) in compound_map.items():
        if lem_start <= canonical_idx < lem_end:
            # This canonical token is covered by a compound witness token
            # Return the full compound for ALL tokens it covers
            if 0 <= wit_idx < len(wit_toks):
                return wit_toks[wit_idx]
    
    # Not part of a compound: delegate to robust span extractor (handles length mismatches)
    return extract_reading_for_span(lem_toks, wit_toks, span)


def ensure_header(root: etree._Element, title: str):
    header = etree.SubElement(root, f'{{{NS_TEI}}}teiHeader')
    fileDesc = etree.SubElement(header, f'{{{NS_TEI}}}fileDesc')
    titleStmt = etree.SubElement(fileDesc, f'{{{NS_TEI}}}titleStmt')
    etree.SubElement(titleStmt, f'{{{NS_TEI}}}title').text = title
    pubStmt = etree.SubElement(fileDesc, f'{{{NS_TEI}}}publicationStmt')
    etree.SubElement(pubStmt, f'{{{NS_TEI}}}p').text = 'Generated automatically from selected witnesses'
    sourceDesc = etree.SubElement(fileDesc, f'{{{NS_TEI}}}sourceDesc')
    etree.SubElement(sourceDesc, f'{{{NS_TEI}}}p').text = 'Lemma: Yasna_Static.xml; Witnesses: user-provided TEI files'
    # taxonomy
    enc = etree.SubElement(header, f'{{{NS_TEI}}}encodingDesc')
    tax = etree.SubElement(enc, f'{{{NS_TEI}}}taxonomy')
    tax.set(f'{{{NS_XML}}}id', 'varClass')
    for cat in ['meaningful', 'trivial', 'unknown']:
        c = etree.SubElement(tax, f'{{{NS_TEI}}}category')
        c.set(f'{{{NS_XML}}}id', cat)
        c.text = cat.capitalize()


def build_apparatus(lemma_path: Path, parts: List[str], witness_paths: List[Path], out_path: Path, per_ms_rdg: bool = False, per_word_apps: bool = False):
    # Gather lemma text per ab
    ab_list = gather_lemma_ab(lemma_path, parts)
    # In-function Y9 defaults as a safety net (covers direct calls too)
    if any((p or '').upper().startswith('Y9') for p in parts):
        if not per_ms_rdg:
            per_ms_rdg = True
        if not per_word_apps:
            per_word_apps = True
    ab_ids = [aid for aid, _ in ab_list]

    # Load optional AB id remap (if present)
    remap_path = Path('res/Yasna/meta/ab_id_remap.yaml')
    ab_remap_all = _load_ab_id_remap(remap_path) if remap_path.exists() else {}
    # Load witnesses' texts per ab
    witnesses_by_ab: Dict[str, Dict[str, str]] = {aid: {} for aid in ab_ids}
    ms_ids: Dict[Path, str] = {wp: ms_id_from_filename(wp) for wp in witness_paths}
    ms_list = sorted(ms_ids.values())
    for wp in witness_paths:
        ms_code = ms_ids[wp].lstrip('#')
        wt_map = load_witness_ab_texts(wp, ab_ids, remap_for_witness=ab_remap_all.get(ms_code))
        ms_id = ms_ids[wp]
        for aid, txt in wt_map.items():
            witnesses_by_ab[aid][ms_id] = txt

    # Build TEI
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
            continue  # no witnesses available for this ab
        lem_toks = tokenize(lem_text)
        wit_toks_map = {ms: tokenize(txt) for ms, txt in wit_txts.items()}
        
        # Detect compound tokens for each witness
        compound_maps = {}
        for ms, wtoks in wit_toks_map.items():
            compound_maps[ms] = detect_compound_tokens(lem_toks, wtoks)
        
        # Build spans: ALWAYS create one span per token (one lemma token per apparatus entry)
        # Witness readings can span multiple tokens via compound detection
        spans_set = set()
        
        if per_word_apps:
            # Add single-token spans for ALL differing tokens
            idxs = differing_token_indices(lem_toks, wit_toks_map)
            for i in idxs:
                spans_set.add((i, i+1))
            
            # Also add apparatus entries for canonical tokens covered by compound witness tokens
            # even if they don't show up as "differing" in the basic alignment
            for ms, cmap in compound_maps.items():
                for wit_idx, (lem_start, lem_end) in cmap.items():
                    # Add single-token entries for all tokens covered by this compound
                    for i in range(lem_start, lem_end):
                        spans_set.add((i, i+1))
        else:
            # Use union variant spans for non-per-word mode
            span_list = union_variant_spans(lem_toks, wit_toks_map)
            spans_set = set(span_list)
        
        # Sort spans by start position
        spans = sorted(list(spans_set))
        
        if not spans:
            continue
        
        for idx, (a, b) in enumerate(spans, start=1):
            app = etree.SubElement(div, f'{{{NS_TEI}}}app')
            app.set(f'{{{NS_XML}}}id', f"app-{aid}-{a}-{b}")
            lem_segment = ' '.join(lem_toks[a:b])
            lem_el = etree.SubElement(app, f'{{{NS_TEI}}}lem')
            lem_el.text = lem_segment
            if per_ms_rdg:
                # Emit one rdg per requested manuscript (no grouping). If a manuscript
                # lacks this AB, include an empty reading as a placeholder.
                for ms in ms_list:
                    wtoks = wit_toks_map.get(ms)
                    if wtoks is not None:
                        cmap = compound_maps.get(ms, {})
                        rdg_txt = extract_reading_for_span_with_compounds(lem_toks, wtoks, (a, b), cmap)
                    else:
                        rdg_txt = ''
                    rdg = etree.SubElement(app, f'{{{NS_TEI}}}rdg')
                    rdg.set('wit', ms)
                    rdg.text = rdg_txt
            else:
                # Group readings with identical surface text across witnesses
                surf_to_wits: Dict[str, List[str]] = defaultdict(list)
                for ms, wtoks in wit_toks_map.items():
                    cmap = compound_maps.get(ms, {})
                    rdg_txt = extract_reading_for_span_with_compounds(lem_toks, wtoks, (a, b), cmap)
                    if not rdg_txt:
                        rdg_txt = ''
                    surf_to_wits[rdg_txt].append(ms)
                for surf, wit_list in surf_to_wits.items():
                    rdg = etree.SubElement(app, f'{{{NS_TEI}}}rdg')
                    rdg.set('wit', ' '.join(sorted(wit_list)))
                    rdg.text = surf
            apps_created += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    etree.ElementTree(root).write(str(out_path), encoding='utf-8', pretty_print=True, xml_declaration=True)
    print(f"Built apparatus with {apps_created} app entries for parts {parts} into {out_path}")


def detect_compound_tokens(lem_toks: List[str], wit_toks: List[str], max_compound_size: int = 4) -> Dict[int, Tuple[int, int]]:
    """Detect witness tokens that are compounds of multiple consecutive canonical tokens.
    
    Returns a mapping: witness_token_index -> (canonical_start_idx, canonical_end_idx)
    
    For example, if canonical has ["ahurō", "mazdā"] at positions 3-4 and witness has ["ahuramazdā"] at position 3,
    this returns {3: (3, 5)} indicating witness token 3 corresponds to canonical tokens 3-5.
    """
    compound_map: Dict[int, Tuple[int, int]] = {}
    
    # First, get basic alignment
    sm = normalized_sequence_matcher(lem_toks, wit_toks)
    
    # Track which canonical positions are already matched
    lem_matched = [False] * len(lem_toks)
    wit_matched = [False] * len(wit_toks)
    
    # Mark simple equal matches first
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for i in range(i1, i2):
                lem_matched[i] = True
            for j in range(j1, j2):
                wit_matched[j] = True
    
    # Now look for compound matches in unmatched witness tokens
    for j in range(len(wit_toks)):
        if wit_matched[j]:
            continue
            
        wit_tok_normalized = normalize_token(wit_toks[j])
        
        # Try to match this witness token against consecutive runs of canonical tokens
        for run_len in range(2, min(max_compound_size + 1, len(lem_toks) + 1)):
            for i_start in range(len(lem_toks) - run_len + 1):
                # Skip if any token in this run is already matched
                if any(lem_matched[i] for i in range(i_start, i_start + run_len)):
                    continue
                
                # Concatenate the canonical tokens (removing spaces and dots)
                lem_compound = ''.join([normalize_token(lem_toks[i]) for i in range(i_start, i_start + run_len)])
                
                # Check if witness token matches this compound
                # Use fuzzy matching to handle slight variations
                ratio = difflib.SequenceMatcher(None, wit_tok_normalized, lem_compound).ratio()
                
                # Also check if witness starts with first token and contains last token (partial match)
                first_tok = normalize_token(lem_toks[i_start])
                last_tok = normalize_token(lem_toks[i_start + run_len - 1])
                partial_match = (wit_tok_normalized.startswith(first_tok) and 
                               last_tok in wit_tok_normalized and
                               len(wit_tok_normalized) > len(first_tok))
                
                if ratio > 0.75 or partial_match:
                    # Found a compound match!
                    compound_map[j] = (i_start, i_start + run_len)
                    # Mark these canonical positions as matched
                    for i in range(i_start, i_start + run_len):
                        lem_matched[i] = True
                    wit_matched[j] = True
                    break  # Stop searching for this witness token
            
            if wit_matched[j]:
                break  # Found a match, move to next witness token
    
    return compound_map


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lemma', default='data/Yasna_Static.xml', help='Lemma TEI file (baseline)')
    ap.add_argument('--parts', required=True, help='Comma-separated part prefixes (e.g., Y9 or Y9,Y10)')
    ap.add_argument('--witness-files', required=True, help='Comma-separated paths to witness TEI files')
    ap.add_argument('--out', required=True, help='Output TEI apparatus path')
    # Global defaults: per-ms and per-word enabled by default; allow disabling with --no-*
    ap.add_argument('--per-ms-rdg', dest='per_ms_rdg', action='store_true', help='Emit one <rdg> per manuscript instead of grouping identical readings')
    ap.add_argument('--no-per-ms-rdg', dest='per_ms_rdg', action='store_false', help='Disable per-manuscript readings (group identical readings)')
    ap.set_defaults(per_ms_rdg=True)
    ap.add_argument('--per-word-apps', dest='per_word_apps', action='store_true', help='Create one <app> per differing word (token) instead of multi-word spans')
    ap.add_argument('--no-per-word-apps', dest='per_word_apps', action='store_false', help='Allow multi-word spans when differences merge across adjacent tokens')
    ap.set_defaults(per_word_apps=True)
    args = ap.parse_args()

    parts = [p.strip() for p in args.parts.split(',') if p.strip()]
    witnesses = [Path(p.strip()) for p in args.witness_files.split(',') if p.strip()]
    # Global defaults now True; explicit flags can disable
    per_ms = bool(args.per_ms_rdg)
    per_word = bool(args.per_word_apps)
    build_apparatus(Path(args.lemma), parts, witnesses, Path(args.out), per_ms_rdg=per_ms, per_word_apps=per_word)


if __name__ == '__main__':
    main()
