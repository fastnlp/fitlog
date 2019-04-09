

import os
import re
import json

def read_logs(log_dir, ignore_null_metric=True):
    """
    传入log_dir返回List[Dict]
    :param log_dir: path, where to read log
    :param ignore_null_metric: bool, 如果metric.log为空, 则跳过
    :return: List[Dict], 每个dict对象是一次实验的记录
    """
    dirs = os.listdir(log_dir)
    logs = []
    for _dir in dirs:
        dir_path = os.path.join(log_dir, _dir)
        if is_dirname_log_record(dir_path):
            _dict = _read_save_log(dir_path, ignore_null_metric)
            if len(_dict)!=0:
                logs.append({'id':_dir, **_dict})
    return logs


def _read_save_log(_save_log_dir, ignore_null_metric=True):
    """
    给定一个包含metric.log, hyper.log, meta.log以及other.log的文件夹，返回一个包含数据的dict. 如果为null则返回空字典

    :param _save_log_dir: 从哪里读取log
    :param ignore_null_metric: 是否metric为空的文件
    :return:
    """
    try:
        filenames = ['meta.log', 'hyper.log', 'metric.log', 'other.log']
        empty = True
        _dict = {}
        with open(os.path.join(_save_log_dir, 'metric.log'), 'r', encoding='utf-8') as f:
            for line in f:
                if len(line.strip())!=0:
                    empty = False

        if empty and ignore_null_metric:
            return _dict

        for filename in filenames:
            filepath = os.path.join(_save_log_dir, filename)
            __dict = _read_log_file(filepath)
            _dict = merge(_dict, __dict)
    except Exception as e:
        print("Exception raised when read {}".format(os.path.abspath(filepath)))
        raise e
    return _dict

def _read_log_file(filepath):
    """
    给定一个filepath, 读取里面的内容，没一行为json，使用后面的内容覆盖前面的内容
    :param filepath: str
    :return: dict.没有内容为空
    """
    a = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            b = json.loads(line)
            a = merge(a, b)
    return a


def merge(a, b, path=None):
    "merges b into a"
    # 将两个dict recursive合并到a中，有相同key的，以a为准
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
        else:
            a[key] = b[key]
    return a


def is_dirname_log_record(dir_path):
    """
    检查dir_path是否是一个合法的log目录。里面必须包含meta.log, hyper.log, metric.log, other,log
    :param dir_path:
    :return:
    """
    if not os.path.isdir(dir_path):
        return False
    if len(re.findall('log_\d+_\d+$', dir_path))!=0:
        filenames = ['meta.log', 'hyper.log', 'metric.log', 'other.log']
        for filename in filenames:
            if not os.path.exists(os.path.join(dir_path, filename)):
                return False
        return True
    else:
        return False

