import csv
import json


def memoize(memoize_for_args: list[str]=None):
    def memoizer(func):
        cache = {}

        def memoized(*args, **kwargs):
            if memoize_for_args is None:
                key = (args, frozenset(kwargs.items()))
            else:
                key = tuple(kwargs.get(arg) for arg in memoize_for_args)

            key = json.dumps(key, sort_keys=True)
            if key not in cache:
                cache[key] = func(*args, **kwargs)
            return cache[key]

        return memoized
    return memoizer


def write_csv(data: list[dict], output_file):
    fieldnames = data[0].keys() if data else []

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def read_csv(input_file) -> list[dict]:
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)
