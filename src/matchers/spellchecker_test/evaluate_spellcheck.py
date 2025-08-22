import difflib
import csv
import os

def load_pairs(path):
    pairs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if '\t' in line:
                original, corrected = line.strip().split('\t', 1)
                orig_words = original.strip().split()
                corr_words = corrected.strip().split()
                for o, c in zip(orig_words, corr_words):
                    pairs.append((o, c))
    return pairs

def word_accuracy(pairs):
    correct = sum(o == c for o, c in pairs)
    return correct / len(pairs) if pairs else 0

def char_accuracy(pairs):
    correct = total = 0
    for o, c in pairs:
        sm = difflib.SequenceMatcher(None, o, c)
        correct += sum(tr.size for tr in sm.get_matching_blocks())
        total += max(len(o), len(c))
    return correct / total if total else 0

def export_csv(pairs, out_path):
    with open(out_path, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["OCR", "Correction", "Diff"])
        for o, c in pairs:
            diff = ''.join([
                f"[{c[j1:j2]}←{o[i1:i2]}]" if tag != "equal" else c[j1:j2]
                for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, o, c).get_opcodes()
            ])
            writer.writerow([o, c, diff])

def main():
    # Correct path: one level up from current file (not four!)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    corrected_path = os.path.join(project_root, "corrected_output.txt")
    csv_path = os.path.join(project_root, "corrections.csv")

    pairs = load_pairs(corrected_path)
    print(f"Total words: {len(pairs)}")
    print(f"Word accuracy: {word_accuracy(pairs):.2%}")
    print(f"Char accuracy: {char_accuracy(pairs):.2%}")

    export_csv(pairs, csv_path)
    print(f"Exported CSV to: {csv_path}")

if __name__ == "__main__":
    main()
