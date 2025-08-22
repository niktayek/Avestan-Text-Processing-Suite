import re

input_file = "../../data/CAB/Yasna/0005.txt"
output_file = "../../data/CAB/Yasna/0005_clean.txt"

rules = [
    (r"_", ""),
    (r"\([^()]*\)", r""),
    (r"\[[^\[\]]*\]", r""),
    (r"<[^<>]*>", r""),
    (r"{[^{}]*}", r""),
    (r"\.\.\.", r""),
    (r"[≈=]", r" "),
    (r"\d", r""),
    (r"^[\s+]", r""),
    (r"\n[ \t]*\n", r"\n"),
    (r"^[\s]+", r""),
]

with open(input_file, "r") as f:
    text = f.read()
    text = ' '.join([word for word in text.split() if word and not any(char.isupper() for char in word)])
    for rule in rules:
        text = re.sub(rule[0], rule[1], text)

with open(output_file, "w") as f:
    f.write(text)
