import random

OCR_NOISE_MAP = {
    "k": ["d"], "d": ["k"], "n": ["b", "u"], "m": ["z"], "ϑ": ["x", "t"],
    "x": ["ϑ"], "t": ["c", "ϑ"], "c": ["t"], "xᵛ": ["x́"], "x́": ["xᵛ"],
    "δ": ["d"], "ŋᵛ": ["ŋ"], "ŋ": ["ŋᵛ"], ".": ["i", ""], "i": ["e", "ə", "ī"],
    "ī": ["ū", "ē", "ə̄"], "ē": ["ī"], "a": ["e", "i"], "e": ["a", "i"],
    "u": ["ū"], "ū": ["u"], "š": ["ṣ̌", "š́", "ṣ̌"], "ṣ̌": ["š"], "z": ["m"],
    "hm": ["ɱ"], "ɱ": ["hm"],
}

def inject_errors(word: str, error_rate: float = 0.2) -> str:
    new_word = ""
    i = 0
    while i < len(word):
        ch = word[i]
        digraph = word[i:i+2]
        if digraph in OCR_NOISE_MAP and random.random() < error_rate:
            new_word += random.choice(OCR_NOISE_MAP[digraph])
            i += 2
            continue
        elif ch in OCR_NOISE_MAP and random.random() < error_rate:
            new_word += random.choice(OCR_NOISE_MAP[ch])
        elif random.random() < error_rate / 3:
            i += 1
            continue
        else:
            new_word += ch
        i += 1
    return new_word
