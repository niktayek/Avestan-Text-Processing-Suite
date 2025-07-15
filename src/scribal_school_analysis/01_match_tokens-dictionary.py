import json
import re
import copy
import os
import Levenshtein
from .utils import memoize
from dataclasses import asdict
from src.cab.cab_xml import CABXML
from src.escriptorium.ocr_xml import OCRXML

REFERENCE_FILES_PATH = [
    # '../../../data/CAB/static_dron.xml',
    # '../../../data/CAB/static_videvdad.xml',
    # '../../../data/CAB/static_vishtasp.xml',
    # '../../../data/CAB/static_visperad.xml',
    # '../../../data/CAB/static_visperad_dh.xml',
    'data/CAB/static_yasna.xml',
    # '../../../data/CAB/static_yasnar.xml',
    # '../../../data/CAB/Videvdad_Static.xml',
]
GENERATED_FILE_PATH = "data/CAB/Yasna/0008_cleaned.xml"
OUTPUT_FILE_PATH = os.path.join(os.path.dirname(__file__), 'res/matches.json')

DISTANCE_THRESHOLD = 3
MERGE_THRESHOLD = 3
ENABLE_NORMALIZER = False
SORT_BY_DISTANCE = False


def main():
    reference_dictionary = create_dictionary(REFERENCE_FILES_PATH)
    # generated_words = read_ocr_words(OCR_FILE_PATH)
    generated_words = read_cab_words(GENERATED_FILE_PATH)

    matches = match_words(generated_words, reference_dictionary)
    if SORT_BY_DISTANCE:
        matches = sorted(matches, key=lambda x: -x['distance'])

    with open(OUTPUT_FILE_PATH, 'w', encoding='utf8') as f:
        for match in matches:
            match['address'] = [asdict(address) for address in match['address']]
        f.write(json.dumps(matches, ensure_ascii=False, indent=4))

def create_dictionary(reference_files_path):
    words = []
    for file_path in reference_files_path:
        cab = CABXML(file_path)
        words += [word.word for word in cab if word.word]
    return set(words)

def read_ocr_words(ocr_file_path):
    ocr_words = OCRXML(ocr_file_path)
    return ocr_words

def read_cab_words(file_path):
    cab_words = CABXML(file_path)
    return cab_words

def match_words(generated_words: OCRXML, reference_dictionary: set[str]):
    matches = []
    cur_ind = 0
    while cur_ind < len(generated_words):
        if cur_ind % 10:
            print(f"matching word {cur_ind}/{len(generated_words)}: {generated_words[cur_ind].word}")

        possible_matches = []
        for i in range(1, MERGE_THRESHOLD + 1):
            max_ind = min(cur_ind + i, len(generated_words))
            generated_word = ''.join([generated_words[j].word for j in range(cur_ind, max_ind)])
            generated_word_address = [generated_words[j].address for j in range(cur_ind, max_ind)]
            match = find_match(
                generated_word=generated_word,
                reference_dictionary=reference_dictionary,
            )
            match = copy.deepcopy(match)
            match['address'] = generated_word_address
            possible_matches.append(match)

        possible_matches = sorted(possible_matches, key=lambda match: (match['distance'], -len(match["reference_word"])))
        matches.append(possible_matches[0])
        cur_ind += len(possible_matches[0]['address'])

    return matches


@memoize(memoize_for_args=['generated_word'])
def find_match(generated_word: str, reference_dictionary: set[str]):
    if generated_word in reference_dictionary:
        return {'generated_word': generated_word, 'reference_word': generated_word, 'distance': 0}

    matched_words = []
    for reference_word in reference_dictionary:
        edit_distance = Levenshtein.distance(generated_word, reference_word)\
            if not ENABLE_NORMALIZER else Levenshtein.distance(normalize(generated_word), normalize(reference_word))
        if edit_distance <= DISTANCE_THRESHOLD:
            matched_words.append({'reference_word': reference_word, 'distance': edit_distance})
    matched_words = sorted(matched_words, key=lambda x: x['distance'])
    if not matched_words:
        return {'generated_word': generated_word, 'reference_word': '', 'distance': 1000}
    return {
        'generated_word': generated_word,
        'reference_word': matched_words[0]['reference_word'],
        'distance': matched_words[0]['distance'],
    }

@memoize()
def normalize(text):
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
    return text


if __name__ == '__main__':
    main()
