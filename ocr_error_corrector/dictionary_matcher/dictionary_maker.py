import json
import nltk
from cab.cab_xml import CABXML
from escriptorium.ocr_text import OCRText
from ocr_error_corrector.text_matcher.config import DISTANCE_THRESHOLD

LANGUAGE = 'avestan'
MANUAL_FILE_PATH = '../../data/Videvdad_Static.xml'
OCR_FILE_PATH = '../../data/62v_65r_OCR_4210.txt'
DISTANCE_THRESHOLD = 2


def main():
    dictionary = create_dictionary(MANUAL_FILE_PATH)
    ocr_words = read_ocr_words(OCR_FILE_PATH)
    matches = match_ocr_words(ocr_words, dictionary)
    with open('res/matches.json', 'w') as f:
        f.write(json.dumps(matches))

def match_ocr_words(ocr_words: list[str], dictionary: set[str]):
    matches = []
    for i, word in enumerate(ocr_words):
        if i % 10:
            print(f"matching word {i}/{len(ocr_words)}: {word}")

        matches.append(find_match(word, dictionary))
    return matches


memo = {}
def find_match(ocr_word: str, dictionary: set[str]):
    if ocr_word in memo:
        return memo[ocr_word]

    if ocr_word in dictionary:
        memo[ocr_word] = (ocr_word, ocr_word)
        return memo[ocr_word]

    matched_words = []
    for word in dictionary:
        if (dist := nltk.edit_distance(word, ocr_word)) <= DISTANCE_THRESHOLD:
            matched_words.append((dist, word))
    matched_words = sorted(matched_words)
    memo[ocr_word] = (
        ocr_word,
        matched_words[0][1] if matched_words else ''
    )
    return memo[ocr_word]


def create_dictionary(manual_file_path):
    cab = CABXML(manual_file_path)
    words = [word.word for word in cab if word.word]
    return set(words)


def read_ocr_words(ocr_file_path):
    ocr_text = OCRText(ocr_file_path)
    words = [word.word for word in ocr_text]
    return words


if __name__ == '__main__':
    main()
