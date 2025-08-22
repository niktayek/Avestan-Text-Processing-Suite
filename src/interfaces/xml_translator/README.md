# XML Translator
This folder contains the code to match the OCR output of a manuscript (in eScriptorium ALTO XML format) with the CAB XML, and replace the content of the CAB XML with the OCR output.

## Steps
1. Run `matcher.py`: this code reads the OCR output and the CAB XML, matches the OCR output with the CAB XML, and saves the matches in `res/matches.json`.
2. Run `print_matches.py`: this code reads the matches from `res/matches.json` and prints the matches in a human-readable format.
3. Run `generate_new_xml.py`: this code reads the matches from `res/matches.json` and replaces the content of the CAB XML with the OCR output. The new XML is saved in `res/new_cab.xml`.
