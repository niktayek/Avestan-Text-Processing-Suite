import re
import json
import nltk

import sys
sys.setrecursionlimit(sys.getrecursionlimit()*10)

from data_loader import load_ocr_words, load_manual_words


def main():
    manual_words = load_manual_words()
    ocr_words = load_ocr_words()

    # print('manual\t', len(manual_words))
    # print('ocr\t', len(ocr_words))
    # return

    manual_index, ocr_index = 0, 0
    end_manual_index, end_ocr_index, matches, _ = recursive_match(manual_words, ocr_words, manual_index, ocr_index, 0)
    print(f"Matched OCR: {ocr_index} to {end_ocr_index} with manual: {manual_index} to {end_manual_index}")
    with open("res/matches.json", "w") as f:
        f.write(json.dumps(matches))
    return


memo = {}
def recursive_match(manual_words, ocr_words, manual_index, ocr_index, error_counter):
    if (manual_index, ocr_index, error_counter) in memo:
        return memo[(manual_index, ocr_index, error_counter)]

    print(manual_index, ocr_index)
    if manual_index >= len(manual_words) or ocr_index >= len(ocr_words) or error_counter > 10:
        memo[(manual_index, ocr_index, error_counter)] = [manual_index, ocr_index, [], error_counter]
        return memo[(manual_index, ocr_index, error_counter)]

    if manual_words[manual_index] in ['W', 'Y']:
        memo[(manual_index, ocr_index, error_counter)] = recursive_match(manual_words, ocr_words, manual_index+1, ocr_index, error_counter)
        memo[(manual_index, ocr_index, error_counter)][3] += error_counter
        return memo[(manual_index, ocr_index, error_counter)]
    if ocr_words[ocr_index] in ['W', 'Y']:
        memo[(manual_index, ocr_index, error_counter)] = recursive_match(manual_words, ocr_words, manual_index, ocr_index+1, error_counter)
        memo[(manual_index, ocr_index, error_counter)][3] += error_counter
        return memo[(manual_index, ocr_index, error_counter)]

    best = (manual_index, ocr_index, [], float('inf'))
    if single_match(manual_words[manual_index], ocr_words[ocr_index]):
        memo_val = recursive_match(manual_words, ocr_words, manual_index+1, ocr_index+1, 0)
        best = [memo_val[0], memo_val[1], [(manual_index, ocr_index)] + memo_val[2], memo_val[3] + error_counter]
    for i in range(1, 5):
        candidate = recursive_match(manual_words, ocr_words, manual_index, ocr_index+i, error_counter+i)
        candidate[3] += error_counter
        if (len(candidate[2]), -candidate[3]) > (len(best[2]), -best[3]):
            best = candidate
    for i in range(1, 5):
        candidate = recursive_match(manual_words, ocr_words, manual_index + i, ocr_index, error_counter + i)
        candidate[3] += error_counter
        if (len(candidate[2]), -candidate[3]) > (len(best[2]), -best[3]):
            best = candidate
    memo[(manual_index, ocr_index, error_counter)] = best
    return memo[(manual_index, ocr_index, error_counter)]


def single_match(manual_word, ocr_word):
    if manual_word == '' or ocr_word == '':
        return False
    if manual_word == ocr_word:
        return True
    # manual_word_without_vowels = remove_vowels(manual_word)  # only for Avestan
    # ocr_word_without_vowels = remove_vowels(ocr_word)  # only for Avestan
    if manual_word == ocr_word:
        return True
    if nltk.edit_distance(manual_word, ocr_word) <= 1:
        return True
    return False

def remove_vowels_avestan(text):
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
    main()
