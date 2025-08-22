import os

# This points to /home/nikta/Desktop/OCR
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))

CORPUS_PATH = os.path.join(PROJECT_ROOT, "data", "static_yasna_clean.txt")
OCR_OUTPUT_PATH = os.path.join(PROJECT_ROOT, "data", "escriptorium", "0091_first_100_pages.txt")

MAX_LEN = 30
ERROR_RATE = 0.4
BATCH_SIZE = 64
EPOCHS = 15
