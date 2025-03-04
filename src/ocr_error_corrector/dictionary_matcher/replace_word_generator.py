import json
from itertools import combinations


def main():
    matches = json.load(open('res/matches.json'))

    for i, match in enumerate(matches):
        if i % 10:
            print(f"matching word {i}/{len(matches)}: {match['ocr_word']}")

        match['replace_word'] = generate_replace_word(match['ocr_word'], match['manual_word'])

    with open('res/replace_dict.json', mode='w', encoding='utf8') as f:
        f.write(json.dumps(matches, ensure_ascii=False, indent=4))


def generate_replace_word(ocr_word, manual_word):
    potential_features = {
        'a', 'ą', 'ą̇', 'å', 'ā', 'ae', 'aē', 'o', 'ō', 'ao', 'aō', 'z', 'ž', 'uu',
        'ū', 'ī', 'ii', 'ŋ', 'ŋ́', 'ŋᵛ', 's', 'š', 'š́', 'ṣ', 'ṣ̌', 'mh', 'm̨',
        'x́', 'x́', 'xᵛ', 'n', 'ń', 'ṇ', 'y', 'ẏ',
    }
    consonants = {
        'k', 'x', 'x́', 'xᵛ', 'g', 'ġ', 'γ', 'c', 'j', 't', 'θ', 'd', 'δ', 't',
        'p', 'č', 'ž', 'š', 'f', 'b', 'β', 'ŋ', 'ŋ́', 'ŋᵛ', 'n', 'ń', 'ṇ', 'm',
        'm̨', 'ẏ', 'y', 'v', 'uu', 'ii', 'r', 'l', 's', 'z', 'ž', 'š́', 'ṣ̌', 'h',
    } - potential_features
    ocr_list = split_by_consonants(ocr_word, consonants)
    manual_list = split_by_consonants(manual_word, consonants)

    ocr_consonant_count = len([part for part in ocr_list if part[1]])
    manual_consonant_count = len([part for part in manual_list if part[1]])
    if ocr_consonant_count == manual_consonant_count:
        ocr_ind = 0
        manual_ind = 0
        while ocr_ind < len(ocr_list):
            if not ocr_list[ocr_ind][1]:
                ocr_ind += 1
                continue
            if not manual_list[manual_ind][1]:
                manual_ind += 1
                continue
            ocr_list[ocr_ind][0] = manual_list[manual_ind][0]
            ocr_ind += 1
            manual_ind += 1

        return ''.join([part[0] for part in ocr_list])

    if ocr_consonant_count > manual_consonant_count:
        ocr_consonant_indices = [i for i, part in enumerate(ocr_list) if part[1]]

def split_by_consonants(word, consonants):
    ret = []
    cur_ind = 0
    while cur_ind < len(word):
        found = False
        for c in consonants:
            if word[cur_ind:].startswith(c):
                ret.append([c, True])
                cur_ind += len(c)
                found = True
                break
        if not found:
            ret.append([word[cur_ind], False])
            cur_ind += 1
    return ret

if __name__ == '__main__':
    main()
