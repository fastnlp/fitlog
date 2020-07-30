
from ...fastlog.log_read import StandbyStepLogReader, MultiStandbyStepLogReader
from .utils import flatten_dict

from collections import defaultdict
import re
import random
from itertools import chain


class ChartStepLogHandler:
    def __init__(self, save_log_dir, uuid, round_to=6, max_steps=400, wait_seconds=60,
                 exclude_columns=None, max_no_updates=30):
        self.reader = StandbyStepLogReader(save_log_dir, uuid, wait_seconds, max_no_updates)
        self.reader.start()

        self._save_log_dir = save_log_dir
        self.uuid = uuid
        self.max_steps = max_steps
        self.round_to = round_to
        self.path2path = {}  #{'metric':dict, 'loss':dict}

        if exclude_columns is None:
            exclude_columns = {}
        else:
            assert isinstance(exclude_columns, dict)
        self.exclude_columns = exclude_columns

    def _add_path2path(self, key, value):
        path2spath = self.path2rpath(value)
        self.path2path[key] = path2spath
        return path2spath

    def read_single_update(self, filepaths, ranges):
        steps = self.reader.read_update_single_log(filepaths, ranges)
        data = {}
        for key, values in steps.items():# key为loss, metric; value为[{'step':, epoch:, loss:{}}],
            # [{'step':, epoch:, metric:{}}]
            if key in self.path2path:
                path2path = self.path2path[key]
            else:
                path2path = self._add_path2path(key, values[0])
            expanded_values = defaultdict(list)
            for v in values:
                expand_v = {}
                real_v = v[key]
                if not isinstance(real_v, dict):
                    real_v = {key: real_v}
                for _key in ['step', 'epoch']:
                    if _key in v:
                        expand_v[_key] = v[_key]
                real_v.pop('step', None)
                real_v.pop('epoch', None)
                _flat_v = flatten_dict('', real_v)
                for i_key, i_value in _flat_v.items():
                    if isinstance(i_value, str):
                        try:
                            i_value = float(i_value)
                        except:
                            continue
                    if isinstance(i_value, (float, int)):
                        if i_key not in path2path:
                            path2path = self._add_path2path(key, real_v)
                        short_i_key = path2path[i_key]
                        if short_i_key in self.exclude_columns:
                            continue
                        i_value = round(i_value, self.round_to)
                        i_expand_v = expand_v.copy()
                        i_expand_v['name'] = short_i_key
                        i_expand_v['value'] = i_value
                        expanded_values[short_i_key].append(i_expand_v)

            l_expanded_values = []
            for i_key in list(expanded_values.keys()):
                i_value = expanded_values[i_key]
                l_expanded_values.extend(i_value)
            data[key] = l_expanded_values
        return data

    def update_logs(self, only_once=False):
        # data: {'finish':(如果结束了有), 'metric': [{}, {}], 'loss':[{}, {}]}
        steps = self.reader.read_update(only_once)
        data = {}
        for key, values in steps.items():# key为loss, metric, value为[{'step':, epoch:, loss:{}或value}]
            # [{'step':, epoch:, metric:{}}]
            if key!='finish' and key!='total_steps':
                if key in self.path2path:
                    path2path = self.path2path[key]
                else:
                    path2path = self._add_path2path(key, values[0])
                expanded_values = defaultdict(list)
                for v in values:
                    expand_v = {}
                    real_v = v[key]
                    if not isinstance(real_v, dict):
                        real_v = {key: real_v}
                    for _key in ['step', 'epoch']:
                        if _key in v:
                            expand_v[_key] = v[_key]
                    real_v.pop('step', None)
                    real_v.pop('epoch', None)
                    _flat_v = flatten_dict('', real_v)
                    for i_key, i_value in _flat_v.items():
                        if isinstance(i_value, str):
                            try:
                                i_value = float(i_value)
                            except:
                                continue
                        if isinstance(i_value, (float, int)):
                            # TODO 可能需要精简一下路径长度， 比如BMESMetric之类的东西
                            if i_key not in path2path:
                                path2path = self._add_path2path(key, real_v)
                            short_i_key = path2path[i_key]
                            if short_i_key in self.exclude_columns:
                                continue
                            i_value = round(i_value, self.round_to)
                            i_expand_v = expand_v.copy()
                            i_expand_v['name'] = short_i_key
                            i_expand_v['value'] = i_value
                            expanded_values[short_i_key].append(i_expand_v)

                l_expanded_values = []
                for i_key in list(expanded_values.keys()):
                    i_value = expanded_values[i_key]
                    if len(i_value)>self.max_steps: # 不能超过一定的step
                        l_expanded_values.extend(i_value[-self.max_steps:])
                    else:
                        l_expanded_values.extend(i_value)
                data[key] = l_expanded_values
            else:
                data[key] = values
        return data

    def path2rpath(self, _dict):
        """
        比如两个value的path
            dev-BMESMetric-f1
            dev-BMESMEtric-pre
            test-BMESMetric-f1
        反着写(删除Metric):
            f1-BMES-dev
            pre-BMES-dev

        :param _dict: {'expanded_path': 'short_path'}
        :return:
        """
        paths = _get_dict_path(_dict)
        path2path = _reverse_path(paths)
        return path2path

def _get_dict_path(_dict, paths=None):
    # 给定一个dict, 返回所有的path，path以[[path], []]展示. 内容存到container中
    if paths==None:
        paths = []
    else:
        paths = paths.copy()
    new_paths = []
    for key, value in _dict.items():
        if isinstance(value, dict):
            _paths = _get_dict_path(value, paths + [key])
            new_paths.extend(_paths)
        else:
            new_paths.append(paths + [key])
    return new_paths

def _reverse_path(paths):
    """

    给定list的path,
        [['BMESF1Metric', 'f1'], ['BMESF1Metric'], ...]
    :param paths: {'BMESF1Metric':'f1-BMESF1Metric'}即把内容放到前面
    :return:
    """
    path2path = {}
    for path in paths:
        new_path = []
        for key in path:
            for span in re.finditer('[Mm]etric$', key):
                key = key[:span.start()]
            new_path.append(key)
        path2path['-'.join(path)] = '-'.join(reversed(new_path))
    return path2path

def _refine_path(paths):
    """
    给定list的path，将公共的部分删掉一些. 这里只处理完全一样深度的metric. 主要为了删除相同的metric_name
        [['metric', 'BMESF1MEtric', 'f1'], ['metric', 'BMESF1Metric'], ...]
    :param paths:
    :return:
    """
    if len(set(map(len, paths)))!=1:# 如果深度不同直接回去
        path2shortpath = {'-'.join(path):'-'.join(path) for path in paths}
    elif len(paths)==0:
        path2shortpath = {'-'.join(paths[0]): paths[0][-1]}
    else:
        delete_depths = []
        for depth in range(len(paths[0])):
            names = set()
            for path in paths:
                names.add(path[depth])
            if len(names)==1:
                delete_depths.append(depth)
        for i in range(len(paths)):
            for d in reversed(delete_depths):
                paths[i].pop(d)
        path2shortpath = {'-'.join(path): '-'.join(path) for path in paths}
    return path2shortpath

def _refine_logs(logs, max_points, round_to=6):
    if len(logs)<max_points:
        return logs

    groups = defaultdict(list)
    for log in logs:
        groups[log['name']].append(log)

    for group_name in list(groups.keys()):
        group = groups[group_name]
        if len(group)>max_points:
            downsample_ratio = max_points/len(group)
            group = [log for log in group if random.random()<downsample_ratio]
            groups[group_name] = group
    new_logs = list(chain(*groups.values()))

    return new_logs


class MultiChartStepLogHandler:
    def __init__(self, root_log_dir, logs, uuid, titles=None, round_to=6, wait_seconds=60, max_no_updates=30):
        """
        在multi_chart中使用的读取函数

        :param str root_log_dir: 从哪个folder读取
        :param list logs: 需要监控的logs，内容类似log_xxx_xxxx
        :param str uuid: multi page独特的uuid
        :param list[str] titles: 出现在这个list的对象需要包含在结果中, None是都包含所有
        :param int round_to:
        :param int wait_seconds: 多少秒没有新的请求就停止
        :param int max_no_updates: 多少次update没有新数据就停止
        """

        self.reader = MultiStandbyStepLogReader(root_log_dir, logs, uuid, wait_seconds, max_no_updates)
        self.reader.start()
        self.root_log_dir = root_log_dir
        self.uuid = uuid
        self.round_to = round_to
        self.titles = titles

    def update_logs(self, handler_names=('metric', 'loss')):
        """
        :param tuple(str) handler_names:

        :return: 返回值的结构如下
                {
                    metric-1: {
                        log_1: [
                            [value, step, epoch],
                            []
                        ]
                    }
                    ...
                    finished_logs: []
                }
        """
        results = self.reader.read_update(handler_names=handler_names)
        for key in list(results.keys()):
            value = results[key]
            if isinstance(value, dict):  # 防止删除了finished_logs
                if self.titles is not None and key not in self.titles:
                    results.pop(key)
                else:
                    for log_id, vs in value.items():
                        for v in vs:
                            # TODO 暂时不考虑inf nan的问题吧
                            v[0] = round(float(v[0]), self.round_to)
        return results


def _replace_nan_inf(value):
    if value == float('inf'):
        value = "Infinity"
    elif value == float('-inf'):
        value = "-Infinity"
    elif str(value) == 'nan':
        value = "NaN"
    return value


if __name__ == '__main__':
    a = {'test':{'F1SpanMetric': {'f1': 0.3606739335382445, 'pre': 0.6220669896180324}}, 'dev':{'F1SpanMetric': {'f1': 0.45963128728272284, 'pre1': 0.25299515839718356}}}

    paths = _get_dict_path(a)
    print(paths)
    print(_reverse_path(paths))

    print(flatten_dict('', a))
