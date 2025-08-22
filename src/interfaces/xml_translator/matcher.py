import os
import re
import nltk
import json
from pprint import pprint

from src.cab.cab_xml import CABXML
from src.escriptorium.ocr_xml import OCRXML
from src.xml_translator.config import (
    CAB_XML_PATH,
    OCR_XML_DIR,
    MATCH_JSON_PATH,
)

import sys
sys.setrecursionlimit(sys.getrecursionlimit()*30)


def main():
    cab_text = CABXML(CAB_XML_PATH)
    ocr_text = OCRXML(OCR_XML_DIR)

    cab_index, ocr_index = 0, 0
    while True:
        if check_strong_match(cab_text, ocr_text, cab_index, ocr_index):
            end_cab_index, end_ocr_index, matches, _ = recursive_match(cab_text, ocr_text, cab_index, ocr_index, 0)
            print(f"Matched OCR: {ocr_index} to {end_ocr_index} with CAB: {cab_index} to {end_cab_index}")

            matches = [
                {'cab_ind': match[0], 'ocr_ind': match[1]}
                for match in matches
            ]

            os.makedirs(os.path.dirname(MATCH_JSON_PATH), exist_ok=True)
            with open(MATCH_JSON_PATH, "w") as f:
                f.write(json.dumps(matches))
            return

        cab_index += 1

memo = {}
def recursive_match(cab_text, ocr_text, cab_index, ocr_index, error_counter):
    if (cab_index, ocr_index, error_counter) in memo:
        return memo[(cab_index, ocr_index, error_counter)]

    print(cab_index, ocr_index)
    if cab_index >= len(cab_text) or ocr_index >= len(ocr_text) or error_counter > 15:
        memo[(cab_index, ocr_index, error_counter)] = [cab_index, ocr_index, [], error_counter]
        return memo[(cab_index, ocr_index, error_counter)]

    if cab_text[cab_index].word in ['W', 'Y']:
        memo[(cab_index, ocr_index, error_counter)] = recursive_match(cab_text, ocr_text, cab_index+1, ocr_index, error_counter)
        # memo[(cab_index, ocr_index, error_counter)][3] += error_counter
        memo[(cab_index, ocr_index, error_counter)][3] += 1
        return memo[(cab_index, ocr_index, error_counter)]
    if ocr_text[ocr_index].word in ['W', 'Y']:
        memo[(cab_index, ocr_index, error_counter)] = recursive_match(cab_text, ocr_text, cab_index, ocr_index+1, error_counter)
        # memo[(cab_index, ocr_index, error_counter)][3] += error_counter
        memo[(cab_index, ocr_index, error_counter)][3] += 1
        return memo[(cab_index, ocr_index, error_counter)]

    best = (cab_index, ocr_index, [], float('inf'))
    if single_match(cab_text[cab_index].word, ocr_text[ocr_index].word):
        memo_val = recursive_match(cab_text, ocr_text, cab_index+1, ocr_index+1, 0)
        # best = [memo_val[0], memo_val[1], [(cab_index, ocr_index)] + memo_val[2], memo_val[3] + error_counter]
        best = [memo_val[0], memo_val[1], [(cab_index, ocr_index)] + memo_val[2], memo_val[3] + 1]
    for i in range(1, 11):
        candidate = recursive_match(cab_text, ocr_text, cab_index, ocr_index+i, error_counter+i)
        candidate[3] += 1
        # candidate[3] += error_counter
        if (len(candidate[2]), -candidate[3]) > (len(best[2]), -best[3]):
            best = candidate
    for i in range(1, 11):
        candidate = recursive_match(cab_text, ocr_text, cab_index + i, ocr_index, error_counter + i)
        # candidate[3] += error_counter
        candidate[3] += 1
        if (len(candidate[2]), -candidate[3]) > (len(best[2]), -best[3]):
            best = candidate
    memo[(cab_index, ocr_index, error_counter)] = best
    return memo[(cab_index, ocr_index, error_counter)]


def check_strong_match(cab_text, ocr_text, cab_index, ocr_index, k=3):
    for i in range(k):
        cab_word = cab_text[cab_index + i]
        ocr_word = ocr_text[ocr_index + i]
        if not single_match(cab_word.word, ocr_word.word):
            return False
        # if remove_vowels(cab_word) != remove_vowels(ocr_word):
        #     return False
    return True

def single_match(cab_word, ocr_word):
    if cab_word == '' or ocr_word == '':
        return False
    if cab_word == ocr_word:
        return True
    cab_word_without_vowels = remove_vowels(cab_word)
    ocr_word_without_vowels = remove_vowels(ocr_word)
    if cab_word_without_vowels == ocr_word_without_vowels:
        return True
    if nltk.edit_distance(cab_word_without_vowels, ocr_word_without_vowels) <= 1:
        return True
    return False

def remove_vowels(text):
    text = re.sub(r"[ą̇aeoāąēōūīəə̄ēyẏ\d]", '', text)
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
