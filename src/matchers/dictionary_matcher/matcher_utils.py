import re
import sys
sys.setrecursionlimit(10000)

def remove_vowels_for_avestan(text):
    text = re.sub(r"[ą̇aeoāąēōūīəə̄ēyẏ.\\d]", '', text)
    text = re.sub(r'([^u])u([^u])', r"\1\2", text)
    text = re.sub(r'([^i])i([^i])', r"\1\2", text)
    uniform_list = [
        ('ŋ', ['ŋ́', 'ŋᵛ']),
        ('s', ['š', 'š́', 'ṣ']),
        ('mh', ['m̨']),
        ('x', ['θ', 'x́']),
        ('y', ['ẏ']),
        ('n', ['ń']),
        ('x́', ['xᵛ']),
        ('t', ['δ', 't', 't̰']),
        ('y', ['ẏ'])
    ]
    for uniform in uniform_list:
        for char in uniform[1]:
            text = re.sub(char, uniform[0], text)
    return text

def normalize_token(token):
    return remove_vowels_for_avestan(token)

def single_match(manual_word, ocr_word):
    if manual_word == '' or ocr_word == '':
        return False
    mw = normalize_token(manual_word)
    ow = normalize_token(ocr_word)
    return mw == ow or edit_distance(mw, ow) <= 1

def edit_distance(a, b):
    if a == b:
        return 0
    if len(a) < len(b):
        return edit_distance(b, a)
    if len(b) == 0:
        return len(a)
    previous_row = range(len(b) + 1)
    for i, c1 in enumerate(a):
        current_row = [i + 1]
        for j, c2 in enumerate(b):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def recursive_match(manual_words, ocr_words, merge_threshold=3, skip_threshold=2):
    memo = {}

    def _match(m, o):
        if (m, o) in memo:
            return memo[(m, o)]

        if m >= len(manual_words) or o >= len(ocr_words):
            return 0, []

        best_score, best_path = 0, []

        # Direct match
        if single_match(manual_words[m], ocr_words[o]):
            score, path = _match(m + 1, o + 1)
            score += 1
            if score > best_score:
                best_score, best_path = score, [(m, o)] + path

        # Merge OCR tokens
        for i in range(2, merge_threshold):
            if o + i > len(ocr_words):
                break
            if single_match(manual_words[m], ''.join(ocr_words[o:o + i])):
                score, path = _match(m + 1, o + i)
                score += 1
                if score > best_score:
                    best_score, best_path = score, [(m, (o, o + i))] + path

        # Merge manual tokens
        for i in range(2, merge_threshold):
            if m + i > len(manual_words):
                break
            if single_match(''.join(manual_words[m:m + i]), ocr_words[o]):
                score, path = _match(m + i, o + 1)
                score += 1
                if score > best_score:
                    best_score, best_path = score, [((m, m + i), o)] + path

        # Skip OCR tokens
        for i in range(1, skip_threshold):
            if o + i < len(ocr_words):
                score, path = _match(m, o + i)
                if score > best_score:
                    best_score, best_path = score, path

        # Skip manual tokens
        for i in range(1, skip_threshold):
            if m + i < len(manual_words):
                score, path = _match(m + i, o)
                if score > best_score:
                    best_score, best_path = score, path

        memo[(m, o)] = (best_score, best_path)
        return memo[(m, o)]

    score, path = _match(0, 0)
    denom = max(len(manual_words), len(ocr_words))
    return score / denom if denom > 0 else 0.0
