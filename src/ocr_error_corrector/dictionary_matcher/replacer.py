import json
from src.escriptorium.ocr_text import OCRText
from src.ocr_error_corrector.dictionary_matcher.config import OCR_FILE_PATH


def main():
    ocr_words = OCRText(OCR_FILE_PATH)

    matches = json.load(open('res/matches.json'))
    match_dict = {match['ocr_word']: match['replace_word'] for match in matches}

    for i, word in enumerate(ocr_words):
        if i % 10:
            print(f"matching word {i}/{len(ocr_words)}: {word.word}")

        word.word = replace_word(word.word, match_dict[word.word])

    ocr_words.save('res/replaced.txt')


def replace_word(ocr_word, manual_word):
    return manual_word
