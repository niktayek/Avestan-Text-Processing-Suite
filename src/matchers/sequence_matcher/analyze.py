from data_loader import load_ocr_words, load_manual_words


def analyze():
    manual_words = load_manual_words()
    ocr_words = load_ocr_words()

    print('manual\t', len(manual_words))
    print('ocr\t', len(ocr_words))


if __name__ == "__main__":
    analyze()
