import json


from data_loader import load_normalized_words


def main():
    manual_words = load_normalized_words("0040_plain_text.txt")
    ocr_words = load_normalized_words("OCR_manual_aligned.txt")

    with open("matches.json", "r") as f:
        matches = json.loads(f.read())

    print(f'number of matches: {len(matches)}')

    match_ind = 0
    manual_cur_ind = matches[0][0]
    ocr_cur_ind = matches[0][1]
    line_ocr = 'OCR: '
    line_manual = 'manual: '
    max_ocr_ind = min(matches[-1][1] + 10, len(ocr_words))
    max_manual_ind = min(matches[-1][0] + 10, len(manual_words))
    while manual_cur_ind < max_manual_ind and ocr_cur_ind < max_ocr_ind:
        if match_ind < len(matches):
            if manual_cur_ind == matches[match_ind][0] and ocr_cur_ind == matches[match_ind][1]:
                ocr_word = ocr_words[ocr_cur_ind]
                manual_word = manual_words[manual_cur_ind]
                line_ocr, line_manual = print_words(
                    f'*{ocr_word}* ({ocr_cur_ind})',
                    f'*{manual_word}* ({manual_cur_ind})',
                    line_ocr, line_manual
                )
                match_ind += 1
                ocr_cur_ind += 1
                manual_cur_ind += 1
                continue
            if manual_cur_ind == matches[match_ind][0]:
                line_ocr, line_manual = print_words(ocr_words[ocr_cur_ind], '', line_ocr, line_manual)
                ocr_cur_ind += 1
                continue
            if ocr_cur_ind == matches[match_ind][1]:
                line_ocr, line_manual = print_words('', manual_words[manual_cur_ind], line_ocr, line_manual)
                manual_cur_ind += 1
                continue
        line_ocr, line_manual = print_words(ocr_words[ocr_cur_ind], manual_words[manual_cur_ind], line_ocr, line_manual)
        ocr_cur_ind += 1
        manual_cur_ind += 1

    with open('matched_text.txt', 'w') as f:
        f.write(f'{line_ocr}\n{line_manual}')

def print_words(word_1, word_2, line_1, line_2):
    max_len = max(len(word_1), len(word_2))
    line_1 += word_1.ljust(max_len) + '\t'
    line_2 += word_2.ljust(max_len) + '\t'
    return line_1, line_2

if __name__ == "__main__":
    main()
