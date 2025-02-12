import json


def main():
    with open('res/matches.json', 'r') as f:
        matches = json.loads(f.read())

    exact_matches = 0
    non_exact_matches = 0
    no_matches = 0
    for match in matches:
        if match[0] == match[1]:
            exact_matches += 1
        elif match[1] == '':
            no_matches += 1
        else:
            non_exact_matches += 1
    print(f'exact matches: {exact_matches}')
    print(f'non exact matches: {non_exact_matches}')
    print(f'no matches: {no_matches}')

if __name__ == "__main__":
    main()
