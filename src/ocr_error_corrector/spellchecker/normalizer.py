import re

# Tolerated orthographic or phonological variations
TOLERATED_VARIANTS = {
    "ā̊": ["ā", "āi"], "ā": ["a", "ą"], "a": ["ai", "ā"], "i": ["e", "ə"],
    "e": ["i", "a"], "ī": ["ū", "ē", "ə̄"], "ū": ["ī", "u"], "ō": ["aō", "u", "uu"],
    "aō": ["ō"], "ə": ["i", "a"], "ə̄": ["ī", "aē"], "ą": ["ā", "u"], "ai": ["iia"],
    "ii": ["aiia", "aii"], "iiā̊": ["aiiā̊"], "ē": ["aē", "ī"], "aē": ["ū", "ə"],
    "ϑ": ["t", "s"], "t": ["ϑ", "c"], "δ": ["d"], "d": ["δ"], "š": ["š́", "ṣ̌", "ṣ̌", "ž", "šhe"],
    "š́": ["š", "ṣ̌"], "ṣ̌": ["š", "š́"], "ṣ̌": ["š"], "ŋ": ["ŋᵛ", "ŋ́", "ŋh", "ṇg"],
    "ŋ́": ["ŋ", "iŋ́"], "xᵛ": ["x", "x́"], "x́": ["xᵛ"], "arə": ["ərə", "ar"],
    "ərə": ["arə", "ar"], "ar": ["arə"], "rā": ["ərā", "ra"], "ra": ["əra"],
    ".": ["i", ""], "hm": ["ɱ"], "ɱ": ["hm"], "auua": ["uua"], "uu": ["uua", "ϑ"],
    "uue": ["auue"], "uā": ["u"], "iiəm": ["aiiam"], "iiō": ["iiōi"], "n": ["ń"],
    "nəm": ["nm"], "the": ["tahe"]
}

# Convert to bidirectional form
BIDIRECTIONAL_VARIANTS = {}
for key, vals in TOLERATED_VARIANTS.items():
    for val in vals:
        BIDIRECTIONAL_VARIANTS.setdefault(key, set()).add(val)
        BIDIRECTIONAL_VARIANTS.setdefault(val, set()).add(key)

# Known abbreviations that may be merged
ABBREVIATIONS = {
    "y": "yasnāica",
    "v": "vaɱāica",
    "x": "xšnaōϑrāica",
    "f": "frasastaiiaēca"
}

def normalize_token(token: str) -> str:
    token = token.lower().strip()
    token = token.replace(" i ", " . ").replace("i", ".")

    for abbr in ABBREVIATIONS:
        token = re.sub(rf"\b{abbr}\b", "", token)
        token = re.sub(rf"{abbr}(?=\w)", "", token)
        token = re.sub(rf"(?<=\w){abbr}", "", token)

    for char, variants in BIDIRECTIONAL_VARIANTS.items():
        for var in variants:
            token = token.replace(var, char)

    return token
