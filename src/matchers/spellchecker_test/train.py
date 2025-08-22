import re
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ocr_error_corrector.spellchecker.model import SpellCheckerLSTM
from ocr_error_corrector.spellchecker.dataset import OCRDataset
from ocr_error_corrector.spellchecker.spell_config import *

# --- Helper: load clean corpus ---
def load_corpus(path):
    with open(path, encoding="utf-8") as f:
        text = f.read().replace("\n", " ").lower()
        return [t for t in re.split(r"\s+", text) if t]

# --- Helper: build character vocab ---
def build_vocab(tokens):
    chars = sorted(set("".join(tokens)))
    char2idx = {c: i + 1 for i, c in enumerate(chars)}  # 0 is reserved for padding
    char2idx["<PAD>"] = 0
    idx2char = {i: c for c, i in char2idx.items()}
    return char2idx, idx2char

# --- Main training function ---
def train_model():
    tokens = load_corpus(CORPUS_PATH)
    char2idx, idx2char = build_vocab(tokens)
    dataset = OCRDataset(tokens, char2idx, max_len=MAX_LEN, error_rate=ERROR_RATE)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    model = SpellCheckerLSTM(vocab_size=len(char2idx))
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss(ignore_index=0)

    for epoch in range(EPOCHS):
        total_loss = 0
        for x, y in loader:
            optimizer.zero_grad()
            output = model(x)  # (batch_size, seq_len, vocab_size)
            loss = criterion(output.view(-1, output.size(-1)), y.view(-1))
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        print(f"Epoch {epoch + 1} Loss: {total_loss:.4f}")

        # Print training examples every 5 epochs
        if epoch % 5 == 0 or epoch == EPOCHS - 1:
            print("\nSample training pairs:")
            for i in range(3):
                x_sample, y_sample = dataset[i]
                noisy = ''.join(idx2char[i.item()] for i in x_sample if i != 0)
                clean = ''.join(idx2char[i.item()] for i in y_sample if i != 0)
                print(f"Noisy: {noisy}")
                print(f"Clean: {clean}")
                print("---")

    torch.save(model.state_dict(), "spell_model.pt")
    return model, char2idx, idx2char
