import re
import string

import config


def load_ocr_words() -> list[str]:
    return load_normalized_words(config.OCR_FILE_PATH)


def load_manual_words() -> list[str]:
    return load_normalized_words(config.MANUAL_FILE_PATH)


def load_normalized_words(file_path: str) -> list[str]:
    with open(file_path, "r") as f:
        text = f.read()
        text = re.sub(r"\n", " ", text)
        text = re.sub(r"\s+", " ", text)

        if config.LANGUAGE == "pahlavi":
            text = re.sub(r"[WYwy]", "", text)
            text = re.sub(r"\d", "", text)

        words = [word for word in text.split(" ") if word]

        if config.LANGUAGE == "avestan":
            words = [word for word in words if not is_pahlavi(word)]

        return words


def is_pahlavi(word):
    if len(set(word).intersection(set(string.ascii_uppercase+"ʾ'w-0123456789"))) > 0:
        return True
    for char in ['Q̱', "Ḇ", "Š", "p̄"]:
        if char in word:
            return True
    return False
