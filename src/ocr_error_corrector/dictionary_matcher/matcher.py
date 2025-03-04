import json
import re
import nltk
from dataclasses import asdict
from src.cab.cab_xml import CABXML
from src.escriptorium.ocr_text import OCRText
from src.ocr_error_corrector.sequence_matcher.config import DISTANCE_THRESHOLD

LANGUAGE = 'avestan'
MANUAL_FILE_PATH = '../../../data/CAB/static_yasna.xml'
OCR_FILE_PATH = '../../../data/escriptorium/0090_first_part_for_error_corrector.txt'
DISTANCE_THRESHOLD = 3


def main():
    dictionary = create_dictionary(MANUAL_FILE_PATH)
    ocr_words = read_ocr_words(OCR_FILE_PATH)
    matches = match_ocr_words(ocr_words, dictionary)
    with open('matches.json', 'w', encoding='utf8') as f:
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

    normalized_ocr_word = remove_vowels(ocr_word)
    matched_words = []
    for word in dictionary:
        normalized_word = remove_vowels(word)
        if (dist := nltk.edit_distance(normalized_word, normalized_ocr_word)) <= DISTANCE_THRESHOLD:
            matched_words.append((dist, word))
    matched_words = sorted(matched_words)
    memo[ocr_word] = (
        ocr_word,
        matched_words[0][1] if matched_words else '',
        matched_words[0][0] if matched_words else 1000,
    )
    return memo[ocr_word]

def remove_vowels(text):
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


def create_dictionary(manual_file_path):
    cab = CABXML(manual_file_path)
    words = [word.word for word in cab if word.word]
    return set(words)


def read_ocr_words(ocr_file_path):
    ocr_words = OCRText(ocr_file_path)
    return ocr_words


if __name__ == '__main__':
    main()
