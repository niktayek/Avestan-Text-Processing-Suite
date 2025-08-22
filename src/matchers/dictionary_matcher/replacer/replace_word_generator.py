import json
from itertools import combinations
from src.matchers.dictionary_matcher.matcher import normalize

import nltk


def main():
    matches = json.load(open('res/matches.json'))

    for i, match in enumerate(matches):
        if i % 10 == 0:
            print(f"matching word {i}/{len(matches)}: {match['ocr_word']}")

        match['replace_word'] = generate_replace_word(match['ocr_word'], match['manual_word'], match['distance'])

    with open('res/replace_dict.json', mode='w', encoding='utf8') as f:
        f.write(json.dumps(matches, ensure_ascii=False, indent=4))


def generate_replace_word(ocr_word, manual_word, allowed_distance):
    potential_features = {
        'a', 'ą', 'ā', 'ā̊' , 'o', 'ō', 'ə', 'ə̄', 'e' 'ē' 'u' 'ū', 'i',
        'ī',
        # 'ŋ', 'ŋ́', 'ŋᵛ', 's', 'š', 'š́', 'ṣ', 'ṣ̌',
        # 'x', 'x́', 'xᵛ', 'n', 'ń', 'ṇ', 'y', 'ẏ', 'ϑ', 't', 'd', 'δ'
    }
    consonants = {
        'k', 'x', 'x́', 'xᵛ', 'g', 'ġ', 'γ', 'c', 'j', 't', 'θ', 'd', 'δ', 't',
        'p', 'č', 'ž', 'š', 'f', 'b', 'β', 'ŋ', 'ŋ́', 'ŋᵛ', 'n', 'ń', 'ṇ', 'm',
        'm̨', 'ẏ', 'y', 'v', 'uu', 'ii', 'r', 'l', 's', 'z', 'ž', 'š́', 'ṣ̌', 'h',
        'ŋ', 'ŋ́', 'ŋᵛ', 's', 'š', 'š́', 'ṣ', 'ṣ̌',
        'x', 'x́', 'xᵛ', 'n', 'ń', 'ṇ', 'y', 'ẏ', 'ϑ', 't', 'd', 'δ'
    } - potential_features
    ocr_list = split_by_consonants(ocr_word, consonants)
    manual_list = split_by_consonants(manual_word, consonants)

    ocr_consonant_count = len([part for part in ocr_list if part[1]])
    manual_consonant_count = len([part for part in manual_list if part[1]])
    if ocr_consonant_count == manual_consonant_count:
        return exact_replace_consonants(ocr_list, manual_list)

    if allowed_distance == 1000:
        return ocr_list, manual_list

    if 0 <= ocr_consonant_count - manual_consonant_count <= allowed_distance:
        return approximate_replace_consonants(ocr_list, manual_list, allowed_distance)
    if 0 <= manual_consonant_count - ocr_consonant_count <= allowed_distance:
        return approximate_replace_consonants(manual_list, ocr_list, allowed_distance)
    return ocr_list, manual_list


def exact_replace_consonants(ocr_list, manual_list):
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


def approximate_replace_consonants(editable_list, fix_list, allowed_distance):
    editable_consonant_count = len([part for part in editable_list if part[1]])
    fixed_consonant_count = len([part for part in fix_list if part[1]])

    editable_consonant_indices = [i for i, part in enumerate(editable_list) if part[1]]
    options = []
    for indices in combinations(editable_consonant_indices, editable_consonant_count - fixed_consonant_count):
        new_editable_list = editable_list.copy()
        indices = sorted(indices, reverse=True)
        for ind in indices:
            new_editable_list.pop(ind)

        new_editable_word = ''.join([part[0] for part in new_editable_list])
        fixed_word = ''.join([part[0] for part in fix_list])
        new_editable_edit_distance = nltk.edit_distance(normalize(new_editable_word), normalize(fixed_word))
        if new_editable_edit_distance < allowed_distance:
            options.append([new_editable_list, new_editable_edit_distance])

    if len(options) == 0:
        return fix_list

    options = sorted(options, key=lambda x: x[1])
    best_option = options[0]
    best_editable_list = best_option[0]
    return exact_replace_consonants(best_editable_list, fix_list)


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
