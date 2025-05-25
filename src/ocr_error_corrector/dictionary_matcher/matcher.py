import json
import re
import copy
import Levenshtein
from dataclasses import asdict
from src.cab.cab_xml import CABXML
from src.escriptorium.ocr_xml import OCRXML
from src.ocr_error_corrector.dictionary_matcher.config import (
    MANUAL_FILES_PATH,
    OCR_FILE_PATH,
    DISTANCE_THRESHOLD,
    SORT_BY_DISTANCE,
    MERGE_THRESHOLD,
    ENABLE_NORMALIZER,
)


def main():
    dictionary = create_dictionary(MANUAL_FILES_PATH)
    ocr_words = read_ocr_words(OCR_FILE_PATH)
    # ocr_words = read_cab_words(OCR_FILE_PATH)
    matches = match_ocr_words(ocr_words, dictionary)
    with open('res/matches.json', 'w', encoding='utf8') as f:
        if SORT_BY_DISTANCE:
            matches = sorted(matches, key=lambda x: -x['distance'])

        for match in matches:
            match['address'] = [asdict(address) for address in match['address']]
        f.write(json.dumps(matches, ensure_ascii=False, indent=4))

def match_ocr_words(ocr_words: OCRXML, dictionary: set[str]):
    matches = []
    cur_ind = 0
    while cur_ind < len(ocr_words):
        if cur_ind % 10:
            print(f"matching word {cur_ind}/{len(ocr_words)}: {ocr_words[cur_ind].word}")

        possible_matches = []
        for i in range(1, MERGE_THRESHOLD + 1):
            max_ind = min(cur_ind + i, len(ocr_words))
            word = ''.join([ocr_words[j].word for j in range(cur_ind, max_ind)])
            word_address = [ocr_words[j].address for j in range(cur_ind, max_ind)]
            match = find_match(word, dictionary)
            match = copy.deepcopy(match)
            match['address'] = word_address
            possible_matches.append(match)

        possible_matches = sorted(possible_matches, key=lambda match: (match['distance'], -len(match["manual_word"])))
        matches.append(possible_matches[0])
        cur_ind += len(possible_matches[0]['address'])

    return matches


memo = {}
def find_match(ocr_word: str, dictionary: set[str]):
    if ocr_word in memo:
        return memo[ocr_word]

    if ocr_word in dictionary:
        memo[ocr_word] = {'ocr_word': ocr_word, 'manual_word': ocr_word, 'distance': 0}
        return memo[ocr_word]

    matched_words = []
    for word in dictionary:
        edit_distance = Levenshtein.distance(ocr_word, word)\
            if not ENABLE_NORMALIZER else Levenshtein.distance(normalize(ocr_word), normalize(word))
        if edit_distance <= DISTANCE_THRESHOLD:
            matched_words.append({'manual_word': word, 'distance': edit_distance})
    matched_words = sorted(matched_words, key=lambda x: x['distance'])
    memo[ocr_word] = {
        'ocr_word': ocr_word,
        'manual_word': matched_words[0]['manual_word'] if matched_words else '',
        'distance': matched_words[0]['distance'] if matched_words else 1000,
    }
    return memo[ocr_word]

normalizer_memo = {}
def normalize(text):
    if text in normalizer_memo:
        return normalizer_memo[text]

    original_text = text
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
        ('x', ['x́', 'x́', 'xᵛ']),
        ('n', ['ń', 'ṇ']),
        ('ī', ['ū']),
        ('ϑ', ['t']),
        ('d', ['δ'])
    ]
    for uniform in uniform_list:
        for char in uniform[1]:
            text = re.sub(char, uniform[0], text)
    # text = re.sub(r'[^a-z]*', '', text)
    normalizer_memo[original_text] = text
    return text


def create_dictionary(manual_files_path):
    words = []
    for manual_file_path in manual_files_path:
        cab = CABXML(manual_file_path)
        words += [word.word for word in cab if word.word]
    return set(words)


def read_ocr_words(ocr_file_path):
    ocr_words = OCRXML(ocr_file_path)
    return ocr_words

# def read_cab_words(file_path):
#     cab_words = CABXML(file_path)
#     return cab_words


if __name__ == '__main__':
    main()
