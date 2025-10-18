import os
import re
import unicodedata
import json
import difflib
import nltk
import argparse
from lxml import etree

from src.interfaces.xml_translator.matcher import single_match


def extract_divs_by_id(tree):
    root = tree.getroot()
    divs = {}
    # find all div elements with an xml:id attribute
    for div in root.findall('.//div'):
        xml_id = div.get('{http://www.w3.org/XML/1998/namespace}id') or div.get('xml:id') or div.get('id')
        if xml_id:
            divs[xml_id] = div
    return divs


def extract_words_from_div(div, insert_space_after_period=False):
    # Collect visible text in order from ab elements inside the div.
    words = []
    if div is None:
        return words
    # Tags to skip entirely when collecting text (keep lb handled specially)
    skip_tags = {'pb', 'supplied', 'abbr', 'foreign', 'nerang'}

    for ab in div.findall('.//ab'):
        # If this <ab> is explicitly marked as Pahlavi/Persian or is a Nerang block, skip it entirely.
        ab_lang = ab.get('{http://www.w3.org/XML/1998/namespace}lang') or ab.get('xml:lang') or ab.get('lang')
        ab_n = (ab.get('n') or '')
        ab_xml_id = (ab.get('{http://www.w3.org/XML/1998/namespace}id') or ab.get('xml:id') or ab.get('id') or '')
        if ab_lang and ab_lang.lower() in ('pahl', 'pers'):
            continue
        if 'nerang' in ab_n.lower() or 'nerang' in ab_xml_id.lower():
            continue

        # Work on a copy so we can safely modify app/seg nodes without changing original tree
        ab_copy = etree.fromstring(etree.tostring(ab))
        # Preprocess app/rdg/seg: replace <app> with rdg[@type='mod'] text when available;
        # remove <seg> elements and prefer rdg type='mod' over rdg type='orig'
        for app in ab_copy.findall('.//app'):
            mod_rdg = app.find('.//rdg[@type="mod"]')
            if mod_rdg is None:
                # fallback to orig or first rdg
                mod_rdg = app.find('.//rdg[@type="orig"]') or app.find('.//rdg')
            replacement_text = ''
            if mod_rdg is not None:
                # join itertext parts with a single space to preserve boundaries between readings
                parts = [t.strip() for t in mod_rdg.itertext() if t and t.strip()]
                replacement_text = ' '.join(parts)
            parent = app.getparent()
            if parent is not None:
                idx = parent.index(app)
                # preserve the original tail so following text isn't lost
                original_tail = app.tail
                # create a text node element to hold replacement text
                new = etree.Element('span')
                new.text = replacement_text
                new.tail = original_tail
                parent.remove(app)
                parent.insert(idx, new)

        # replace any remaining <seg> elements with their text (or a single space) to avoid collapsing words
        for seg in ab_copy.findall('.//seg'):
            seg_parent = seg.getparent()
            if seg_parent is not None:
                idx = seg_parent.index(seg)
                original_tail = seg.tail
                new = etree.Element('span')
                seg_text_parts = [t.strip() for t in seg.itertext() if t and t.strip()]
                new.text = ' '.join(seg_text_parts) if seg_text_parts else ' '
                new.tail = original_tail
                seg_parent.remove(seg)
                seg_parent.insert(idx, new)

        # build text only from nodes that are not in skip_tags and not in Pahlavi/Persian language
        parts = []
        for node in ab_copy.iter():
            # skip XML comments (they sometimes contain transliteration/nerang content)
            if isinstance(node, etree._Comment):
                continue
            # element tag local-name
            tag = etree.QName(node.tag).localname if isinstance(node.tag, str) else ''
            # check xml:lang attribute
            lang = node.get('{http://www.w3.org/XML/1998/namespace}lang') or node.get('xml:lang') or node.get('lang')
            if tag in skip_tags:
                # skip node text and its subtree
                continue
            if lang and lang.lower() in ('pahl', 'pers'):
                continue
            # Special handling for line-breaks: when break="no" join tail without extra space
            if tag == 'lb':
                br = node.get('break')
                tail = node.tail or ''
                if br and br.lower() == 'no':
                    # if previous part exists and is text-like, merge directly into it
                    if parts and isinstance(parts[-1], tuple):
                        parts[-1] = (parts[-1][0], parts[-1][1].rstrip() + tail.lstrip())
                    else:
                        parts.append(('LB_JOIN', tail.lstrip()))
                else:
                    # treat as normal boundary: append as separate text piece
                    parts.append(('LB_BREAK', tail or ''))
                continue
            # include text and tail for other nodes (store as tuples)
            if node.text:
                parts.append(('TEXT', node.text))
            if node.tail:
                parts.append(('TAIL', node.tail))
        # parts is a list of (kind, text) tuples; join the text portion
        text = ''.join([p[1] for p in parts if isinstance(p, tuple)])
        # Optionally ensure dot+no-space sequences are treated as sentence boundary (only for manuscript text)
        if insert_space_after_period:
            text = re.sub(r'\.(?=[^\s\d\W])', '. ', text)

        tokens = tokenize(text)
        # filter out pahlavi-like tokens
        tokens = [t for t in tokens if not is_pahlavi_token(t)]
        # normalize tokens (NFC, lowercase, safe replacements)
        tokens = [normalize_token(t) for t in tokens]
        words.extend(tokens)
    # fallback: if no ab children, tokenize the div text
    if not words:
        text = ''.join(div.itertext())
        words = tokenize(text)
    return words


def tokenize(text):
    # split on whitespace and strip surrounding punctuation
    raw_tokens = re.findall(r"[^\s<>]+", text)
    tokens = []
    for t in raw_tokens:
        # remove surrounding punctuation characters but preserve dots (.) so dot+space boundaries remain
        cleaned = t.strip(',;:\"()[]{}«»—–')
        if cleaned:
            tokens.append(cleaned)
    return tokens


def normalize_token(tok: str) -> str:
    # NFC normalization and lowercase
    t = unicodedata.normalize('NFC', tok)
    # common visual normalizations
    t = t.replace('⸳', '.')
    t = t.replace('⁛', '')
    # normalize spacing/punctuation inside token
    t = t.strip()
    # lowercase to make matching more forgiving
    t = t.lower()
    return t


def is_pahlavi_token(token: str) -> bool:
    """Heuristic to detect Pahlavi/Persian tokens we want to ignore.

    We treat tokens as Pahlavi-like when they contain ASCII uppercase letters, digits,
    hyphens or apostrophes typical of nerang transliterations (e.g. HNHTWN-tn').
    This heuristic is conservative: it only returns True when token has uppercase
    letters or digits or hyphen/apostrophe and lacks many lowercase a-z letters.
    """
    # if token has any characters from A-Z or digits or hyphen/apostrophe
    if re.search(r'[A-Z0-9]', token) or re.search(r"[-']", token):
        # count lowercase letters
        lower_count = len(re.findall(r'[a-zāąēīōūẏŋšṣḥδθṯṙṝ̣̇]', token, flags=re.IGNORECASE))
        # if there are few lowercase letters, treat as pahlavi-like
        if lower_count <= 1:
            return True
    return False


def align_word_sequences(canon_words, our_words, window=3, ratio_threshold=0.68, max_canon_span=3):
    """Local-window matching: for each canonical word, search nearby our_words for best match.

    Prefer matches where `single_match` returns True; otherwise pick candidate with highest
    string similarity (difflib ratio) above ratio_threshold. Unmatched canonical words are
    marked as deletes; unmatched our words are inserts.
    """
    m = len(our_words)
    our_matched = [False] * m
    matches = []

    # Greedy monotonic matching: iterate over manuscript tokens (our_words) and match to the earliest
    # possible canonical token after the last matched canonical index. This prevents earlier canon tokens
    # from being bound to a later manuscript token when words are missing.
    n = len(canon_words)
    canon_matched = [None] * n  # will store our_index matched to this canonical index
    last_ci = -1
    # max number of canonical tokens to try concatenating when matching a single manuscript token
    # kept as a parameter so it can be tuned from the CLI without changing code
    # (default 3 to preserve previous behavior)
    # max_canon_span = 3

    for oi, ow in enumerate(our_words):
        best = None
        best_score = (-1.0, float('-inf'))
        best_ratio = -1.0
        # search canonical tokens starting from just after last matched index
        search_start = last_ci + 1
        search_end = min(n, search_start + window * 3 + 1)

        # prefer exact/single-match via single_match
        for ci in range(search_start, search_end):
            if canon_matched[ci] is not None:
                continue
            try:
                if single_match(canon_words[ci], ow):
                    best = (ci, 1, 1.0)
                    best_ratio = 1.0
                    best_score = (1.0, -0)
                    break
            except Exception:
                pass

        # similarity fallback: try single canonical tokens
        if best is None:
            for ci in range(search_start, search_end):
                if canon_matched[ci] is not None:
                    continue
                a = normalize_token(canon_words[ci])
                b = normalize_token(ow)
                ratio = difflib.SequenceMatcher(None, a, b).ratio()
                a_alt = a.replace('ii', 'ai').replace('ə̄', 'ē')
                b_alt = b.replace('ii', 'ai').replace('ə̄', 'ē')
                ratio_alt = max(difflib.SequenceMatcher(None, a_alt, b).ratio(),
                                difflib.SequenceMatcher(None, a, b_alt).ratio(),
                                difflib.SequenceMatcher(None, a_alt, b_alt).ratio())
                ratio = max(ratio, ratio_alt)
                score = (ratio, -abs(ci - search_start))
                if score > best_score:
                    best_score = score
                    best_ratio = ratio
                    best = (ci, 1, ratio)

        # try concatenating small spans of canonical tokens (many-to-one) but only if they immediately start at ci
        if best is None or best_ratio < ratio_threshold:
            for ci in range(search_start, min(n, search_start + window * 3)):
                if canon_matched[ci] is not None:
                    continue
                for span in range(2, max_canon_span + 1):
                    if ci + span > n:
                        break
                    if any(canon_matched[ci + k] is not None for k in range(span)):
                        continue
                    combined = [canon_words[ci + k] for k in range(span)]
                    cand_variants = [".".join(combined), "".join(combined)]
                    for cvar in cand_variants:
                        a = normalize_token(cvar)
                        b = normalize_token(ow)
                        ratio = difflib.SequenceMatcher(None, a, b).ratio()
                        a_alt = a.replace('ii', 'ai').replace('ə̄', 'ē')
                        b_alt = b.replace('ii', 'ai').replace('ə̄', 'ē')
                        ratio_alt = max(difflib.SequenceMatcher(None, a_alt, b).ratio(),
                                        difflib.SequenceMatcher(None, a, b_alt).ratio(),
                                        difflib.SequenceMatcher(None, a_alt, b_alt).ratio())
                        ratio = max(ratio, ratio_alt)
                        # Before accepting a many-to-one candidate, ensure none of the
                        # component canonical tokens already have a near-exact individual
                        # match elsewhere in the stanza (to avoid stealing those matches).
                        reject_span_due_to_duplicates = False
                        for k in range(span):
                            comp_ci = ci + k
                            comp_norm = normalize_token(canon_words[comp_ci]).replace('.', '')
                            # scan for other occurrences of same normalized token
                            for other_ci in range(n):
                                if other_ci >= ci and other_ci < ci + span:
                                    # skip components inside this candidate span
                                    continue
                                if normalize_token(canon_words[other_ci]).replace('.', '') != comp_norm:
                                    continue
                                other_oi = canon_matched[other_ci]
                                if other_oi is None or other_oi == oi:
                                    continue
                                other_our = our_words[other_oi] if other_oi < len(our_words) else ''
                                comp_vs_other_our_ratio = difflib.SequenceMatcher(None, comp_norm, normalize_token(other_our).replace('.', '')).ratio()
                                if comp_vs_other_our_ratio >= 0.95:
                                    reject_span_due_to_duplicates = True
                                    break
                            if reject_span_due_to_duplicates:
                                break

                        if reject_span_due_to_duplicates:
                            # skip this candidate span because it would steal a strong
                            # individual match elsewhere
                            continue

                        score = (ratio, -abs(ci - search_start))
                        if score > best_score:
                            best_score = score
                            best_ratio = ratio
                            best = (ci, span, ratio)
                if best_ratio >= 0.95:
                    break

        # Accept best candidate if it passes threshold
        if best is not None and best_ratio >= ratio_threshold:
            ci, span, _ = best
            for k in range(span):
                canon_matched[ci + k] = oi
            last_ci = ci + span - 1

    # Build matches: canonical tokens (in order)
    # --- Conservative post-processing helper: try merging next canonical into current match ---
    def levenshtein(a: str, b: str) -> int:
        # small DP implementation, fine for short tokens
        if a == b:
            return 0
        la, lb = len(a), len(b)
        if la == 0:
            return lb
        if lb == 0:
            return la
        prev = list(range(lb + 1))
        for i, ca in enumerate(a, start=1):
            cur = [i] + [0] * lb
            for j, cb in enumerate(b, start=1):
                cost = 0 if ca == cb else 1
                cur[j] = min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + cost)
            prev = cur
        return prev[lb]

    # Try to merge next canonical token into current matched canonical token, but only as a
    # conservative last-resort: require near-exact match (edit distance <= 1) or containment
    # with similar length (difference <= 2). This prevents frequent editorial phrases from
    # being appended to a nearby manuscript token.
    for ci in range(0, n - 1):
        oi = canon_matched[ci]
        if oi is None:
            continue
        # normalize strings for distance comparison
        a = normalize_token(canon_words[ci])
        b = normalize_token(our_words[oi]) if oi < len(our_words) else ''
        a_clean = a.replace('.', '')
        b_clean = b.replace('.', '')
        # if equal and small length diff, skip (already matched well)
        if a_clean == b_clean and abs(len(a_clean) - len(b_clean)) <= 2:
            continue
        # look ahead to next canonical token
        if canon_matched[ci + 1] is not None:
            continue
        next_tok = normalize_token(canon_words[ci + 1])
        combined = (a + next_tok).replace('.', '')
        # compute edit distance between combined and manuscript token
        dist = levenshtein(combined, b_clean)
        # allow containment only when lengths are similar (to avoid editorial prefixes)
        length_similar = abs(len(combined) - len(b_clean)) <= 2
        contains = (combined in b_clean or b_clean in combined) and length_similar
        # Before merging, ensure that neither component token is strongly matched
        # elsewhere (to avoid stealing a one-to-one match from another manuscript token).
        for ci in range(0, n - 1):
            oi = canon_matched[ci]
            if oi is None:
                continue
            # normalize strings for distance comparison
            a = normalize_token(canon_words[ci])
            b = normalize_token(our_words[oi]) if oi < len(our_words) else ''
            a_clean = a.replace('.', '')
            b_clean = b.replace('.', '')
            # if equal and small length diff, skip (already matched well)
            if a_clean == b_clean and abs(len(a_clean) - len(b_clean)) <= 2:
                continue
            # look ahead to next canonical token
            if canon_matched[ci + 1] is not None:
                continue
            next_tok = normalize_token(canon_words[ci + 1])
            combined = (a + next_tok).replace('.', '')
            # compute edit distance between combined and manuscript token
            dist = levenshtein(combined, b_clean)
            # allow containment only when lengths are similar (to avoid editorial prefixes)
            length_similar = abs(len(combined) - len(b_clean)) <= 2
            contains = (combined in b_clean or b_clean in combined) and length_similar
            # duplicate-safety: if either component token has a near-exact match elsewhere,
            # don't merge here (prefer the other one-to-one matches)
            reject_merge_due_to_duplicates = False
            for comp_ci in (ci, ci + 1):
                comp_norm = normalize_token(canon_words[comp_ci]).replace('.', '')
                for other_ci in range(n):
                    if other_ci == comp_ci:
                        continue
                    if normalize_token(canon_words[other_ci]).replace('.', '') != comp_norm:
                        continue
                    other_oi = canon_matched[other_ci]
                    if other_oi is None or other_oi == oi:
                        continue
                    other_our = our_words[other_oi] if other_oi < len(our_words) else ''
                    comp_vs_other_our_ratio = difflib.SequenceMatcher(None, comp_norm, normalize_token(other_our).replace('.', '')).ratio()
                    if comp_vs_other_our_ratio >= 0.95:
                        reject_merge_due_to_duplicates = True
                        break
                if reject_merge_due_to_duplicates:
                    break
            if dist <= 2 or contains:
                if not reject_merge_due_to_duplicates:
                    # merge: assign next canonical token to same our_index
                    canon_matched[ci + 1] = oi
    # Reverse pass: if current canonical is unmatched but next is matched, try attaching current
    # to next's our_index but only under conservative conditions (edit distance <=1 or
    # containment with similar length).
    for ci in range(0, n - 1):
        if canon_matched[ci] is not None:
            continue
        next_oi = canon_matched[ci + 1]
        if next_oi is None:
            continue
        # combined string of current+next
        cur = normalize_token(canon_words[ci]).replace('.', '')
        nxt = normalize_token(canon_words[ci + 1]).replace('.', '')
        combined = (cur + nxt)
        b_clean = normalize_token(our_words[next_oi]).replace('.', '') if next_oi < len(our_words) else ''
        dist = levenshtein(combined, b_clean)
        length_similar = abs(len(combined) - len(b_clean)) <= 2
        contains = (combined in b_clean or b_clean in combined) and length_similar
        # duplicate-safety: if either component token has a near-exact match elsewhere,
        # do not attach it to the next matched our index.
        reject_merge_due_to_duplicates = False
        for comp_ci in (ci, ci + 1):
            comp_norm = normalize_token(canon_words[comp_ci]).replace('.', '')
            for other_ci in range(n):
                if other_ci == comp_ci:
                    continue
                if normalize_token(canon_words[other_ci]).replace('.', '') != comp_norm:
                    continue
                other_oi = canon_matched[other_ci]
                if other_oi is None or other_oi == next_oi:
                    continue
                other_our = our_words[other_oi] if other_oi < len(our_words) else ''
                comp_vs_other_our_ratio = difflib.SequenceMatcher(None, comp_norm, normalize_token(other_our).replace('.', '')).ratio()
                if comp_vs_other_our_ratio >= 0.95:
                    reject_merge_due_to_duplicates = True
                    break
            if reject_merge_due_to_duplicates:
                break
        if dist <= 2 or contains:
            if not reject_merge_due_to_duplicates:
                canon_matched[ci] = next_oi

    # --- Crossing / inversion fixer ---
    # Greedy monotonic matching can sometimes match two canonical tokens to manuscript
    # tokens in inverted order (oi > oj for ci < cj). Try small-window local swaps when
    # the sum of similarities improves by swapping the assigned manuscript indices.
    def token_similarity(a_tok: str, b_tok: str) -> float:
        a = normalize_token(a_tok).replace('.', '')
        b = normalize_token(b_tok).replace('.', '')
        return difflib.SequenceMatcher(None, a, b).ratio()

    cross_window = 12  # look ahead up to this many canonical tokens for inverted matches
    improvement_delta = 0.05
    for ci in range(n):
        oi = canon_matched[ci]
        if oi is None:
            continue
        # look forward for inverted pairs
        for cj in range(ci + 1, min(n, ci + 1 + cross_window)):
            oj = canon_matched[cj]
            if oj is None:
                continue
            # inversion: earlier canon assigned to later our index
            if oi > oj:
                # compute current similarity sum and swapped sum
                cur = token_similarity(canon_words[ci], our_words[oi]) + token_similarity(canon_words[cj], our_words[oj])
                swapped = token_similarity(canon_words[ci], our_words[oj]) + token_similarity(canon_words[cj], our_words[oi])
                if swapped > cur + improvement_delta:
                    # perform swap
                    canon_matched[ci], canon_matched[cj] = oj, oi
                    # update oi for cascading checks
                    oi = canon_matched[ci]
    for ci, cw in enumerate(canon_words):
        oi = canon_matched[ci]
        if oi is None:
            matches.append({
                'canon_index': ci,
                'our_index': None,
                'canon_word': cw,
                'our_word': '',
                'relation': 'delete',
                'matched': False
            })
        else:
            ow = our_words[oi]
            # detect many-to-one when the same manuscript index is used for multiple canonical tokens
            count = canon_matched.count(oi)
            if count > 1:
                relation = 'many-to-one'
            else:
                relation = 'equal' if normalize_token(cw) == normalize_token(ow) else 'substitution'
            matches.append({
                'canon_index': ci,
                'our_index': oi,
                'canon_word': cw,
                'our_word': ow,
                'relation': relation,
                'matched': True
            })

    # remaining unmatched our words -> inserts
    used_our = set([oi for oi in canon_matched if oi is not None])
    for oi, ow in enumerate(our_words):
        if oi not in used_our:
            matches.append({
                'canon_index': None,
                'our_index': oi,
                'canon_word': '',
                'our_word': ow,
                'relation': 'insert',
                'matched': False
            })

    # --- Add explicit merged entries for readability: when multiple canonical tokens map to the
    # same manuscript token (many-to-one), create a combined record showing the joined canonical
    # form (e.g. "fərā.tanuuascīt̰.") mapped to the manuscript token. Also detect simple
    # one-to-many on the manuscript side: adjacent manuscript tokens that together match a
    # single canonical token and emit a combined record for that too. These are appended as
    # additional records (do not remove the original per-token records) so the merge is visible.

    # build mapping our_index -> list of canon indices
    our_to_canons = {}
    for ci, oi in enumerate(canon_matched):
        if oi is None:
            continue
        our_to_canons.setdefault(oi, []).append(ci)

    # many-to-one canonical -> our: create merged canonical records only when the combined
    # canonical string clearly corresponds to the manuscript token. This avoids noisy merges
    # (e.g. frequent editorial phrases) while keeping genuine concatenations like the Y0.7 case.
    def strip_trailing_dot(s):
        return s[:-1] if s.endswith('.') else s

    for oi, cis in our_to_canons.items():
        if len(cis) <= 1:
            continue
        cis_sorted = sorted(cis)
        canon_tokens = [canon_words[i] for i in cis_sorted]
        combined_core = '.'.join([strip_trailing_dot(t) for t in canon_tokens])
        combined_canon = combined_core + '.'

        # normalized forms for comparison
        combined_norm = normalize_token(combined_canon).replace('.', '')
        our_norm = normalize_token(our_words[oi]).replace('.', '') if oi < len(our_words) else ''
        # strong-merge conditions: near-exact (<=1 edit) OR very high ratio OR containment
        # with length-similarity (containment alone is not sufficient; it must be a near-equal length)
        ratio_combined = difflib.SequenceMatcher(None, combined_norm, our_norm).ratio()
        dist_combined = levenshtein(combined_norm, our_norm)
        length_similar = abs(len(combined_norm) - len(our_norm)) <= 3
        containment = combined_norm and (combined_norm in our_norm or our_norm in combined_norm) and length_similar
        # Avoid creating a merged record when one of the component canonical tokens
        # already has a strong individual match elsewhere in the stanza. This
        # prevents merging duplicated small tokens (like "yō."/"nō.") into a
        # nearby manuscript token when the same tokens are matched one-to-one
        # elsewhere.
        reject_merge_due_to_duplicates = False
        for ci_comp in cis_sorted:
            comp_norm = normalize_token(canon_words[ci_comp]).replace('.', '')
            # scan for the same normalized component elsewhere with a different assignment
            for other_ci in range(n):
                if other_ci in cis_sorted:
                    continue
                if normalize_token(canon_words[other_ci]).replace('.', '') != comp_norm:
                    continue
                other_oi = canon_matched[other_ci]
                if other_oi is None or other_oi == oi:
                    continue
                # compute how well that other occurrence matches its manuscript match
                other_our = our_words[other_oi] if other_oi < len(our_words) else ''
                comp_vs_other_our_ratio = difflib.SequenceMatcher(None, comp_norm, normalize_token(other_our).replace('.', '')).ratio()
                # require a near-exact individual match elsewhere to count as a duplicate
                if comp_vs_other_our_ratio >= 0.95:
                    # there exists a strong individual match for this component elsewhere
                    reject_merge_due_to_duplicates = True
                    break
            if reject_merge_due_to_duplicates:
                break

        if not reject_merge_due_to_duplicates and (dist_combined <= 2 or ratio_combined >= 0.95 or containment):
            matches.append({
                'canon_indexes': cis_sorted,
                'canon_word': combined_canon,
                'our_index': oi,
                'our_word': our_words[oi] if oi < len(our_words) else '',
                'relation': 'many-to-one (merged)',
                'matched': True
            })

    # one-to-many our -> canonical: look for adjacent our tokens around a matched our_index
    # that together better match the canonical token; append a merged our record when found.
    used_our_for_merge = set()
    for ci, oi in enumerate(canon_matched):
        if oi is None:
            continue
        # check left neighbor
        for offset in (-1, 1):
            other = oi + offset
            if other < 0 or other >= len(our_words):
                continue
            # skip if other is already used in a merged canonical group
            if other in used_our_for_merge:
                continue
            # Only consider other if it's not currently used by any canonical (i.e., unmatched)
            if other in our_to_canons:
                # it's used by a canon already; skip to avoid conflicts
                continue
            # try combining the two our tokens in canonical order
            if offset == -1:
                combined_our = strip_trailing_dot(our_words[other]) + '.' + strip_trailing_dot(our_words[oi]) + '.'
                our_indexes = [other, oi]
            else:
                combined_our = strip_trailing_dot(our_words[oi]) + '.' + strip_trailing_dot(our_words[other]) + '.'
                our_indexes = [oi, other]

            # compare combined_our to canonical token
            a = normalize_token(combined_our)
            b = normalize_token(canon_words[ci])
            # use both ratio and small edit distance as thumbs
            ratio = difflib.SequenceMatcher(None, a, b).ratio()
            dist = levenshtein(a.replace('.', ''), b.replace('.', ''))
            # require a fairly strong match for one-to-many merges as well: either containment
            # with similar length, or a high ratio, or a very small edit distance. Containment
            # alone (where the combined is much longer) will not trigger a merge.
            ratio_min_for_one_to_many = max(ratio_threshold, 0.9)
            a_norm = a.replace('.', '')
            b_norm = b.replace('.', '')
            length_similar_om = abs(len(a_norm) - len(b_norm)) <= 3
            containment_om = (a_norm in b_norm or b_norm in a_norm) and length_similar_om
            if containment_om or ratio >= ratio_min_for_one_to_many or dist <= 2:
                matches.append({
                    'canon_index': ci,
                    'our_indexes': our_indexes,
                    'canon_word': canon_words[ci],
                    'our_word': combined_our,
                    'relation': 'one-to-many (merged)',
                    'matched': True
                })
                used_our_for_merge.update(our_indexes)

    # Sort matches by canon_index (None last) and then our_index to keep output stable
    def sort_key(item):
        # merged entries may use 'canon_indexes' or 'our_indexes' or single indices; normalize key
        canon_key = item.get('canon_index')
        if canon_key is None and 'canon_indexes' in item:
            canon_key = item['canon_indexes'][0] if item['canon_indexes'] else None
        our_key = item.get('our_index')
        if our_key is None and 'our_indexes' in item:
            our_key = item['our_indexes'][0] if item['our_indexes'] else None
        return (canon_key if canon_key is not None else float('inf'), our_key if our_key is not None else float('inf'))

    matches.sort(key=sort_key)
    return matches


def match_stanzas(canon_path, our_path, out_path=None, limit=None, window=3, ratio_threshold=0.68, max_canon_span=3):
    # Parse with a forgiving parser if needed (handles duplicate IDs and minor malformations)
    try:
        canon_tree = etree.parse(canon_path)
    except etree.XMLSyntaxError:
        parser = etree.XMLParser(recover=True, remove_blank_text=True, huge_tree=True)
        canon_tree = etree.parse(canon_path, parser=parser)

    try:
        our_tree = etree.parse(our_path)
    except etree.XMLSyntaxError:
        parser = etree.XMLParser(recover=True, remove_blank_text=True, huge_tree=True)
        our_tree = etree.parse(our_path, parser=parser)

    canon_divs = extract_divs_by_id(canon_tree)
    our_divs = extract_divs_by_id(our_tree)

    results = []
    count = 0
    for xml_id, our_div in our_divs.items():
        if limit and count >= limit:
            break
        canon_div = canon_divs.get(xml_id)
        if canon_div is None:
            # skip if not found
            continue
        canon_words = extract_words_from_div(canon_div, insert_space_after_period=False)
        our_words = extract_words_from_div(our_div, insert_space_after_period=True)
        alignment = align_word_sequences(canon_words, our_words, window=window, ratio_threshold=ratio_threshold, max_canon_span=max_canon_span)
        results.append({
            'xml_id': xml_id,
            'canon_word_count': len(canon_words),
            'our_word_count': len(our_words),
            'alignment': alignment
        })
        count += 1

    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    return results


def main():
    parser = argparse.ArgumentParser(description='Match stanza-level xml:id and align words between two Yasna XMLs')
    # make positional args optional; if omitted, try to use config values
    parser.add_argument('canonical', nargs='?', help='Path to canonical Yasna XML')
    parser.add_argument('ours', nargs='?', help='Path to our Yasna XML to align')
    parser.add_argument('--out', help='Output JSON path', default='res/stanza_word_matches.json')
    parser.add_argument('--limit', type=int, help='Limit number of stanzas to process', default=None)
    parser.add_argument('--ratio', type=float, help='Similarity ratio threshold for accepting matches', default=0.68)
    parser.add_argument('--window', type=int, help='Local search window size (in canonical tokens)', default=3)
    parser.add_argument('--max-canon-span', type=int, help='Max number of canonical tokens to try concatenating (many-to-one)', default=3)
    args = parser.parse_args()

    canonical = args.canonical
    ours = args.ours

    # If either path is missing, try to pull defaults from config
    if canonical is None or ours is None:
        try:
            from src.interfaces.xml_translator import config as xt_config
        except Exception:
            xt_config = None

        # Resolve canonical: prefer explicit, then config CAB_XML_PATH, then data/Yasna_Static.xml
        if canonical is None:
            if xt_config and hasattr(xt_config, 'CAB_XML_PATH'):
                canonical = xt_config.CAB_XML_PATH
                if not os.path.isabs(canonical):
                    canonical = os.path.normpath(os.path.join(os.getcwd(), canonical))
            # fallback candidate
            if (not canonical or not os.path.exists(canonical)):
                alt = os.path.join(os.getcwd(), 'data', 'Yasna_Static.xml')
                if os.path.exists(alt):
                    canonical = alt

        # Resolve ours: prefer explicit, then a single xml inside OCR_XML_DIR, then data/Yasna_Static.xml
        if ours is None:
            found = None
            if xt_config and hasattr(xt_config, 'OCR_XML_DIR'):
                od = xt_config.OCR_XML_DIR
                od_path = od if os.path.isabs(od) else os.path.normpath(os.path.join(os.getcwd(), od))
                if os.path.isdir(od_path):
                    for fname in os.listdir(od_path):
                        if fname.lower().endswith('.xml'):
                            found = os.path.join(od_path, fname)
                            break
                elif os.path.isfile(od_path):
                    found = od_path
            if found:
                ours = found
            else:
                alt = os.path.join(os.getcwd(), 'data', 'Yasna_Static.xml')
                if os.path.exists(alt):
                    ours = alt

    if not canonical or not os.path.exists(canonical):
        raise SystemExit(f'Canonical XML not found; provide path or set CAB_XML_PATH in config. Tried: {canonical}')
    if not ours or not os.path.exists(ours):
        raise SystemExit(f'Our XML not found; provide path or set OCR_XML_DIR in config. Tried: {ours}')

    results = match_stanzas(canonical, ours, args.out, args.limit, window=args.window, ratio_threshold=args.ratio, max_canon_span=args.max_canon_span)
    print(f'Wrote {len(results)} stanza alignments to {args.out}')


if __name__ == '__main__':
    main()
