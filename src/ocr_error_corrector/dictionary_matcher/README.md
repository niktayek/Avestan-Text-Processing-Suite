# Dictionary Matcher
This module for each word in the OCR output finds the best matching word in a dictionary created by a set of manually transliterated manuscripts.

## Steps
1. Configure
   * The list of manually transliterated manuscripts in CAB XML format
   * The OCR output in eScriptorium text format
   * The matching configuration (e.g., DISTANCE_THRESHOLD, ENABLE_NORMALIZATION, etc.)
2. Run `matcher.py`. It generates a file named `res/matches.json`.
3. Run `json_to_csv.py`. It translates `res/matches.json` to `res/matches.csv`.
4. Import the CSV file in a Google sheet to analyze the result
