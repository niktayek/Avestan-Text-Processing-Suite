import re


def load_ocr_words() -> list[str]:
    return load_normalized_words("data/export_doc22_0040_text_202502040015.txt")


def load_manual_words() -> list[str]:
    return load_normalized_words("data/0040_plain_text.txt")


def load_normalized_words(file_path: str) -> list[str]:
    with open(file_path, "r") as f:
        text = f.read()
        text = re.sub(r"\n", " ", text)
        text = re.sub(r"\s+", " ", text)
        return [word for word in text.split(" ") if word]
