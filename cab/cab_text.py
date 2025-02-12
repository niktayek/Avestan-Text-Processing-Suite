import dataclasses
import re
from lxml import etree


class CABText:
    @dataclasses.dataclass
    class Address:
        id: str
        index: int

    def __init__(self, file_path):
        self._abs = self._load_xml(file_path)
        self._items = self._list_items()

    def _load_xml(self, file_path):
        tree = etree.parse(file_path)
        root = tree.getroot()
        all_abs = root.findall('.//ab')
        return [
            (
                ab.get('{http://www.w3.org/XML/1998/namespace}id'),
                re.sub(r'\n', '', re.sub(' +', ' ', inner_text)).strip(),
            ) for ab in all_abs if len(inner_text := ''.join(ab.itertext()).strip()) > 0
        ]

    def _list_items(self):
        items = []
        for id, text in self._abs:
            # text = re.sub('(\\.|\s+)', ' ', text)
            words = text.split(" ")
            for ind, word in enumerate(words):
                items.append((self.Address(id, ind), word))
        return items

    def __getitem__(self, item):
        return self._items[item]

    def __len__(self):
        return len(self._items)
