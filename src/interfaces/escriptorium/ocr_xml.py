import dataclasses
import os
import xml.etree.ElementTree as ET
import re


# It reads eScriptorium OCR XML output and let us go over the words one by one.
class OCRXML:
    @dataclasses.dataclass
    class Word:
        @dataclasses.dataclass
        class Address:
            page: str
            line: int
            index: int

        address: Address
        word: str

    def __init__(self, dir_path):
        self._lines = self._load_xml(dir_path)
        self._items = self._list_items()

    def _load_xml(self, dir_path):
        all_lines = []
        xml_files = list(os.path.join(dir_path, filename) for filename in os.listdir(dir_path) if filename.endswith(".xml"))
        xml_files = sorted(xml_files)
        for file_path in xml_files:
            file_name = os.path.basename(file_path)
            tree = ET.parse(file_path)
            root = tree.getroot()

            all_strings = root.findall('.//{http://www.loc.gov/standards/alto/ns-v4#}String')
            lines = [
                (
                    file_name.replace(".xml", ""),
                    line_ind,
                    string.get("CONTENT").strip(),
                ) for line_ind, string in enumerate(all_strings) if len(string.get("CONTENT").strip()) > 0
            ]

            all_lines += lines
        return all_lines

    def _list_items(self):
        items = []
        for page, line, text in self._lines:
            text = text.replace("&#x27;", "")
            text = re.sub(r' +', ' ', text)
            text = text.replace('.', ' ')
            text = re.sub('\s+', ' ', text)
            words = text.strip().split(" ")
            for ind, word in enumerate(words):
                items.append(self.Word(self.Word.Address(page, line, ind), word))
        return items

    def __getitem__(self, item):
        return self._items[item]

    def __len__(self):
        return len(self._items)
