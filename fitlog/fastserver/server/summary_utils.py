
import os
import json
import numpy as np
from ...fastgit.committer import _colored_string
from .utils import flatten_dict
from numbers import Number
from ...fastlog.log_read import LogReader
from ..server.server_config import _get_config_names
from ..server.table_utils import get_log_and_extra_based_on_config
from itertools import groupby
from operator import itemgetter
from functools import partial
import traceback
from ..server.table_utils import merge as merge_use_b, expand_dict
from .table_utils import expand_dict
from .table_utils import generate_columns
from copy import deepcopy

def check_uuid_summary(gold_uuid, _uuid):
    if gold_uuid==_uuid:
        return None
    else:
        return {'status': 'fail',
                'msg': "It seems like your page is out-of-date, please refresh."}


def read_summary(root_log_dir:str, summary_name):
    """

    :param root_log_dir: 存放logs的地方。
    :param summary_name: str，summary的名称
    :return: {}不包含summary_name
    """
    summary_fp = os.path.join(root_log_dir, 'summaries', summary_name + '.summary')
    summary = {}
    if os.path.exists(summary_fp):
        with open(summary_fp, 'r', encoding='utf-8') as f:
            summary = json.loads(f.readline())
    return summary

def _get_all_summuries(root_log_dir:str):
    summary_dir = os.path.join(root_log_dir, 'summaries')
    summary_names = []
    if os.path.exists(summary_dir):
        filenames = os.listdir(summary_dir)
        for filename in filenames:
            if filename.endswith('.summary'):
                summary_names.append(os.path.splitext(filename)[0])
    return summary_names

def save_summary(root_log_dir, summary_name, summary):
    """
    保存summary到硬盘中

    :param root_log_dir:
    :param summary_name: str
    :param summary:
    :return:
    """
    summary_dir = os.path.join(root_log_dir, 'summaries')
    try:
        os.makedirs(summary_dir, exist_ok=True)
        with open(os.path.join(summary_dir, summary_name + '.summary'), 'w', encoding='utf-8') as f:
                f.write(json.dumps(summary))
    except Exception as e:
        print(_colored_string("Error happens when save summaries.", 'red'))
        print(e)
        return {'status':'fail', 'msg':'Fail to save your summaries.'}

def delete_summary(root_log_dir, summary_name):
    """
    删除summary
    :param root_log_dir:
    :param summary_name:
    :return:
    """
    summary_dir = os.path.join(root_log_dir, 'summaries')
    try:
        fp = os.path.join(summary_dir, summary_name + '.summary')
        if os.path.exists(fp):
            os.remove(fp)
        return True
    except Exception as e:
        print(_colored_string("Error happens when delete summary {}.".format(summary_name), 'red'))
        print(e)
        return False


def read_logs(log_name, root_log_dir, extra_data=None):
    # log_name可以为str(config_name), 或list[str]:每一项为一个log; root_log_dir是从哪里读取log
    log_reader = LogReader()
    if isinstance(log_name, str): # 传入的是实际上config_name
        config_names = _get_config_names(root_log_dir)
        if config_names.index(log_name) == -1:
            return {'status':'fail', 'msg':'There is no config named {}.'.format(log_name)}
        logs, configs, extra_data = get_log_and_extra_based_on_config(log_reader, root_log_dir,
                                                                      log_name)
        # 获取所有的hyper,other以及metric
    elif isinstance(log_name, list):
        log_names = log_name
        log_reader.set_log_dir(root_log_dir)
        logs = log_reader.read_certain_logs(log_names)
        if len(logs) != len(log_names):
            not_found_log = set(log_names) - set([log['id'] for log in logs])
            for log in not_found_log:
                if log not in extra_data:
                    print(_colored_string("The following logs are not found {}.".format(
                                list(not_found_log)), 'blue'))
        # 将extra_data合并到log中
        if extra_data==None:
            extra_data = {}
        extra_log_dict = {key: value for key, value in zip(list(extra_data.keys()),
                                                           expand_dict(list(extra_data.values()), connector='-'))}
        all_logs = []
        for log in logs:
            if log['id'] in extra_log_dict:
                extra_log = extra_log_dict[log['id']]
                log = merge_use_b(log, extra_log, use_b=True)
                all_logs.append(log)
            else:
                all_logs.append(log)
        for key, value in extra_log_dict.items():
            if 'id' in value and key in log_name:  # 说明是用户自己手动加入的
                all_logs.append(value)
        logs = all_logs
    else:
        return {'status':'fail', 'msg':"Unknown data source."}
    filtered_logs = logs
    # for log in logs:  # 排除用户自己加入的数据
    #     if re.match('^log_\d{8}_\d{6}$', log['id']):
    #         filtered_logs.append(log)
    return filtered_logs

def get_summary_selection_from_logs(logs):
    """

    :param logs: [{}, {}], nested的log记录
    :return:axis:[], metric:[]
    """
    axis_selections = {}
    metric_selections = {}
    for log in logs:
        flat_log = flatten_dict('', log)
        for key, value in flat_log.items():
            if key.startswith('other-'):
                axis_selections[key] = 1
            elif key.startswith('hyper-'):
                axis_selections[key] = 1
            elif key.startswith('metric-'):
                if key in metric_selections:
                    if not isinstance(value, Number):
                        try:
                            value = float(value)
                        except Exception as e:
                            print(_colored_string("Metric:{} has non-numeric value:{}.".format(key, value), 'red'))
                            metric_selections[key] = 0
                else:
                    if isinstance(value, Number):
                        metric_selections[key] = 1
                    else:
                        metric_selections[key] = 1
    metrics = []
    for key, value in metric_selections.items():
        if value==0:
            print(_colored_string("Metric:{} has non-numeric value.".format(key), 'red'))
        else:
            metrics.append(key)
    return list(axis_selections.keys()), metrics


def groupBy(data, key):
    """

    :param data: List[dict], 一级dict
    :param key: str，以哪个为key进行group
    :return: 可以看成[[key1, group1], [key2, group2]]
    """
    data.sort(key=lambda x:str(x[key]))
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
                print(_colored_string("Conflict in key:{} when merge:{}, {}".format(key, a, b), 'red'))
        else:
            a[key] = b[key]
    return a

def calculate_on_grouped_data(grouped_data, method):
    """
    给定需要在哪个key上计算，得到该key上method计算的值
    grouped_data: {'a': {'b' :[{'id':xx, 'f1':1.0}, {}, ...]}}, method=max, calculate_on='f1'
        -> {'a': {'b' :{'f1':1.0}}}

    :param grouped_data: nested dict, 最里层为list[dict]
    :param method: 在list[dict]进行操作，返回两个dict作为结果; 第一个是结果, 第二个是从哪些log计算得来
    :return: {} nested的group的数据结果, {} nested的group从哪里计算来的
    """
    data = {}
    data_sources = {}
    if isinstance(grouped_data, list):
        return method(grouped_data)
    else:
        for key, value in grouped_data.items():
            tmp1, tmp2 = calculate_on_grouped_data(value, method)
            if len(tmp1)==0:
                continue
            else:
                data[key] = tmp1
            if len(tmp2)==0:
                continue
            else:
                data_sources[key] = tmp2
    return data, data_sources


def _summary_eq(summary1, summary2):
    # 检查两个summary是否相等
    checked_keys = ['vertical', 'horizontals', 'method', 'criteria', 'results', 'result_maps']
    for key in checked_keys:
        if key in summary1 and key in summary2:
            if not summary1[key]==summary2[key]:
                return False
        elif key not in summary1 and key not in summary2:
            continue
        else:
            if key in summary1:
                if len(summary1[key])!=0:
                    return False
            if key in summary2:
                if len(summary2[key])!=0:
                    return False
    return True

def generate_summary_table(vertical, horizontals, method, criteria, results, result_maps, selected_data,
                     root_log_dir, extra_data, extra_summary):
    # extra_data: [{一级}]
    logs = read_logs(selected_data, root_log_dir, extra_data)
    if isinstance(logs, dict): # 发生了错误了
        return logs

    if method in ('avg', 'avg_std'):
        criteria = []

    # 将logs flat
    flat_logs = []
    for log in logs:
        flat_logs.append(flatten_dict('', log))

    # 检查是否所有的result都在
    check_results = {result:0 for result in results}
    check_criteria = {criterion:0 for criterion in criteria }
    for log in flat_logs:
        for result in check_results.keys():
            if result in log:
                check_results[result] = 1
        for criterion in check_criteria.keys():
            if criterion in log:
                check_criteria[criterion] = 1
    miss_criteria = []
    for key, value in check_criteria.items():
        if value!=1:
            miss_criteria.append(key)
    miss_results = []
    for key,value in check_results.items():
        if value!=1:
            miss_results.append(key)
    msg = ''
    if miss_criteria:
        msg += "Criterion:{} not found.".format(miss_criteria)
    if miss_results:
        msg += "Result:{} not found.".format(miss_results)
    if msg:
        return {'status':'fail', 'msg':msg}

    # 这里存在一个问题是如果result有两个，但映射成了同一个值; 还有种可能是需要的结果都没有
    result_map_dict = {key:value for key,value in zip(results, result_maps)}
    duplicate_maps = []
    no_result_log = []
    no_criterion_log = []
    for index, log in enumerate(flat_logs):
        catch = False  # 替换过一次
        # todo 如果max的key与result是一致的话，会出现问题
        copy_log = deepcopy(log)
        for result, mapped_name in result_map_dict.items():  #result是需要取出的值，mapped_name是映射为的name
            if result in log:
                if result!=mapped_name:
                    if mapped_name in log:  # 映射为了log中已经有的值
                        duplicate_maps.append((mapped_name, log['id']))
                    else:
                        log[mapped_name] = log[result]  # 进行映射
                        # log.pop(result)  # 为什么要pop出来？
                catch = True
        at_least_on_criterion = len(criteria)==0
        for criterion in criteria:
            if criterion in copy_log:
                at_least_on_criterion = True
        if not catch:
            no_result_log.append(index)
        if not at_least_on_criterion:
            no_criterion_log.append(index)
    if len(duplicate_maps)!=0:
        return {'status':'fail', 'msg':"Conflict mapped name, there already exist these names in the log."
                                       " Please change the following mapped names.".format(duplicate_maps)}

    if no_result_log:
        print(_colored_string("Ignore {} logs, since they have no result entry.".format(len(no_result_log)), 'red'))
    if no_criterion_log:
        print(_colored_string("Ignore {} logs, since they have no criterion entry.".format(len(no_criterion_log)), 'red'))
    deleted_log_index = list(set(no_result_log + no_criterion_log))
    deleted_log_index.sort(reverse=True)
    for index in deleted_log_index:
        flat_logs.pop(index)
    if not flat_logs:
        return {'status':'fail', 'msg':'No valid log. Refer to server log.'.format(results)}

    # 检查是否所有的vertical, horizontal都在
    grouped_columns = []
    if vertical:
        grouped_columns.append(vertical)
    if horizontals:
        grouped_columns.extend(horizontals)
    if not grouped_columns:
        return {'status':'fail', 'msg':'Empty vertical and horizontal.'.format(results)}
    else:
        targets = grouped_columns.copy()
        for log in flat_logs:
            for col in grouped_columns:
                if col in log and col in targets:
                    targets.remove(col)
                if len(targets)==0:
                    break
            if len(targets)==0:
                break
        if targets:
            return {"status":'fail', 'msg':'{} not found for vertical and horizontal.'.format(targets)}
    # 根据情况进行group

    # 1. 如果log中没有该group值就添加一个None
    for log in flat_logs:
        for column in grouped_columns:
            if column not in log:
                log[column] = 'SummaryNone'
    # 2. 然后进行group操作。
    groups = get_grouped_data(flat_logs, grouped_columns)

    # 3. 根据method进行计算
    if method=='avg':
        method = avg_method
    elif method=='max':
        method = partial(max_method, base_on=criteria)
    elif method=='min':
        method = partial(min_method, base_on=criteria)
    elif method=='avg_std':
        method = avg_std_method
    else:
        return {'status':'fail', 'msg':"Unsupported method {}.".format(method)}

    # 4. 获取结果
    try:
        grouped_results = {}
        grouped_sources = {}
        for mapped_name in result_maps:
            partial_method = partial(method, result_on=mapped_name)
            _dict, _dict_source  = calculate_on_grouped_data(groups, partial_method)
            merge(grouped_results, _dict)
            merge(grouped_sources, _dict_source)
    except Exception as e:
        print("Exception happens when calculate {}.".format(mapped_name))
        traceback.print_exc()
        return {'status':'fail', 'msg':"When calculate {}, the following error occurred:{}.".format(mapped_name,
                                                                                                    repr(e))}

    # 5. 使其分割为正确的一行一行的形式
    summary_results = []
    summary_sources = {}
    column_order = {}
    if vertical:
        index = 0
        field_name = vertical.split('-')[-1]
        column_order['id'] = 'EndOfOrder'
        column_order[field_name] = 'EndOfOrder'
        column_order['OrderKeys'] = ['id', field_name]
        for key, value in grouped_results.items():
            value[field_name] = key
            value['id'] = str(index)
            summary_results.append(value)
            summary_sources[str(index)] = flatten_dict('', grouped_sources[key])
            index += 1

    else:
        grouped_results['id'] = '0'
        summary_results = [grouped_results]
        summary_sources['0'] = flatten_dict('', grouped_sources)

    # 6. 加入extra_summary, 如果有的话
    summary_results.extend(expand_dict(extra_summary))

    results = generate_columns(summary_results, hidden_columns={'id':1}, column_order=column_order, editable_columns={},
                     exclude_columns={}, ignore_unchanged_columns=False,
                     str_max_length=20, round_to=6, num_extra_log=0)
    results['status'] = 'success'
    results['summary_sources'] = summary_sources
    return results


def avg_method(data, result_on):
    try:
        values = []
        for log in data:
            if result_on in log:
                values.append(float(log[result_on]))
        if len(values)==0:
            value = {}
            return value, {}
        else:
            value = np.mean(values)
            return {result_on: value}, {result_on:[log['id'] for log in data]}
    except Exception as e:
        print(_colored_string("Exception occurred when calculate mean for {}.".format(result_on), 'red'))
        try:
            print("When calculate on {}.".format(values))
        except:
            pass
        print(e)
        raise e

def avg_std_method(data, result_on):
    try:
        values = []
        for log in data:
            if result_on in log:
                values.append(float(log[result_on]))
        if len(values)==0:
            value = {}
            return value, {}
        else:
            value = '{:.6f}({:.6f})'.format(np.mean(values), np.std(values))
            return {result_on: value}, {result_on:[log['id'] for log in data]}
    except Exception as e:
        print(_colored_string("Exception occurred when calculate mean for {}.".format(result_on), 'red'))
        try:
            print("When calculate on {}.".format(log))
        except:
            pass
        print(e)
        raise e


def max_method(data, base_on, result_on):
    """

    :param data: list[dict]
    :param base_on: [], 根据哪个计算
    :param result_on: 使用它的值
    :return:
    """
    try:
        valid_logs = []
        for log in data:
            for key in base_on:
                if key in log:
                    log['SortedKey'] = float(log[key])
                    valid_logs.append(log)
                    break
        if len(valid_logs)>1:
            valid_logs.sort(key=itemgetter('SortedKey'), reverse=True)
            max_log = valid_logs[0]
        elif len(valid_logs)==1:
            max_log = valid_logs[0]
        else:
            max_log = {}
        if result_on in max_log:
            return {result_on:max_log[result_on]}, {result_on: [log['id'] for log in valid_logs]}
        else:
            return {}, {}
    except Exception as e:
        print(_colored_string("Exception occurred when calculate max for {}.".format(result_on), 'red'))
        print(e)
        raise e

def min_method(data, base_on, result_on):
    """

    :param data: list[dict]
    :param base_on: [], 根据哪个计算
    :param result_on: 使用它的值
    :return:
    """
    try:
        valid_logs = []
        for log in data:
            for key in base_on:
                if key in log:
                    log['SortedKey'] = float(log[key])
                    valid_logs.append(log)
                    break
        if len(valid_logs)>1:
            valid_logs.sort(key=itemgetter('SortedKey'))
            min_log = valid_logs[0]
        elif len(valid_logs)==1:
            min_log = valid_logs[0]
        else:
            min_log = {}
        if result_on in min_log:
            return {result_on:min_log[result_on]}, {result_on: [log['id'] for log in valid_logs]}
        else:
            return {}, {}
    except Exception as e:
        print(_colored_string("Exception occurred when calculate min for {}.".format(result_on), 'red'))
        print(e)
        raise e
