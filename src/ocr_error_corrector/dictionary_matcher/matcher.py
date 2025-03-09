import json
import re
import nltk
import Levenshtein
from dataclasses import asdict
from src.cab.cab_xml import CABXML
from src.escriptorium.ocr_text import OCRText
from src.ocr_error_corrector.dictionary_matcher.config import (
    MANUAL_FILE_PATH,
    OCR_FILE_PATH,
    DISTANCE_THRESHOLD,
)


def main():
    dictionary = create_dictionary(MANUAL_FILE_PATH)
    ocr_words = read_ocr_words(OCR_FILE_PATH)
    matches = match_ocr_words(ocr_words, dictionary)
    with open('res/matches.json', 'w', encoding='utf8') as f:
        matches = [
            {
                'ocr_word': match[0][0],
                'manual_word': match[0][1],
                'distance': match[0][2],
                'address': asdict(match[1])
            }
            for match in matches
        ]
        matches = sorted(matches, key=lambda x: -x['distance'])
        # matches_csv = '\n'.join([
        #     f"{match['ocr_word']},{match['manual_word']},{match['distance']},{str(match['address'])}"
        #     for match in matches
        # ])
        f.write(json.dumps(matches, ensure_ascii=False, indent=4))

def match_ocr_words(ocr_words: OCRText, dictionary: set[str]):
    matches = []
    for i, word in enumerate(ocr_words):
        if i % 10:
            print(f"matching word {i}/{len(ocr_words)}: {word.word}")

        matches.append((find_match(word.word, dictionary), word.address))
    return matches


memo = {}
def find_match(ocr_word: str, dictionary: set[str]):
    if ocr_word in memo:
        return memo[ocr_word]

    if ocr_word in dictionary:
        memo[ocr_word] = (ocr_word, ocr_word, 0)
        return memo[ocr_word]

    normalized_ocr_word = normalize(ocr_word)
    matched_words = []
    for word in dictionary:
        normalized_word = normalize(word)
        # if (dist := nltk.edit_distance(normalized_word, normalized_ocr_word)) <= DISTANCE_THRESHOLD:
        if (dist := Levenshtein.distance(normalized_word, normalized_ocr_word)) <= DISTANCE_THRESHOLD:
            matched_words.append((dist, word))
    matched_words = sorted(matched_words)
    memo[ocr_word] = (
        ocr_word,
        matched_words[0][1] if matched_words else '',
        matched_words[0][0] if matched_words else 1000,
    )
    return memo[ocr_word]

def normalize(text):
    uniform_list = [
        ('a', ['ą', 'ą̇', 'å', 'ā']),
        ('ae', ['aē']),
        ('o', ['ō']),
        ('ao', ['aō']),
        ('z', ['ž']),
        ('uu', ['ū', 'ī', 'ii']),
        ('ŋ', ['ŋ́', 'ŋᵛ']),
        ('s', ['š', 'š́', 'ṣ', 'ṣ̌']),
        ('mh', ['m̨']),
        ('x', ['θ', 'x́', 'x́', 'xᵛ']),
        ('n', ['ń', 'ṇ']),
        ('t', ['δ', 't', 't̰']),
        ('y', ['ẏ']),
    ]
    for uniform in uniform_list:
        for char in uniform[1]:
            text = re.sub(char, uniform[0], text)
    # text = re.sub(r'[^a-z]*', '', text)
    return text


def create_dictionary(manual_file_path):
    cab = CABXML(manual_file_path)
    words = [word.word for word in cab if word.word]
    return set(words)


def read_ocr_words(ocr_file_path):
    ocr_words = OCRText(ocr_file_path)
    return ocr_words


if __name__ == '__main__':
    main()
