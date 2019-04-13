


def expand_dict(prefix, _dict, connector='-', include_fields=None):
    new_dict = {}
    for key, value in _dict.items():
        if prefix != '':
            new_prefix = prefix + connector + key
        else:
            new_prefix = key
        if isinstance(value, dict):
            new_dict.update(expand_dict(new_prefix, value, connector, include_fields))
        else:
            if include_fields is None or new_prefix in include_fields:
                new_dict[new_prefix] = value
    return new_dict