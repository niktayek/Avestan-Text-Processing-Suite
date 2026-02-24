import re
import unicodedata
from typing import List

# SPECIAL_GRAPHEMES adapted from existing Avestan tokenizers in the repo
SPECIAL_GRAPHEMES: List[str] = [
    'ə̄u', 'aō', 'aē', 'āu', 'āi', 'ōi', 'ou', 'ai', 'au',
    'ā̊', 'ą̇', 'ə̄', 't̰', 'x́', 'xᵛ', 'ŋ́', 'ŋᵛ', 'š́', 'ṣ̌', 'ṇ', 'ń', 'ɱ', 'ġ', 'γ', 'δ', 'ẏ', 'č', 'ž', 'β',
    'ā', 'ą', 'ō', 'ē', 'ū', 'ī',
    'a', 'o', 'ə', 'e', 'u', 'i',
    'k', 'x', 'g', 'c', 'j', 't', 'ϑ', 'd', 'p', 'b', 'ŋ', 'n', 'm',
    'y', 'v', 'r', 'l', 's', 'z', 'š', 'h', 'uu', 'ii'
]
SPECIAL_GRAPHEMES.sort(key=len, reverse=True)
SPECIAL_GRAPHEME_RE = re.compile('|'.join(map(re.escape, SPECIAL_GRAPHEMES)))

# Equivalence map for comparison/canonicalization only (not written back to TEI)
EQUIV_MAP = {
    # diphthongs & vowels
    'ae': 'aē', 'aē': 'aē', 'ao': 'aō', 'aō': 'aō',
    'ou': 'ō',  'ō': 'ō',
    'ii': 'ī',  'ī': 'ī', 'uu': 'ū', 'ū': 'ū',
    # sibilants cluster to š
    'ṣ̌': 'š', 'ś': 'š', 'ṣ': 'š', 'š́': 'š', 'š': 'š', 'š': 'š',
    # nasals
    'ṇ': 'n', 'ń': 'n', 'ŋ': 'ŋ', 'ŋ́': 'ŋ', 'ŋᵛ': 'ŋ',
    # fricatives
    'ϑ': 't',
}

DECORATIVE_PUNCT_RE = re.compile(r"[\.,;:·⸳]+$")
WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(s: str) -> str:
    """NFC normalize, collapse spaces, trim."""
    s = unicodedata.normalize('NFC', str(s))
    s = WHITESPACE_RE.sub(' ', s).strip()
    return s


def strip_decorative_punct(s: str) -> str:
    s = normalize_text(s)
    return DECORATIVE_PUNCT_RE.sub('', s)


def strip_combining(s: str) -> str:
    """Remove combining marks for comparison-only checks."""
    nfd = unicodedata.normalize('NFD', s)
    base = ''.join(ch for ch in nfd if unicodedata.category(ch) != 'Mn')
    return unicodedata.normalize('NFC', base)


def tokenize_graphemes(word: str) -> List[str]:
    word = normalize_text(word)
    tokens: List[str] = []
    i = 0
    while i < len(word):
        m = SPECIAL_GRAPHEME_RE.match(word, i)
        if m:
            tokens.append(m.group())
            i = m.end()
        else:
            tokens.append(word[i])
            i += 1
    return tokens


def canonical_feature(s: str) -> str:
    """Convert 'A for B' to 'A→B'; keep 'A→B' as-is; trim and NFC."""
    s = normalize_text(s)
    if '→' in s:
        left, right = s.split('→', 1)
        return f"{left.strip()}→{right.strip()}"
    if ' for ' in s:
        left, right = s.split(' for ', 1)
        return f"{left.strip()}→{right.strip()}"
    return s


def _equiv_token(tok: str) -> str:
    return EQUIV_MAP.get(tok, tok)


def canonicalize_token_for_feature(tok: str) -> str:
    """Map a grapheme to an equivalence representative for feature key construction."""
    return _equiv_token(tok)


def is_avestan_token(t: str) -> bool:
    """Heuristic: token contains at least one letter-like char from transliteration set."""
    t = normalize_text(t)
    # If tokenizer can match any SPECIAL_GRAPHEME, consider it avestan
    return any(SPECIAL_GRAPHEME_RE.match(t, i) for i in range(len(t))) or any(ch.isalpha() for ch in t)
