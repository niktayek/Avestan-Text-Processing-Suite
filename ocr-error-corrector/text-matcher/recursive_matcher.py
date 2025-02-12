import re
import json
import nltk

import sys
sys.setrecursionlimit(sys.getrecursionlimit()*10)

from data_loader import load_ocr_words, load_manual_words
import config


def match():
    manual_words = load_manual_words()
    ocr_words = load_ocr_words()

    end_manual_index, end_ocr_index, matches, _ = recursive_match(manual_words, ocr_words, 0, 0, 0)
    print(f"Matched {len(matches)} words")
    print(f"OCR: 0 to {end_ocr_index} with manual: 0 to {end_manual_index}")
    with open("res/matches.json", "w") as f:
        f.write(json.dumps(matches))
    return


memo = {}
def recursive_match(manual_words, ocr_words, manual_index, ocr_index, error_counter):
    if (manual_index, ocr_index, error_counter) in memo:
        return memo[(manual_index, ocr_index, error_counter)]

    print(manual_index, ocr_index)
    if manual_index >= len(manual_words) or ocr_index >= len(ocr_words) or error_counter > config.ERROR_THRESHOLD:
        memo[(manual_index, ocr_index, error_counter)] = [manual_index, ocr_index, [], error_counter]
        return memo[(manual_index, ocr_index, error_counter)]

    if config.LANGUAGE == 'avestan':
        if manual_words[manual_index][1] in config.AVESTAN_MANUAL_IGNORE_LIST:
            memo[(manual_index, ocr_index, error_counter)] = recursive_match(manual_words, ocr_words, manual_index + 1, ocr_index, error_counter)
            memo[(manual_index, ocr_index, error_counter)][3] += calculate_error_counter(error_counter)
            return memo[(manual_index, ocr_index, error_counter)]
        if ocr_words[ocr_index][1] in config.AVESTAN_OCR_IGNORE_LIST:
            memo[(manual_index, ocr_index, error_counter)] = recursive_match(manual_words, ocr_words, manual_index, ocr_index + 1, error_counter)
            memo[(manual_index, ocr_index, error_counter)][3] += calculate_error_counter(error_counter)
            return memo[(manual_index, ocr_index, error_counter)]

    best = (manual_index, ocr_index, [], float('inf'))
    if single_match(manual_words[manual_index], ocr_words[ocr_index]):
        memo_val = recursive_match(manual_words, ocr_words, manual_index + 1, ocr_index + 1, 0)
        best = [
            memo_val[0],
            memo_val[1],
            [(
                (manual_index, manual_index + 1),
                (ocr_index, ocr_index + 1)
            )] + memo_val[2],
            memo_val[3] + calculate_error_counter(error_counter),
        ]

    for i in range(2, config.MERGE_THRESHOLD):
        if not single_match(manual_words[manual_index], ''.join(ocr_words[ocr_index:ocr_index + i])):
            continue

        candidate = recursive_match(manual_words, ocr_words, manual_index + 1, ocr_index + i, 0)
        candidate[3] += calculate_error_counter(error_counter)
        if (len(candidate[2]) + 1, -candidate[3]) > (len(best[2]), -best[3]):
            best = [
                candidate[0],
                candidate[1],
                [(
                    (manual_index, manual_index + 1),
                    (ocr_index, ocr_index + i),
                )] + candidate[2],
                candidate[3],
            ]

    for i in range(2, config.MERGE_THRESHOLD):
        if not single_match(''.join(manual_words[manual_index:manual_index + i]), ocr_words[ocr_index]):
            continue

        candidate = recursive_match(manual_words, ocr_words, manual_index + i, ocr_index + 1, 0)
        candidate[3] += calculate_error_counter(error_counter)
        if (len(candidate[2]) + 1, -candidate[3]) > (len(best[2]), -best[3]):
            best = [
                candidate[0],
                candidate[1],
                [(
                    (manual_index, manual_index + i),
                    (ocr_index, ocr_index + 1),
                )] + candidate[2],
                candidate[3],
            ]

    for i in range(1, config.SKIP_THRESHOLD):
        candidate = recursive_match(manual_words, ocr_words, manual_index, ocr_index + i, error_counter + i)
        candidate[3] += calculate_error_counter(error_counter)
        if (len(candidate[2]), -candidate[3]) > (len(best[2]), -best[3]):
            best = candidate
    for i in range(1, config.SKIP_THRESHOLD):
        candidate = recursive_match(manual_words, ocr_words, manual_index + i, ocr_index, error_counter + i)
        candidate[3] += calculate_error_counter(error_counter)
        if (len(candidate[2]), -candidate[3]) > (len(best[2]), -best[3]):
            best = candidate

    memo[(manual_index, ocr_index, error_counter)] = best
    return memo[(manual_index, ocr_index, error_counter)]


def single_match(manual_word, ocr_word):
    if manual_word == '' or ocr_word == '':
        return False

    if config.LANGUAGE == 'avestan':
        manual_word = remove_vowels_for_avestan(manual_word)
        ocr_word = remove_vowels_for_avestan(ocr_word)

    if manual_word == ocr_word:
        return True
    if nltk.edit_distance(manual_word, ocr_word) <= config.DISTANCE_THRESHOLD:
        return True
    return False

def calculate_error_counter(error_counter):
    if config.ERROR_ACCUMULATION_METHOD == 'linear':
        return error_counter
    if config.ERROR_ACCUMULATION_METHOD == 'constant':
        return 1

def remove_vowels_for_avestan(text):
    text = re.sub(r"[ą̇aeoāąēōūīəə̄ēyẏ\.\d]", '', text)
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


if __name__ == "__main__":
    match()
