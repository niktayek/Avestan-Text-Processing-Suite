import csv
import json

input_file = 'res/matches - 0091_1-100_new_addetrsing.csv'
output_file = 'res/matches-0091_1-100.json'

results = []

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) < 4:
            continue  # skip incomplete rows
        ocr_word = row[0].strip()
        manual_word = row[1].strip()
        try:
            distance = int(row[2])
        except ValueError:
            distance = None

        address_str = row[3].strip().replace("'", '"')  # Convert to valid JSON
        try:
            address = json.loads(address_str)
        except json.JSONDecodeError:
            address = []

        results.append({
            "ocr_word": ocr_word,
            "manual_word": manual_word,
            "distance": distance,
            "address": address
        })

with open(output_file, 'w', encoding='utf-8') as out:
    json.dump(results, out, indent=4, ensure_ascii=False)
