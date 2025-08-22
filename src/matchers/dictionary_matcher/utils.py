def memoize(memoize_for_args: list[str]=None):
    def memoizer(func):
        cache = {}

        def memoized(*args, **kwargs):
            if memoize_for_args is None:
                key = (args, frozenset(kwargs.items()))
            else:
                key = tuple(kwargs.get(arg) for arg in memoize_for_args)

            if key not in cache:
                cache[key] = func(*args, **kwargs)
            return cache[key]

        return memoized
    return memoizer
