import json
import csv

input_file = 'res/replace_dict.json'
output_file = 'res/replace_dict.csv'

with open(input_file, 'r') as json_file:
    data = json.load(json_file)

fieldnames = data[0].keys() if data else []

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
    writer.writeheader()
    writer.writerows(data)
