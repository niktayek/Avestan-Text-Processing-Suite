import dataclasses
import re
from lxml import etree


# This reads CAB XML files and let us go over the words one by one.
class CABXML:
    @dataclasses.dataclass
    class Word:
        @dataclasses.dataclass
        class Address:
            id: str
            index: int

        address: Address
        word: str

    def __init__(self, file_path):
        self._abs = self._load_xml(file_path)
        self._items = self._list_items()

    def _load_xml(self, file_path):
        parser = etree.XMLParser(recover=True)
        with open(file_path, 'r') as f:
            xml_str = f.read()
        root = etree.fromstring(xml_str, parser)
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
            text = re.sub(r'(\S)\.(\S)', r'\1\2', text)
            text = text.replace('.', ' ')
            text = text.replace('.', ' ')
            text = re.sub('\s+', ' ', text)
            words = text.split(" ")
            for ind, word in enumerate(words):
                items.append(self.Word(self.Word.Address(id, ind), word))
        return items

    def __getitem__(self, item):
        return self._items[item]

    def __len__(self):
        return len(self._items)


if __name__ == '__main__':
    cab_xml = CABXML('/home/nikta/Downloads/static_yasna.xml')
    for word in cab_xml:
        print(word)
