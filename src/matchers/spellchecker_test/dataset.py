import torch
from torch.utils.data import Dataset
import random

# OCR-style substitution map (based on your observed OCR errors)
OCR_ERROR_MAP = {
    "ā̊": ["ā", "a"],
    "ā": ["a", "ā̊"],
    "a": ["ā", "e"],
    "i": ["", "e", "a"],
    "e": ["i", "a"],
    "o": ["ō", "aō"],
    "ō": ["o", "aō", "u"],
    "ū": ["ī", "u"],
    "ą": ["ā"],
    "ə": ["i", "a"],
    "aē": ["ī", "ē"],
    "ē": ["ī", "e"],
    "ϑ": ["t", "x"],
    "t": ["ϑ", "c"],
    "xᵛ": ["x", "c"],
    "š": ["ṣ̌", "š́", "ž"],
    "ŋ": ["ŋᵛ", "n"],
    "ŋᵛ": ["ŋ"],
    "m": ["z"],
    "n": ["b", "u"],
    "d": ["k"],
    "δ": ["d"],
    "u": ["n"],
    ".": [""],
}

def inject_errors(word, error_rate=0.4):
    result = []
    i = 0
    while i < len(word):
        # Safely treat word as a string
        if isinstance(word, list):
            word = ''.join(word)

        # Handle multicharacter tokens (like xᵛ)
        if i + 1 < len(word) and word[i:i+2] in OCR_ERROR_MAP:
            token = word[i:i+2]
            if random.random() < error_rate:
                result.append(random.choice(OCR_ERROR_MAP[token]))
            else:
                result.append(token)
            i += 2
            continue

        char = word[i]
        if char in OCR_ERROR_MAP and random.random() < error_rate:
            result.append(random.choice(OCR_ERROR_MAP[char]))
        elif random.random() < error_rate / 6:  # deletion
            pass
        elif random.random() < error_rate / 6:  # insertion
            result.append(char)
            result.append(random.choice("aeiou"))
        else:
            result.append(char)
        i += 1

    return "".join(result)

class OCRDataset(Dataset):
    def __init__(self, tokens, char2idx, max_len=30, error_rate=0.4):
        self.tokens = tokens
        self.char2idx = char2idx
        self.max_len = max_len
        self.error_rate = error_rate

    def __len__(self):
        return len(self.tokens)

    def __getitem__(self, idx):
        clean = self.tokens[idx]
        noisy = inject_errors(clean, self.error_rate)

        x = [self.char2idx.get(c, 0) for c in noisy[:self.max_len]]
        y = [self.char2idx.get(c, 0) for c in clean[:self.max_len]]

        x += [0] * (self.max_len - len(x))
        y += [0] * (self.max_len - len(y))

        return torch.tensor(x), torch.tensor(y)
