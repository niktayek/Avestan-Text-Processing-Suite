import os
import re
import copy
import Levenshtein
from dataclasses import asdict, dataclass
from typing import List

from .config import OUTPUT_DIR, FOR_TEST
from .utils import memoize, write_csv
from src.interfaces.cab.cab_xml import CABXML
from src.interfaces.escriptorium.ocr_xml import OCRXML


# =========================
# INPUT / OUTPUT PATHS
# =========================
REFERENCE_FILES_PATH = [
    # 'data/CAB/static_dron.xml',
    # 'data/CAB/static_videvdad.xml',
    # 'data/CAB/static_vishtasp.xml',
    # 'data/CAB/static_visperad.xml',
    # 'data/CAB/static_visperad_dh.xml',
    'data/Yasna_Static.xml',
    # 'data/CAB/static_yasnar.xml',
    # 'data/CAB/Videvdad_Static.xml',
    # 'data/Canonical_Yasna.txt',  # TODO: support .txt input
]

# The manuscript (CAB) to match
TRANSLITERATION_FILE_PATH = "data/CAB/Yasna/0008_cleaned.xml"

# Output CSV
OUTPUT_FILE_PATH = os.path.join(OUTPUT_DIR, 'matches.csv')


# =========================
# CONFIGURATION KNOBS
# =========================
DISTANCE_THRESHOLD = 3
MERGE_THRESHOLD = 3               # usually 2 is enough once tokens are words
ENABLE_NORMALIZER = False
SORT_BY_DISTANCE = False          # if True -> ASC by distance at the very end
PROGRESS_EVERY = 200              # print progress every N tokens


# =========================
# TOKEN TYPES
# =========================
@dataclass
class WordToken:
    word: str
    address: List[object]  # list of underlying char-level addresses


# =========================
# DOTS / BOUNDARIES
# =========================
# Dot-like chars that may appear/disappear *inside* words
INNER_DOT_CHARS = ''.join([
    '.',        # U+002E period
    '\u00B7',   # · middle dot
    '\u2E33',   # ⸳ raised dot
])

# Hard punctuation that should block merges across boundaries
# (Note: '.' is *not* here; we treat it as potentially inside-word and handle separately)
HARD_PUNCT_END = re.compile(r'[?!,:;]+$')
HARD_PUNCT_BEG = re.compile(r'^[?!,:;]+')


def strip_inner_dots(s: str) -> str:
    """
    Remove INNER_DOT_CHARS everywhere EXCEPT we also drop a final dot-like char,
    since we're using this only for distance, not for boundary detection.
    """
    if not s:
        return s
    return s.translate({ord(c): None for c in INNER_DOT_CHARS})


def is_nonbreaking(addr) -> bool:
    """
    True if the boundary before 'addr' is explicitly non-breaking (e.g., <lb break="no"/>).
    Adjust flags to whatever your address object exposes.
    """
    try:
        for flag in ('lb_break_no', 'no_break', 'join_next', 'hyphen_join'):
            if getattr(addr, flag, False):
                return True
    except Exception:
        pass
    return False


def is_nonbreaking_between(addr_left, addr_right) -> bool:
    """
    Equivalent check but phrased as a boundary between two addresses.
    We look on the left; adapt if your address marks it on the right.
    """
    return is_nonbreaking(addr_left)


def same_ab(a, b) -> bool:
    """
    True if two addresses belong to the same <ab> region. Permissive fallback.
    """
    try:
        a_id = getattr(a, 'ab_id', None)
        b_id = getattr(b, 'ab_id', None)
        return (a_id is not None) and (a_id == b_id)
    except Exception:
        return True  # permissive if no info


# =========================
# NORMALIZATION (optional)
# =========================
@memoize()
def normalize(text: str) -> str:
    """
    Collapse variants to uniform forms for distance, if ENABLE_NORMALIZER.
    NOTE: Order matters; review before enabling.
    """
    uniform_list = [
        ('a', ['ą', 'ą̇', 'å', 'ā']),
        ('ae', ['aē']),
        ('o', ['ō']),
        ('e', ["i"]),
        ('i', ['\.']),
        ('ao', ['aō']),
        ('uu', ['ū', 'ī', 'ii']),
        ('ŋ', ['ŋ́', 'ŋᵛ']),
        ('s', ['š', 'š́', 'ṣ', 'ṣ̌']),
        ('mh', ['m̨']),
        ('x', ['x́', 'x́', 'xᵛ']),  # x́ repeated intentionally per original rules
        ('n', ['ń', 'ṇ']),
        ('ī', ['ū']),
        ('ϑ', ['t']),
        ('d', ['δ']),
    ]
    for uniform, variants in uniform_list:
        for char in variants:
            text = re.sub(char, uniform, text)
    return text


def distance_with_dot_tolerance(candidate: str, reference: str) -> int:
    """
    Edit distance that tolerates mid-word dot differences:
    min(distance(raw), distance(dot-stripped)).
    Apply normalization first if enabled.
    """
    if ENABLE_NORMALIZER:
        cand_n = normalize(candidate)
        ref_n = normalize(reference)
        d1 = Levenshtein.distance(cand_n, ref_n)
        d2 = Levenshtein.distance(strip_inner_dots(cand_n), strip_inner_dots(ref_n))
    else:
        d1 = Levenshtein.distance(candidate, reference)
        d2 = Levenshtein.distance(strip_inner_dots(candidate), strip_inner_dots(reference))
    return min(d1, d2)


# =========================
# CHAR -> WORD RETOKENIZATION
# =========================
HARD_PUNCT_SET = set(['?', '!', ',', ':', ';'])
DOT_LIKE_SET   = set(INNER_DOT_CHARS)


def group_chars_into_words(char_tokens) -> List[WordToken]:
    """
    Collapse char-level CAB tokens into word tokens:
    - merge across <lb break="no"/>
    - keep mid-word dots if present (they become part of the word object)
    - break on spaces, hard punctuation, or <ab> changes
    """
    words: List[WordToken] = []
    buf_chars: List[str] = []
    buf_addrs: List[object] = []

    def flush():
        if buf_chars:
            words.append(WordToken(''.join(buf_chars), list(buf_addrs)))
            buf_chars.clear()
            buf_addrs.clear()

    prev_addr = None

    for t in char_tokens:
        ch = getattr(t, 'word', '')
        addr = getattr(t, 'address', None)

        # If explicit spaces exist in the stream (rare in CAB), break word
        if ch == ' ':
            flush()
            prev_addr = addr
            continue

        # Break on <ab> boundary
        if prev_addr is not None and not same_ab(prev_addr, addr):
            flush()

        start_new = False

        if not buf_chars:
            # starting a new word
            pass
        else:
            # If previous boundary explicitly non-breaking, always allow
            if is_nonbreaking(prev_addr):
                pass
            else:
                # If previous char ended with "hard" punctuation, break
                if buf_chars and buf_chars[-1] in HARD_PUNCT_SET:
                    start_new = True
                # Dot-like chars are allowed *inside* words, so we do not force a break here

        if start_new:
            flush()

        buf_chars.append(ch)
        buf_addrs.append(addr)
        prev_addr = addr

    flush()
    return words


# =========================
# I/O HELPERS
# =========================
def create_dictionary(reference_files_path):
    words = []
    for file_path in reference_files_path:
        cab = CABXML(file_path)
        # CABXML may already be word-level for canonicals; if not, group
        # Try to detect single-char tokens by sampling a few
        sample = []
        for k, item in enumerate(cab):
            w = getattr(item, 'word', '')
            if w:
                sample.append(w)
            if k >= 50:
                break
        if sample and all(len(w) == 1 for w in sample):
            # re-iterate fully (fresh iterator) and group to words
            cab_full = CABXML(file_path)
            word_tokens = group_chars_into_words(cab_full)
            words += [wt.word for wt in word_tokens if wt.word]
        else:
            # likely already word-level
            # need to re-open because we consumed up to 51 items
            cab_full = CABXML(file_path)
            words += [item.word for item in cab_full if getattr(item, 'word', None)]
    return set(words)


def read_ocr_words(ocr_file_path) -> List[WordToken]:
    # If your OCRXML yields words, you could just return OCRXML(ocr_file_path)
    # For symmetry, we group if it is char-level.
    ocr = OCRXML(ocr_file_path)
    sample = []
    for k, item in enumerate(ocr):
        w = getattr(item, 'word', '')
        if w:
            sample.append(w)
        if k >= 50:
            break
    if sample and all(len(w) == 1 for w in sample):
        # char-level -> group to words
        ocr_full = OCRXML(ocr_file_path)
        return group_chars_into_words(ocr_full)
    else:
        # already word-level -> wrap into WordToken with a single address list
        ocr_full = OCRXML(ocr_file_path)
        out: List[WordToken] = []
        for it in ocr_full:
            w = getattr(it, 'word', '')
            if not w:
                continue
            out.append(WordToken(w, [getattr(it, 'address', None)]))
        return out


def read_cab_words(file_path) -> List[WordToken]:
    # CABXML often yields char-level for manuscripts -> group to words
    cab = CABXML(file_path)
    sample = []
    for k, item in enumerate(cab):
        w = getattr(item, 'word', '')
        if w:
            sample.append(w)
        if k >= 50:
            break
    if sample and all(len(w) == 1 for w in sample):
        cab_full = CABXML(file_path)
        return group_chars_into_words(cab_full)
    else:
        cab_full = CABXML(file_path)
        out: List[WordToken] = []
        for it in cab_full:
            w = getattr(it, 'word', '')
            if not w:
                continue
            out.append(WordToken(w, [getattr(it, 'address', None)]))
        return out


# =========================
# MATCHING
# =========================
def boundary_type(tokens: List[WordToken], j: int, j1: int) -> str:
    """
    Boundary class between tokens[j] and tokens[j1]:
      - 'NONBREAK' : explicit non-breaking boundary (e.g., <lb break="no"/>)
      - 'SOFT_DOT' : left token ends with a dot-like char
      - 'HARD'     : hard punctuation or different <ab>; do not merge
      - 'NORMAL'   : ordinary boundary (allow merge if helpful)
    """
    a, b = tokens[j].address[-1], tokens[j1].address[0]  # use edge addresses

    if is_nonbreaking_between(a, b):
        return 'NONBREAK'

    if not same_ab(a, b):
        return 'HARD'

    left_word = tokens[j].word or ''
    right_word = tokens[j1].word or ''

    if left_word and left_word[-1] in DOT_LIKE_SET:
        return 'SOFT_DOT'

    if HARD_PUNCT_END.search(left_word) or HARD_PUNCT_BEG.search(right_word):
        return 'HARD'

    return 'NORMAL'


def distance_maybe_normalized(cand: str, ref: str) -> int:
    return distance_with_dot_tolerance(cand, ref)


@memoize(memoize_for_args=['transliterated_word'])
def find_match(transliterated_word: str, reference_dictionary: set[str]):
    # Fast path
    if transliterated_word in reference_dictionary:
        return {'transliterated': transliterated_word, 'reference': transliterated_word, 'distance': 0}

    matched = []
    tlen = len(transliterated_word)
    # Cheap length band (±1 extra for dot stripping differences)
    max_len_delta = DISTANCE_THRESHOLD + 1

    for ref in reference_dictionary:
        if abs(len(ref) - tlen) > max_len_delta:
            continue
        d = distance_maybe_normalized(transliterated_word, ref)
        if d <= DISTANCE_THRESHOLD:
            matched.append({'reference': ref, 'distance': d})

    if not matched:
        return {'transliterated': transliterated_word, 'reference': '', 'distance': 1000}

    matched.sort(key=lambda x: x['distance'])
    best = matched[0]
    return {'transliterated': transliterated_word, 'reference': best['reference'], 'distance': best['distance']}


def match_words(transliterated_words: List[WordToken], reference_dictionary: set[str]):
    matches = []
    cur_ind = 0
    total = len(transliterated_words)

    while cur_ind < total:
        if PROGRESS_EVERY and (cur_ind % PROGRESS_EVERY == 0):
            print(f"matching word {cur_ind}/{total}: {transliterated_words[cur_ind].word}")

        possible = []

        for i in range(1, MERGE_THRESHOLD + 1):
            max_ind = min(cur_ind + i, total)

            # Inspect boundaries inside this merged span
            worst = 'NONBREAK'  # severity: HARD > SOFT_DOT > NORMAL > NONBREAK
            can_merge = True
            for j in range(cur_ind, max_ind - 1):
                bt = boundary_type(transliterated_words, j, j + 1)
                if bt == 'HARD':
                    can_merge = False
                    break
                if bt == 'SOFT_DOT' and worst in ('NONBREAK', 'NORMAL'):
                    worst = 'SOFT_DOT'
                elif bt == 'NORMAL' and worst == 'NONBREAK':
                    worst = 'NORMAL'
            if not can_merge:
                break  # further merges would cross the same HARD boundary

            # Build candidate string & addresses
            cand = ''.join(transliterated_words[j].word for j in range(cur_ind, max_ind))
            addr = []
            for j in range(cur_ind, max_ind):
                addr.extend(transliterated_words[j].address)

            m = copy.deepcopy(find_match(cand, reference_dictionary))
            m['address'] = addr
            # helper keys for sorting (stripped before CSV)
            m['merge_len'] = (max_ind - cur_ind)
            m['ref_len']   = len(m['reference'])
            m['is_exact']  = int(m['distance'] == 0)
            m['bt']        = worst
            possible.append(m)

        if not possible:
            # Fallback single-token miss (shouldn’t happen)
            tok = transliterated_words[cur_ind]
            possible = [{
                'transliterated': tok.word,
                'reference': '',
                'distance': 1000,
                'address': tok.address,
                'merge_len': 1,
                'ref_len': 0,
                'is_exact': 0,
                'bt': 'HARD',
            }]

        # For dot-merge penalty, compare to the single-token candidate
        one_tok = next((m for m in possible if m['merge_len'] == 1), None)
        one_d = one_tok['distance'] if one_tok else 9999

        def soft_dot_penalty(m):
            # Penalize taking a multi-token merge across a dot unless it's strictly better
            if m['bt'] == 'SOFT_DOT' and m['merge_len'] > 1 and not m['is_exact'] and m['distance'] >= one_d:
                return 1
            return 0

        possible.sort(
            key=lambda m: (
                m['distance'] > 0,   # exact first
                soft_dot_penalty(m), # discourage bad dot merges
                m['merge_len'],      # prefer fewer tokens
                m['distance'],       # then actual distance
                -m['ref_len'],       # tie-break on longer reference
            )
        )

        best = possible[0]
        matches.append(best)
        cur_ind += best['merge_len']

    return matches


# =========================
# MAIN
# =========================
def main():
    reference_dictionary = create_dictionary(REFERENCE_FILES_PATH)

    # Use CAB (manuscript) reader by default; groups chars -> words automatically
    transliterated_words = read_cab_words(TRANSLITERATION_FILE_PATH)

    # Only truncate if FOR_TEST=True (set in your .config)
    if FOR_TEST:
        transliterated_words = transliterated_words[:100]

    matches = match_words(transliterated_words, reference_dictionary)

    if SORT_BY_DISTANCE:
        matches = sorted(matches, key=lambda x: x['distance'])

    # Strip helper keys and convert addresses to dicts for CSV
    for m in matches:
        m['address'] = [asdict(a) if hasattr(a, '__dataclass_fields__') else (a.__dict__ if hasattr(a, '__dict__') else a)
                        for a in m['address']]
        for k in ('merge_len', 'ref_len', 'is_exact', 'bt'):
            if k in m:
                del m[k]

    write_csv(matches, OUTPUT_FILE_PATH)


if __name__ == '__main__':
    main()