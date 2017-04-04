def match(value, pattern, exact=False):
    if exact:
        return value == pattern
    
    pattern = pattern.split('*')
    if len(pattern) == 2:
        return value.startswith(pattern[0])
    elif len(pattern) == 1:
        return value == pattern[0]
    else:
        raise ValueError(pattern)


def match_any(value, patterns, exact=False):
    return any([
        match(value, pattern, exact=exact)
        for pattern in patterns
    ])
