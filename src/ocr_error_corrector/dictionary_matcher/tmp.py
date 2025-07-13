from filling_changes_with_tagging import tokenize_graphemes, dp_differ
import unicodedata

# manual = 'raṣ̌nōiš'
# ocr = 'rašnaōš'
# manual = 'rašnōiš'
# ocr = 'rašnaōš'
# manual = 'tauruuaiieni'
# ocr = 'tauruuaiiəne'
manual = 'baragraməṇtąm'
ocr = 'barəgaramaṇtąm'


manual_tokens = tokenize_graphemes(unicodedata.normalize("NFC", manual))
ocr_tokens = tokenize_graphemes(unicodedata.normalize("NFC", ocr))
changes = dp_differ(manual_tokens, ocr_tokens)
print(f"Manual: \t{manual_tokens}")
print(f"OCR:    \t{ocr_tokens}")
print(f"Changes: {changes}")
