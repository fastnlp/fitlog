# encoding=utf-8

# 验证如何将dict或者json文件转换为columns

import os
import json
from collections import defaultdict
from functools import reduce
from .server_config import read_extra_data
from .server_config import read_server_config
from .utils import expand_dict
from .server_config import save_config
from .server_config import save_extra_data
import warnings

def generate_columns(logs, hidden_columns=None, column_order=None, editable_columns=None,
                     exclude_columns=None, filter_condition=None, ignore_unchanged_columns=True,
                     str_max_length=20, round_to=6, ignore_not_exist=False):
    """

    :param logs: list of dict对象返回List形式的column数据.
    :param hidden_columns: {}, can chooose parent columns, then all children will be hidden
    :param column_order: dict, column的顺序
    :param editable_columns: dict，那些column是可以编辑的
    :param filter_condition: dict, 每个key的筛选条件
    :param ignore_unchanged_columns: 是否忽略不变的column
    :param int str_max_length: 长于这个的str会被以...替代
    :param round_to: int，保留多少位小数
    :param ignore_not_exist: bool, 如果不存在filter_condition中的内容，则认为是不满足条件

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
    if filter_condition is None:
        filter_condition = {}
    else:
        assert isinstance(exclude_columns, dict), "Only dict is allowed for filter_condition."

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
    exclude_log_ids = {}
    for ID, _dict in enumerate(logs):
        fields = {}
        for key, value in _dict.items():
            max_depth = max(add_field('', key, value, fields, connector, 0), max_depth)
        for key, value in fields.items():
            field_values[key].append(value)
        # field是一个一维的dict，内含expanded的key以及它的value
        filter = False
        # 如果不满足filter的条件(value不同，包含对应的key)，就不要把它添加到数据中去了
        for key, value in filter_condition.items():
            if key in fields:
                if str(value) != str(fields[key]):
                    filter = True
                    break
            elif ignore_not_exist:
                filter = True
                break
        if not filter:
            data.append(fields)
        else:
            exclude_log_ids[ID] = 1
    # 删除不满足条件的filter，如果没有满足条件的，则filter失效
    filtered_logs = [log for idx, log in enumerate(logs) if idx not in exclude_log_ids]
    if len(filtered_logs)==0:
        warnings.warn("No log meets the condition.")
    else:
        logs = filtered_logs

    # 删掉的log需要排除
    field_values = defaultdict(list) # 每种key的不同value
    for ID, _dict in enumerate(logs):
        fields = {}
        for key, value in _dict.items():
            max_depth = max(add_field('', key, value, fields, connector, 0), max_depth)
        for key, value in fields.items():
            field_values[key].append(value)

    unchange_columns = {}
    if ignore_unchanged_columns and len(logs)>1:
        must_include_columns = ['meta-fit_id', 'meta-git_id']
        for key, value in field_values.items():
            if len(value)==len(logs):
                value_set = set(value)
                # 每次都是一样的结果, 但排除只有一个元素的value以及可修改的column
                if len(value_set) == 1 and len(value)!=1 and key not in editable_columns:
                    unchange_columns[key] = value[0]  # 防止加入column中
        exclude_columns.update(unchange_columns) # 所有不变的column都不选择了
        for column in must_include_columns:
            if column in exclude_columns:
                exclude_columns.pop(column)
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
            col_span, c_col_ord = add_columns('', key, value, 0, max_depth, new_column_dict, order_value, connector,
                                              exclude_columns,
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

    data = {log['id']:log for log in data}
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
                item['filterStrictSearch'] = True
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

def merge(a, b, path=None, use_b=True):
    "merges b into a"
    # 将两个dict recursive合并到a中，有相同key的，根据use_b判断使用哪个值
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif use_b:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a

def prepare_incremental_data(logs, new_logs, field_columns, filter_condition=None, ignore_not_exist=False):
    """

    :param logs: {'id':dict, ...}, 之前的数据, flatten, dict.
    :param new_logs: List[dict,], 新读取到的数据, nested
    :param field_columns: {field:1}, 在前端显示的内容field
    :param filter_condition: {}, 用于过滤不需要的内容
    :param ignore_not_exist: bool, 是否删除过滤条件不存在的log
    :return: {'new_logs':[dict(), dict()...], 'update_logs':[dict(), dict()...]}
    """
    if filter_condition is None:
        filter_condition = {}

    # 1. 将new_logs的内容展平
    new_dict = {}
    for log in new_logs:
        ex_dict = expand_dict('', log, connector='-', include_fields=field_columns)
        filter = False  # 是否忽略掉
        for f_k, f_v in filter_condition.items():
            if f_k in ex_dict:
                if str(ex_dict[f_k]) != f_v:
                    filter = True
            elif ignore_not_exist:
                filter = True
        if not filter:
            new_dict[log['id']] = ex_dict

    # 2. 将logs中的内容进行替换，或增加.
    updated_logs = []
    keys = list(new_dict.keys())
    for key in keys:
        if key in logs:
            value = new_dict.pop(key)
            log = merge(logs[key], value, use_b=True)
            updated_logs.append(log)
        else:
            new_dict[key]['memo'] = 'Click to edit'
    new_logs = list(new_dict.values())

    for key, value in new_dict.items():
        logs[key] = value

    return new_logs, updated_logs


def prepare_data(log_reader, log_dir, log_config_name, all_data=None): # 准备好需要的数据， 应该包含从log dir中读取数据
    """

    :param log_reader: 用于读取数据的Reader对象
    :param log_dir: str, 哪里是存放所有log的大目录
    :param log_config_path: 从哪里读取config
    :param all_data: dict, 如果不为None则不会从硬盘读取config和extra_data

    :return:
    """
    print("Start preparing data.")
    # 1. 从log读取数据
    log_dir = os.path.abspath(log_dir)
    log_config_path = os.path.join(log_dir, log_config_name)
    log_config_path = os.path.abspath(log_config_path)

    # 读取config文件
    # 读取log_setting_path
    if all_data is None:
        all_data = {}
    all_data.update(read_server_config(log_config_path))

    deleted_rows = all_data['deleted_rows']

    logs = log_reader.read_logs(deleted_rows)

    if len(logs)==0:
        raise ValueError("No valid log found in {}.".format(log_dir))

    # read extra_data
    if 'extra_data' not in all_data: # 只有在第一次需要读取
        extra_data_path = os.path.join(log_dir, 'log_extra_data.txt')
        extra_data = {}
        if os.path.exists(extra_data_path):
            extra_data = read_extra_data(extra_data_path)
        all_data['extra_data'] = extra_data

    # 2. 取出其他settings
    hidden_columns = all_data['hidden_columns']
    column_order = all_data['column_order']
    editable_columns = all_data['editable_columns']
    exclude_columns = all_data['exclude_columns']
    ignore_unchanged_columns = all_data['basic_settings']['ignore_unchanged_columns']
    str_max_length = all_data['basic_settings']['str_max_length']
    round_to = all_data['basic_settings']['round_to']

    new_all_data = generate_columns(logs=logs, hidden_columns=hidden_columns, column_order=column_order,
                                editable_columns=editable_columns,
                                exclude_columns=exclude_columns,
                                filter_condition=all_data['filter_condition'],
                                ignore_unchanged_columns=ignore_unchanged_columns,
                                str_max_length=str_max_length, round_to=round_to,
                                ignore_not_exist=all_data['settings']['Ignore_filter_condition_not_exist_log'])
    all_data.update(new_all_data)

    field_columns = {}
    for key, value in all_data['column_dict'].items():
        if 'field' in value:
            field_columns[key] = 1
    all_data['field_columns'] = field_columns

    return all_data

def replace_with_extra_data(data, extra_data, filter_condition=None, deleted_rows=None, ignore_not_exist=False):
    """

    :param data: {}, key是id，value是一阶json，包含了各个field的值
    :param extra_data: {}, key是id，value是一阶json，包含了各个field的值
    :param filter_condition: {}, 一级json。满足条件才加入(如果对应位置为空，也算满足条件)
    :param deleted_rows:{}, 一级json。在里面的id不能出现在返回的data中
    :param bool ignore_not_exist: 是否忽略不存在的filter_condition的key的log
    :return: 对data进行inplace修改
    """
    # 将数据进行替换
    extra_data = extra_data.copy()
    if len(extra_data)!=0:
        for d, value in data.items():
            if d in extra_data:
                tmp = extra_data.pop(d)
                for k, v in tmp.items():
                    value[k] = v
    # 将新增到extra_data的内容加进去
    if filter_condition is None:
        filter_condition = {}
    if deleted_rows is None:
        deleted_rows = {}
    if len(extra_data)>0: # 还有剩余的，说明是新加入的
        for key, value in extra_data.items(): # key是log的id，value是这个log新加入的内容
            if key in deleted_rows:
                continue
            filter = False  # 是否忽略掉
            for f_k, f_v in filter_condition.items():
                if f_k in value:
                    if str(value[f_k])!=f_v:
                        filter = True
                elif ignore_not_exist:
                    filter = True
            if not filter:
                if 'id' in value:  # 只有有id的才是用户加入的row
                    data[key] = value

def save_all_data(all_data, log_dir, log_config_name):
    # 保存settings和extra文件
    if all_data['settings']['Save_settings']:  # 如果需要保存
        log_config_path = os.path.join(log_dir, log_config_name)
        save_config(all_data, config_path=log_config_path)
        # save editable columns
        if len(all_data['extra_data']) != 0:
            extra_data_path = os.path.join(log_dir, 'log_extra_data.txt')
            save_extra_data(extra_data_path, all_data['extra_data']) # extra_data是一个dict。key为id，value为内容
        print("Settings are saved to {}.".format(log_config_path))



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
