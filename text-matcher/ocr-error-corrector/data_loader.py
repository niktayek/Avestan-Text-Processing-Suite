import re
import string


def load_ocr_words() -> list[str]:
    return load_normalized_words("data/OCR_manual_aligned.txt")


def load_manual_words() -> list[str]:
    return load_normalized_words("data/0040_plain_Avestan.txt")


def load_normalized_words(file_path: str) -> list[str]:
    with open(file_path, "r") as f:
        text = f.read()
        text = re.sub(r"\n", " ", text)
        text = re.sub(r"\s+", " ", text)
        return [word for word in text.split(" ") if word and not is_pahlavi(word)]


def is_pahlavi(word):
    if len(set(word).intersection(set(string.ascii_uppercase+"ʾ'w-0123456789"))) > 0:
        return True
    for char in ['Q̱', "Ḇ", "Š", "p̄"]:
        if char in word:
            return True
    return False
