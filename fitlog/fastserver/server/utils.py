


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


def replace_nan_inf(data):
    # data: List[dict]
    if isinstance(data, list):
        for d in data:
            _replace_nan_inf(d)
    elif isinstance(data, dict):
        _replace_nan_inf(data)
    else:
        raise TypeError("Unsupported type.")
    return data

def _replace_nan_inf(d):
    for k, value in d.items():
        if isinstance(value, dict):
            _replace_nan_inf(value)
        elif isinstance(value, list):
            for d in value:
                _replace_nan_inf(d)
        elif value==float('inf'):
            d[k] = "Infinity"
        elif value==float('-inf'):
            d[k] = "-Infinity"
        elif str(value)=='nan':
            d[k] = "NaN"

def check_uuid(gold_uuid, _uuid):
    if gold_uuid==_uuid:
        return None
    else:
        return {'status': 'fail',
                'msg': "The data are out-of-date, please refresh this page. Or, you can set this page as Offline to "
                       "stop sending updates to the server."}