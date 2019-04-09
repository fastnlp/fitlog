# encoding=utf-8

# 验证如何将dict或者json文件转换为columns

import json
from collections import defaultdict
from functools import reduce

def generate_columns(logs, hidden_columns=None, column_order=None, editable_columns=None,
                     exclude_columns=None, ignore_unchanged_columns=True,
                     str_max_length=20, round_to=6):
    """
    :param dict_lst: list of dict对象返回List形式的column数据.
    :param hidden_columns: {}, can chooose parent columns, then all children will be hidden
    :param column_order: dict
    :param round_to: int，保留多少位小数

    return:
        data: List[]数据
        unchange_columns: dict
        column_order: dict, 前端显示的column_order
        hidden_columns: dict, 需要隐藏的column，具体到field的
        column_dict: {}只有一级内容，根据prefix取出column内容，使用DFS对order_dict访问，然后将内容增加到columns中
    """
    assert len(logs)!=0, "Empty list is not allowed."

    connector = '-'  # 不能使用“!"#$%&'()*+,./:;<=>?@[\]^`{|}~ ”
    unselectable_columns = {} # 这个dict中的prefix没有filter选项，(1) 每一行都不一样的column; (2) 只有一种value的column
    if editable_columns is None:
        editable_columns = {'memo': 1} # 在该dict的内容是editable的, 保证不会被删除
    else:
        assert isinstance(editable_columns, dict), "Only dict is allowed for editable_columns."
        editable_columns['memo'] = 1
    if exclude_columns is None:
        exclude_columns = {}
    else:
        assert isinstance(exclude_columns, dict), "Only dict is allowed for exclude_columns."

    assert isinstance(logs, list), "Only list type supported."
    for _dict in logs:
        assert isinstance(_dict, dict), "Only dict supported."
        for key,value in _dict.items():
            assert key == 'id', "`id` must be put in the first key."
            break
    if hidden_columns is not None:
        assert isinstance(hidden_columns, dict), "Only dict type suppported."
    else:
        hidden_columns = {}
    if column_order is not None:
        assert isinstance(column_order, dict), "Only dict tyep supported."
    else:
        column_order = dict()

    def add_field(prefix, key, value, fields, connector, depth):
        if prefix != '':
            prefix = prefix + connector + key
        else:
            prefix = key
        if prefix in exclude_columns: # 排除的话就不要了
            return 0
        max_depth = depth
        if isinstance(value, dict):
            for k, v in value.items():
                max_depth = max(add_field(prefix, k, v, fields, connector, depth), max_depth)
        else:
            if isinstance(value, float) and round_to is not None:
                value = round(value, round_to)
            if isinstance(value, str):
                if len(value)>str_max_length and prefix not in editable_columns: # editable的不限制
                    value = value[:str_max_length] + '...'
                    unselectable_columns[prefix] = 1
            fields[prefix] = value
        return max_depth + 1

    data = []
    max_depth = 1
    field_values = defaultdict(list) # 每种key的不同value
    for ID, _dict in enumerate(logs):
        fields = {}
        for key, value in _dict.items():
            max_depth = max(add_field('', key, value, fields, connector, 0), max_depth)
        for key, value in fields.items():
            field_values[key].append(value)
        data.append(fields)

    unchange_columns = {}
    if ignore_unchanged_columns and len(logs)>1:
        for key, value in field_values.items():
            value_set = set(value)
            if len(value_set) == 1 and key not in editable_columns: # 每次都是一样的结果, 但排除可修改的column
                unchange_columns[key] = value[0]  # 防止加入column中
        exclude_columns.update(unchange_columns) # 所有不变的column都不选择了
        for fields in data:
            for key, value in exclude_columns.items():
                if key in fields:
                    fields.pop(key)

    for key, value in field_values.items():
        value_set = set(value)
        if len(value_set) == len(value) or len(value_set)==1:
            unselectable_columns[key] = 1

    column_dict = {}  # 这个dict用于存储结构，用于创建columns. 因为需要保证创建的顺序不能乱。 Nested dict
    reduce(merge, [column_dict] + logs)
    remove_exclude(column_dict, exclude_columns)

    column_dict['memo'] = '-' # 这一步是为了使得memo默认在最后一行
    for _dict in data:
        if 'memo' not in _dict:
            _dict['memo'] = 'Click to edit'

    # 需要生成column_order
    new_column_order = dict()
    new_column_dict = {}

    # generate_columns
    new_hidden_columns = {}
    column_keys = [key for key in column_dict.keys()]

    first_column_keys = []
    for key, order_value in column_order.items(): # 先按照order_dict进行排列
        if key in column_dict:
            value = column_dict[key]
            col_span, c_col_ord = add_columns('', key, value, 0, max_depth, new_column_dict, order_value, connector, exclude_columns,
                        unselectable_columns,
                        editable_columns, hidden_columns, new_hidden_columns, False)
            column_keys.pop(column_keys.index(key))
            if col_span!=0:
                new_column_order[key] = c_col_ord
                first_column_keys.append(key)
    for key in column_keys: # 再按照剩下的排
        value = column_dict[key]
        col_span, c_col_ord = add_columns('', key, value, 0, max_depth, new_column_dict, None, connector, exclude_columns,
                    unselectable_columns,
                    editable_columns, hidden_columns, new_hidden_columns, False)
        if col_span != 0:
            new_column_order[key] = c_col_ord
            first_column_keys.append(key)
    new_column_order['OrderKeys'] = first_column_keys # 使用一个OrderKeys保存没一层的key的顺序

    res = {'data': data, 'unchanged_columns':unchange_columns, 'column_order': new_column_order, 'column_dict':new_column_dict,
           'hidden_columns': new_hidden_columns}

    return res

def remove_exclude(column_dict, exclude_dict, prefix=''):
    # 将exclude_dict中的field从nested的column_dict中移除
    keys = list(column_dict.keys())
    for key in keys:
        if prefix=='':
            new_prefix = key
        else:
            new_prefix = prefix + '-' + key
        if new_prefix in exclude_dict:
            column_dict.pop(key)
        else:
            if isinstance(column_dict[key], dict):
                remove_exclude(column_dict[key], exclude_dict, new_prefix)


def add_columns(prefix, key, value, depth, max_depth, column_dict, order_value, connector, exclude_columns,
                unselectable_columns, editable_columns, hidden_columns, new_hidden_columns, hide):
    if prefix != '':
        prefix = prefix + connector + key
    else:
        prefix = key
    if prefix in exclude_columns:
        return 0, None
    if not hide:
        if prefix in hidden_columns:
            hide = True

    item = {}
    item['title'] = key
    colspan = 1
    min_unuse_depth = max_depth - depth - 1
    column_order = {}
    if isinstance(value, dict):
        total_colspans = 0
        column_keys = [key for key in value.keys()]
        first_column_keys = []
        if isinstance(order_value, dict):# 如果order_value是dict，说明下面还有顺序
            for o_key, o_v in order_value.items():
                if o_key in value:
                    n_val = value[o_key]
                    colspan, c_col_ord = add_columns(prefix, o_key, n_val, depth + 1, max_depth, column_dict, o_v,
                                                     connector, exclude_columns, unselectable_columns, editable_columns,
                                                     hidden_columns, new_hidden_columns, hide)
                    total_colspans += colspan
                    min_unuse_depth = 0
                    column_keys.pop(column_keys.index(o_key))
                    if colspan!=0: # 需要排除这个column
                        column_order[o_key] = c_col_ord
                        first_column_keys.append(o_key)
        for key in column_keys:
            v = value[key]
            colspan, c_col_ord = add_columns(prefix, key, v, depth + 1, max_depth, column_dict, None, connector,
                                             exclude_columns, unselectable_columns, editable_columns,
                                             hidden_columns, new_hidden_columns, hide)
            total_colspans += colspan
            min_unuse_depth = 0
            if colspan != 0:  # 需要排除这个column
                column_order[key] = c_col_ord
                first_column_keys.append(key)
        colspan = total_colspans
        column_order['OrderKeys'] = first_column_keys
    else:
        item['field'] = prefix
        item['sortable'] = 'true'
        if prefix not in unselectable_columns:
            if prefix in editable_columns:
                item['filterControl'] = 'input'
            else:
                item['filterControl'] = 'select'
        if prefix in editable_columns:
            item['editable'] = 'true'
        else:
            item['editable'] = 'false'
        if hide:
            new_hidden_columns[prefix] = 1
        column_order = "EndOfOrder"

    item['rowspan'] = min_unuse_depth + 1
    item['colspan'] = colspan
    column_dict[prefix] = item

    return colspan, column_order

def merge(a, b, path=None):
    "merges b into a"
    # 将两个dict recursive合并到a中，
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass # same leaf value
            # else:
            #     raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a

if __name__ == '__main__':
    _dict = json.loads('{"id":0, "a":1,"b":{"a":{"d":4,"e":5},"b":2}}')
    print(_dict)
    data = generate_columns([_dict], column_order={'memo':0, 'b':{'b':0, 'a':{'e':0, 'd':0}}, 'a':0, 'id':0})
    print(data['column_order'])
    print(data['column_dict'])
    import json
    print(json.dumps(_dict))

    # _dict = {'a': 1}
    # print(str(_dict))
    # print(json.loads('{"a":1,"b":2,"c":3,"d":4,"e":5}'))
    # print(type(json.loads('{"a":1,"b":{"a":1,"b":2},"c":3,"d":4,"e":5}')))
