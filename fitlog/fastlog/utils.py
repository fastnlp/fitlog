

def flatten_dict(prefix, _dict, connector='-'):
    """
    给定一个dict, 将其展平，比如{"a":{"v": 1}} -> {"a-v":1}

    :param prefix:
    :param _dict:
    :param connector:
    :return:
    """
    new_dict = {}
    for key, value in _dict.items():
        if prefix != '':
            new_prefix = prefix + connector + str(key)
        else:
            new_prefix = str(key)
        if isinstance(value, dict):
            new_dict.update(flatten_dict(new_prefix, value, connector))
        else:
            new_dict[new_prefix] = value
    return new_dict