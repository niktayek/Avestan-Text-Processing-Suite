import json

from src.cab.cab_xml import CABXML
from src.escriptorium.ocr_xml import OCRXML
from src.xml_translator.config import (
    CAB_XML_PATH,
    OCR_XML_DIR,
    MATCH_JSON_PATH,
    MATCHED_TEXT_PATH,
)


def main():
    cab_text = CABXML(CAB_XML_PATH)
    ocr_text = OCRXML(OCR_XML_DIR)

    with open(MATCH_JSON_PATH, "r") as f:
        matches = json.loads(f.read())

    print(f'number of matches: {len(matches)}')

    match_ind = 0
    cab_cur_ind = matches[0]['cab_ind']
    ocr_cur_ind = matches[0]['ocr_ind']
    line_ocr = 'OCR: '
    line_cab = 'CAB: '
    max_ocr_ind = min(matches[-1]['ocr_ind'] + 10, len(ocr_text))
    max_cab_ind = min(matches[-1]['cab_ind'] + 10, len(cab_text))
    while cab_cur_ind < max_cab_ind and ocr_cur_ind < max_ocr_ind:
        if match_ind < len(matches):
            if cab_cur_ind == matches[match_ind]['cab_ind'] and ocr_cur_ind == matches[match_ind]['ocr_ind']:
                ocr_word = ocr_text[ocr_cur_ind]
                cab_word = cab_text[cab_cur_ind]
                line_ocr, line_cab = print_words(
                    f'*{ocr_word.word}* ({ocr_word.address.page}-{ocr_word.address.line})',
                    f'*{cab_word.word}* ({cab_word.address.id})',
                    line_ocr, line_cab
                )
                match_ind += 1
                ocr_cur_ind += 1
                cab_cur_ind += 1
                continue
            if cab_cur_ind == matches[match_ind]['cab_ind']:
                line_ocr, line_cab = print_words(ocr_text[ocr_cur_ind].word, '', line_ocr, line_cab)
                ocr_cur_ind += 1
                continue
            if ocr_cur_ind == matches[match_ind]['ocr_ind']:
                line_ocr, line_cab = print_words('', cab_text[cab_cur_ind].word, line_ocr, line_cab)
                cab_cur_ind += 1
                continue
        line_ocr, line_cab = print_words(ocr_text[ocr_cur_ind].word, cab_text[cab_cur_ind].word, line_ocr, line_cab)
        ocr_cur_ind += 1
        cab_cur_ind += 1

    with open(MATCHED_TEXT_PATH, 'w') as f:
        f.write(f'{line_ocr}\n{line_cab}')


def print_words(word_1, word_2, line_1, line_2):
    max_len = max(len(word_1), len(word_2))
    line_1 += word_1.ljust(max_len) + '\t'
    line_2 += word_2.ljust(max_len) + '\t'
    return line_1, line_2

if __name__ == "__main__":
    main()
