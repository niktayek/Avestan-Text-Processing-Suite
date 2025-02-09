import re

input_file = "../ocr-error-corrector/text-matcher/data/TD2_16_29_Mackenzie_manual.txt"
output_file = "../ocr-error-corrector/text-matcher/data/TD2_16_29_Mackenzie_manual_clean.txt"

rules = [
    (r"_", ""),
    (r"\([^()]*\)", r""),
    (r"\[[^\[\]]*\]", r""),
    (r"<[^<>]*>", r""),
    (r"{[^{}]*}", r""),
    (r"\.\.\.", r""),
]

with open(input_file, "r") as f:
    text = f.read()
    for rule in rules:
        text = re.sub(rule[0], rule[1], text)

with open(output_file, "w") as f:
    f.write(text)
