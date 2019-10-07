# encoding=utf-8

# 验证如何将dict或者json文件转换为columns

import os
import json
from collections import defaultdict
from functools import reduce
from .server_config import read_extra_data
from .server_config import read_server_config
from .utils import flatten_dict
from .server_config import save_config
from .server_config import save_extra_data
import numbers
from ...fastgit.committer import _colored_string
import warnings

from .utils import LogFilter

def generate_columns(logs, hidden_columns=None, column_order=None, editable_columns=None,
                     exclude_columns=None, ignore_unchanged_columns=True,
                     str_max_length=20, round_to=6, num_extra_log=0):
    """

    :param logs: list of dict. [{'id': xx, 'meta':{'status': 'finish'}, "hyper": {'lr':... }}}]， 必须要包含一个'id' key
    :param hidden_columns: {}, can choose parent columns, then all children will be hidden. 一级dict
    :param column_order: dict, column的顺序
    :param exclude_columns: dict, 一级dict
    :param editable_columns: dict，那些column是可以编辑的
    :param ignore_unchanged_columns: 是否忽略不变的column
    :param int str_max_length: 长于这个的str会被以...替代
    :param round_to: int，保留多少位小数
    :param num_extra_log:int, 多少条log是用户自己加入的。用于过滤unchanged_columns

    return:
        data: {}数据{'id1': {'id':id1, 'xx':xx}} flat的dict
        unchange_columns: dict
        column_order: dict, 前端显示的column_order
        hidden_columns: dict, 需要隐藏的column，具体到field的
        column_dict: {}只有一级内容，根据prefix取出column内容，使用DFS对column_order访问，然后将内容增加到columns中
    """
    assert len(logs)!=0, "Empty list is not allowed."

    connector = '-'  # 不能使用“!"#$%&'()*+,./:;<=>?@[\]^`{|}~ ”
    unselectable_columns = {} # 这个dict中的prefix没有filter选项，(1) 每一行都不一样的column; (2) 只有一种value的column
    # (3) 长度超过一定长度的column

    def add_field(prefix, key, value, fields, connector, depth):
        if prefix != '':
            prefix = prefix + connector + str(key)
        else:
            prefix = str(key)
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

    # 获取展开后的log
    max_depth = 1
    field_values = defaultdict(list) # 每种key的不同value
    data = []
    for ID, _dict in enumerate(logs):
        fields = {}
        for key, value in _dict.items():
            max_depth = max(add_field('', key, value, fields, connector, 0), max_depth)
        data.append(fields)
        for key, value in fields.items():
            field_values[key].append(value)

    # 判断那些column没有变化过，
    unchange_columns = {}
    if ignore_unchanged_columns and len(logs)>1:
        must_include_columns = ['meta-fit_id', 'meta-git_id']
        for key, value in field_values.items():
            if len(value) >= len(logs)-num_extra_log:
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
        if len(value_set) >= len(value)-num_extra_log or len(value_set)==1:
            unselectable_columns[key] = 1

    # 增加一个默认可以edit的column
    for _dict in data:
        for key in editable_columns.keys():
            if key not in _dict:
                _dict[key] = 'Click to edit'

    # 需要生成column_order, column_dict与隐藏的column
    new_column_order = dict()
    new_column_dict = {}
    new_hidden_columns = {}

    column_dict = {}  # 这个dict用于存储结构，用于创建columns. 因为需要保证创建的顺序不能乱。 Nested dict
    reduce(merge, [column_dict] + logs)
    if len(editable_columns)>0:
        _dict = expand_dict([editable_columns], connector='-')[0]
        merge(column_dict, _dict, use_b=False)
    remove_exclude(column_dict, exclude_columns)

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
    # 将exclude_dict(flattened的)中的field从nested的column_dict中移除
    keys = list(column_dict.keys())
    for key in keys:
        if prefix=='':
            new_prefix = str(key)
        else:
            new_prefix = prefix + '-' + str(key)
        if new_prefix in exclude_dict:
            column_dict.pop(key)
        else:
            if isinstance(column_dict[key], dict):
                remove_exclude(column_dict[key], exclude_dict, new_prefix)


def add_columns(prefix, key, value, depth, max_depth, column_dict, order_value, connector, exclude_columns,
                unselectable_columns, editable_columns, hidden_columns, new_hidden_columns, hide):
    # 向column_dict中添加column的性质的dict; 并且生成new_hidden_columns(包含到最细的粒度); 返回值是column的顺序
    if prefix != '':
        prefix = prefix + connector + str(key)
    else:
        prefix = str(key)
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
    :param new_logs: List[dict,], 新读取到的数据, nested。包含了新增加的log以及更新的log
    :param field_columns: {field:1}, 在前端table显示的内容field. 只用抽取这些field即可
    :param filter_condition: {}, 用于过滤不需要的内容
    :param ignore_not_exist: bool, 是否删除过滤条件不存在的log
    :return: {'new_logs':[dict(), dict()...], 'update_logs':[dict(), dict()...]}
    """
    if filter_condition is None:
        filter_condition = {}

    # 1. 将new_logs的内容展平
    new_dict = {}
    log_filter = LogFilter(filter_condition)
    for log in new_logs:
        flat_dict = flatten_dict('', log, connector='-')
        _filter = log_filter._filter_this_log_or_not(flat_dict, ignore_not_exist)
        if not _filter:
            new_dict[log['id']] = flat_dict

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

def expand_dict(dicts, connector='-'):
    """

    :param dicts: [dict1, dict2]
        [{
            'hyper-hidden_size':1
            'id':xx
        },{
            'hyper-xxx-xxx':1,
            'id':xx
        }]
    :param connector: str.
    :return:
        [{
            'hyper':{'hidden_size':1},
            'id':xxx
        }, {

        }]
    """
    def _expand_dict(keys, value):
        if len(keys)==1:
            return {keys[0]:value}
        else:
            return {keys[0]:_expand_dict(keys[1:], value)}

    logs = []
    for _dict in dicts:
        tmp = {}
        for key, value in _dict.items():
            merge(tmp, _expand_dict(key.split(connector), value), use_b=True)
        logs.append(tmp)
    return logs


def get_log_and_extra_based_on_config(log_reader, log_dir, log_config_name):
    """
    根据config文件读取log，并将extra里面的数据进行替换. 将重置log_reader的状态.

    :param log_reader: LogReader
    :param log_dir: str
    :param log_config_name: str
    :return: logs: [{}, {}];
             configs: {}, 包含配置文件中的所有内容
             extra_data:{}， 包含log_extra_data.txt的所有内容
    """
    log_dir = os.path.abspath(log_dir)
    log_config_path = os.path.join(log_dir, log_config_name)
    log_config_path = os.path.abspath(log_config_path)
    log_reader.set_log_dir(log_dir)
    configs = read_server_config(log_config_path)

    deleted_log_ids = configs['deleted_rows']

    logs = log_reader.read_logs(deleted_log_ids)
    if len(logs)==0:
        raise ValueError("No valid log found in {}.".format(log_dir))

    # read extra_data
    extra_data_path = os.path.join(log_dir, 'log_extra_data.txt')
    extra_data = {}
    if os.path.exists(extra_data_path):
        extra_data = read_extra_data(extra_data_path)

    # 将extra_data合并到log中
    extra_log_dict = {key:value for key,value in zip(list(extra_data.keys()),
                                                     expand_dict(list(extra_data.values()), connector='-'))}
    all_logs = []
    for log in logs:
        if log['id'] in extra_log_dict:
            extra_log = extra_log_dict[log['id']]
            log = merge(log, extra_log, use_b=True)
            all_logs.append(log)
        else:
            all_logs.append(log)
    for key, value in extra_log_dict.items():
        if 'id' in value and value['id'] not in deleted_log_ids: # 说明是用户自己手动加入的
            all_logs.append(value)

    # 根据过滤条件删除不需要的
    filtered_logs = []
    log_filter = LogFilter(filter_condition=configs['filter_condition'])
    for log in all_logs:
        flat_log = flatten_dict('', log)
        if not log_filter._filter_this_log_or_not(flat_log=flat_log,
                                                  ignore_not_exist=configs['settings']['Ignore_filter_condition_not_exist_log']):
            filtered_logs.append(log)

    return filtered_logs, configs, extra_data


def prepare_data(log_reader, log_dir, log_config_name, all_data=None): # 准备好需要的数据， 应该包含从log dir中读取数据
    """

    :param log_reader: 用于读取数据的Reader对象
    :param log_dir: str, 哪里是存放所有log的大目录
    :param log_config_path: 从哪里读取config
    :param all_data: dict

    :return:
    """
    print("Start preparing data...")
    # 1. 从log读取数据
    logs, configs, extra_data = get_log_and_extra_based_on_config(log_reader, log_dir, log_config_name)

    if all_data is None:
        all_data = {}
    if 'extra_data' not in all_data:
        all_data['extra_data'] = extra_data
    all_data.update(configs)
    # 2. 取出其他settings
    hidden_columns = all_data['hidden_columns']
    column_order = all_data['column_order']
    editable_columns = all_data['editable_columns']
    exclude_columns = all_data['exclude_columns']
    ignore_unchanged_columns = all_data['basic_settings']['ignore_unchanged_columns']
    str_max_length = all_data['basic_settings']['str_max_length']
    round_to = all_data['basic_settings']['round_to']

    # 3. 获取从extra_log来的数量
    num_extra_log = 0
    for log_id, log in extra_data.items():
        if 'id' in log:
            if log['id'] not in all_data['deleted_rows']:
                num_extra_log += 1

    new_all_data = generate_columns(logs=logs, hidden_columns=hidden_columns, column_order=column_order,
                                editable_columns=editable_columns,
                                exclude_columns=exclude_columns,
                                ignore_unchanged_columns=ignore_unchanged_columns,
                                str_max_length=str_max_length, round_to=round_to,
                                num_extra_log=num_extra_log)
    all_data.update(new_all_data)

    field_columns = {}
    for key, value in all_data['column_dict'].items():
        if 'field' in value:
            field_columns[key] = 1
    all_data['field_columns'] = field_columns

    return all_data


def save_all_data(all_data, log_dir, log_config_name, force_save=False):
    # 保存settings和extra文件, 会根据情况判断是否存储。
    if all_data['settings']['Save_settings'] or force_save:  # 如果需要保存
        log_config_path = os.path.join(log_dir, log_config_name)
        save_config(all_data, config_path=log_config_path)
        # save editable columns
        extra_data_path = os.path.join(log_dir, 'log_extra_data.txt')
        if len(all_data['extra_data']) != 0:
            save_extra_data(extra_data_path, all_data['extra_data']) # extra_data是一个dict。key为id，value为内容
        else:
            if os.path.exists(extra_data_path):
                os.remove(extra_data_path)
        print("Settings are saved to {}.".format(log_config_path))
