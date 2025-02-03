import re


def load_normalized_words(file_path: str) -> list[str]:
    with open(file_path, "r") as f:
        text = f.read()
        text = re.sub(r"\n", " ", text)
        text = re.sub(r"\s+", " ", text)
        return [word for word in text.split(" ") if word]
