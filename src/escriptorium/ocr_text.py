import dataclasses


# It reads eScriptorium OCR text output and let us go over the words one by one.
class OCRText:
    @dataclasses.dataclass
    class Word:
        @dataclasses.dataclass
        class Address:
            line: int
            index: int

        address: Address
        word: str

    def __init__(self, file_path):
        self._lines = self._load_text(file_path)
        self._items = self._list_items()

    def _load_text(self, file_path):
        with open(file_path, 'r') as f:
            lines = f.readlines()
            return lines

    def _list_items(self):
        items = []
        for line_id, line in enumerate(self._lines):
            words = line.split(" ")
            for ind, word in enumerate(words):
                word = word.strip()
                word = word.replace('.', '. ')
                for word_part in word.split():
                    items.append(self.Word(self.Word.Address(line_id, ind), word_part))
        return items

    def __getitem__(self, item):
        return self._items[item]

    def __len__(self):
        return len(self._items)
