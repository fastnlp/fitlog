
from itertools import groupby
from operator import itemgetter
import numpy as np

def groupBy(data, key):
    """

    :param data: List[dict], 一级dict
    :param key: str，以哪个为key进行group
    :return: 可以看成[[key1, group1], [key2, group2]]
    """
    data.sort(key=itemgetter(key))
    grouped_data = groupby(data, itemgetter(key)) # key + 迭代器。可以看成[[key1, group1], [key2, group2]]
    return grouped_data

def get_grouped_data(data, keys):
    """

    :param data: list[dict]. dict为1级
    :param keys: 依次按照keys进行group
    :return: {}nested的dict，最后的value是符合这个group的结果
    """
    _dict = {}
    if len(keys)==1:
        grouped_data = groupBy(data, keys[0])
        for key, group in grouped_data:
            _dict[key] = list(group)
    else:
        key = keys[0]
        grouped_data = groupBy(data, key)
        for key, group in grouped_data:
            _dict[key] = get_grouped_data(list(group), keys[1:])
    return _dict

def merge(a, b, path=None):
    "merges b into a"
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass # same leaf value
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


if __name__ == '__main__':
    # a, b, c用来分， d,e用来计算
    # import numpy as np
    # from fitlog.fastserver.server.summary_utils import calculate_on_grouped_data
    # a = np.random.choice(list('abcde'), size=50)
    # b = np.random.choice(list('ABCDE'), size=50)
    # c = np.random.choice(list([1,2,3,4,5]), size=50)
    # d = np.random.random(size=(50,))
    # e = np.random.randn(50)
    #
    # data = [{'a':x1, 'b':x2, 'c':x3, 'd':x4, 'e':x5} for (x1,x2,x3,x4,x5) in
    #             zip(a,b,c,d,e)]
    # print(data)
    # _dict = get_grouped_data(data, keys=['a', 'b'])
    # d0 = {}
    # d1 = calculate_on_grouped_data(_dict, max, 'd')
    # d2 = calculate_on_grouped_data(_dict, max, 'e')
    #
    # merge(merge(d0, d1), d2)
    # print(d0)
    from fitlog.fastserver.server.summary_utils import generate_summary_table

    vertical = 'hyper-weight_decay'
    horizontals = ['hyper-rnn_layers']
    method = 'max'
    criteria = ['metric-BMESF1PreRecMetric-f', 'metric-step']
    results = ['metric-test-BMESF1PreRecMetric-rec']
    result_maps = ['f']
    selected_data = 'default.cfg'
    root_log_dir = '../../model_test/codes/V1/logs'

    print(generate_summary_table(vertical, horizontals, method, criteria, results, results, selected_data,
                     root_log_dir))