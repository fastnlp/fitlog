import os
import re
import json
from collections import defaultdict
from typing import List
import threading
import time


class LogReader:
    """
    用于读取日志的类, 用于配合Table使用
    """
    
    def __init__(self):
        """
        self._line_counter里面的内容:{save_log_dir: {filename: (line_count, last_change_time)}}
        """
        self._log_dir = None
        self._ignore_null_loss_or_metric = True  # 如果loss和metric都是null的话，则忽略
        self._line_counter = defaultdict(lambda: None)  # 记住每个log读取到的line的数量以及修改时间
    
    def set_log_dir(self, log_dir: str):
        """
        设置 log 的存放位置
        """
        if not os.path.isdir(log_dir):
            raise RuntimeError("`{}` is not a valid directory.".format(log_dir))
        empty = True
        for _dir in os.listdir(log_dir):
            if is_dirname_log_record(os.path.join(log_dir, _dir)):
                empty = False
        if empty:
            raise RuntimeError("`{}` has no valid logs.".format(log_dir))
        
        self._log_dir = log_dir
        self._line_counter.clear()  # 删除记录，使得重新读取
    
    def read_logs(self, ignore_log_names: dict = None) -> List[dict]:
        """
        从日志存放路径读取日志. 只会读取有更新的log

        :param ignore_log_names: 如果包含在这个里面，就不会读取该log
        :return: 如果有内容或者有更新的内容，则返回一个 list，里面每个元素都是nested的dict.
            [{
                'id':
                'metric': {nested dict},
                'meta': {},
                ...
            },{
            }]
        """
        assert self._log_dir is not None, "You have to set log_dir first."
        if ignore_log_names is None:
            ignore_log_names = {}
        dirs = os.listdir(self._log_dir)
        logs = []
        for _dir in dirs:
            if _dir in ignore_log_names:
                continue
            dir_path = os.path.join(self._log_dir, _dir)
            if is_dirname_log_record(dir_path):
                _dict, file_stats = _read_save_log(dir_path, self._ignore_null_loss_or_metric,
                                                   self._line_counter[_dir])
                if len(_dict) != 0:
                    logs.append({'id': _dir, **_dict})
                    self._line_counter[_dir] = file_stats
        return logs

    def read_certain_logs(self, log_dir_names):
        """
        给定log的名称，只读取对应的log
        :param log_dir_names: list[str]
        :return: [{}, {}], nested的log
        """
        assert self._log_dir is not None, "You have to set log_dir first."
        logs = []
        for _dir in log_dir_names:
            dir_path = os.path.join(self._log_dir, _dir)
            if is_dirname_log_record(dir_path):
                _dict, file_stats = _read_save_log(dir_path, self._ignore_null_loss_or_metric,
                                                   self._line_counter[_dir])
                if len(_dict) != 0:
                    logs.append({'id': _dir, **_dict})
        return logs


def _read_save_log(_save_log_dir: str, ignore_null_loss_or_metric: bool = True, file_stats: dict = None):
    """
    给定一个包含metric.log, hyper.log, meta.log以及other.log的文件夹，返回一个包含数据的dict. 如果为null则返回空字典
    不读取loss.log, 因为里面的内容对table无意义。
    
    :param _save_log_dir: 日志存放的目录， 已经最后一级了，即该目录下应该包含metric.log等了
    :param ignore_null_loss_or_metric: 是否忽略metric和loss都为空的文件
    :param file_stats::
    
            {
                'meta.log': [current_line, last_modified_time],
                'hyper.log':[], 'metric.log':[], 'other.log':[]
            }
            
    :return:
        _dict: {'metric': {nested dict}, 'loss': {} }
        file_stats: {'meta.log': [current_line, last_modified_time],
                     'metric.log': [, ]} # 只包含有更新的文件的内容
    """
    try:
        filenames = ['meta.log', 'hyper.log', 'best_metric.log', 'other.log']
        if file_stats is None:
            file_stats = {}
        for filename in filenames:
            if filename not in file_stats:
                file_stats[filename] = [-1, -1]
        _dict = {}

        def _is_file_empty(fn):
            empty = True
            fp = os.path.join(_save_log_dir, fn)
            if os.path.exists(fp):
                with open(fp, 'r', encoding='utf-8') as f:
                    for line in f:
                        if len(line.strip()) != 0:
                            empty = False
                            break
            return empty

        if os.path.exists(os.path.join(_save_log_dir, 'metric.log')) and \
            not os.path.exists(os.path.join(_save_log_dir, 'best_metric.log')):  # 可能是之前的版本生成的, 适配一下
            with open(os.path.join(_save_log_dir, 'metric.log'), 'r', encoding='utf-8') as f, \
                open(os.path.join(_save_log_dir, 'best_metric.log'), 'w', encoding='utf-8') as f2:
                for line in f:
                    if not line.startswith('S'):  # 是best_metric
                        best_line = line
                        f2.write(best_line)

        empty = _is_file_empty('best_metric.log') and _is_file_empty('loss.log')
        
        if empty and ignore_null_loss_or_metric:
            return _dict, file_stats

        for filename in filenames:
            filepath = os.path.join(_save_log_dir, filename)
            last_modified_time = os.path.getmtime(filepath)
            if file_stats[filename][1] == last_modified_time:
                continue
            file_stats[filename][1] = last_modified_time
            start_line = file_stats[filename][0]
            __dict, end_line = _read_nonstep_log_file(filepath, start_line)
            file_stats[filename][0] = end_line
            _dict = merge(_dict, __dict, use_b=False)  # 在这里，需要以文件指定顺序，保留靠前的内容的值
    except Exception as e:
        print("Exception raised when read {}".format(os.path.abspath(_save_log_dir)))
        print(repr(e))
        raise e
    return _dict, file_stats


def is_log_dir_has_step(_save_log_dir: str) -> bool:
    """
    给定log_dir, 判断是否有step数据
    
    :param _save_log_dir 日志存放的目录
    :return: 是否有step数据
    """
    if not is_dirname_log_record(_save_log_dir):
        return False
    try:
        filenames = ['loss.log', 'metric.log']
        for filename in filenames:
            filepath = os.path.join(_save_log_dir, filename)
            if not os.path.exists(filepath):
                continue
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('S'):
                        return True
    except Exception as e:
        print("Exception raised when read {}".format(os.path.abspath(filepath)))
        return False
    return False


def _read_nonstep_log_file(filepath: str, start_line: int = 0) -> (dict, int):
    """
    给定一个filepath, 读取里面非Step: 开头的line，每一行为json，使用后面的内容覆盖前面的内容
    
    :param filepath: 读取文件的路径
    :param start_line: 从哪一行开始读取
    :return: 返回一个字典(没有内容为空)和最后读取到的行号
    """
    a = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        index = -1
        for index, line in enumerate(f):
            if index < start_line:
                continue
            if not line.startswith('S'):  # 读取非step的内容
                line = line.strip()
                try:
                    b = json.loads(line)  # TODO 如果含有非法字符(例如“!"#$%&'()*+,./:;<=>?@[\]^`{|}|~ ”)，导致前端无法显示怎么办？
                except:
                    print("Corrupted json format in {}, line:{}".format(filepath, line))
                    continue
                a = merge(a, b, use_b=True)
    return a, index + 1


def merge(a: dict, b: dict, use_b: bool = True) -> dict:
    """
    将两个dict recursive合并到a中，有相同key的，根据use_b判断使用哪个值
    
    :param a: 字典 a
    :param b: 字典 b
    :param use_b: 是否使用字典 b 的值
    :return: 返回字典 a
    """
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], use_b)
            elif use_b:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a


def is_dirname_log_record(dir_path: str) -> bool:
    """
    检查dir_path是否是一个合法的log目录。合法的log目录里必须包含meta.log。
    
    :param dir_path: 被检测的路径
    :return: 是否合法
    """
    if not os.path.isdir(dir_path):
        return False
    if len(re.findall(r'log_\d{8}_\d{6}$', dir_path)) != 0:
        filenames = ['meta.log']  # 至少要有meta.log表明这个是合法的log
        for filename in filenames:
            if not os.path.exists(os.path.join(dir_path, filename)):
                return False
        return True
    else:
        return False


def is_log_record_finish(save_log_dir: str) -> bool:
    """
    检测日志的记录是否已经结束
    
    :param save_log_dir: 日志存放的目录
    :return:
    """
    if is_dirname_log_record(save_log_dir):
        with open(os.path.join(save_log_dir, 'meta.log'), 'r', encoding='utf-8') as f:
            line = ''
            for line in f:
                pass
            if len(line.strip()) != 0:
                try:
                    _d = json.loads(line)
                except:
                    return False
                if 'state' in _d['meta'] and _d['meta']['state'] == 'finish':
                    return True
    return False


class StandbyStepLogReader(threading.Thread):
    """
    用于多线程读取日志的类. 配合画图使用的。
    
    :param save_log_dir: 日志存放的目录
    :param uuid: 用于唯一识别 Reader 的 uuid
    :param wait_seconds:  在文件关闭后再等待{wait_seconds}秒结束进程
    :param max_no_updates: 在{max_no_updates}秒内没有更新时结束进程
    """
    
    def __init__(self, save_log_dir: str, uuid: str, wait_seconds: int = 60, max_no_updates: int = 30):
        super().__init__()
        
        self.save_log_dir = save_log_dir
        self._file_handlers = {}
        
        self.uuid = uuid
        self._last_access_time = None
        # 如果这么长时间没有读取到新的数据，就认为是不需要再读取的了
        # 如果这么长时间没有再次调用，就关掉文件
        self._wait_seconds = wait_seconds
        
        self.unfinish_lines = {}  # 防止读写冲突, key: line
        self._stop_flag = False
        self._quit = False
        self._no_update_count = 0
        self.max_no_update = max_no_updates
        
        self._last_meta_md_time = None
        self._meta_path = os.path.join(self.save_log_dir, 'meta.log')
        self._total_steps = None
    
    def _create_file_handler(self):
        """
        检查是否有未加入的handler，有则加入进来
        
        :return:
        """
        for filename in ['metric.log', 'loss.log']:
            handler_name = filename.split('.')[0]
            if handler_name in self._file_handlers:
                continue
            filepath = os.path.join(self.save_log_dir, filename)
            handler = open(filepath, 'r', encoding='utf-8')
            self._file_handlers[handler_name] = handler
    
    def _is_finish_in_meta(self) -> bool:
        """
        检查是否已经在meta中写明了finish的状态了
        
        :return: bool
        """
        
        last_meta_md_time = os.path.getmtime(self._meta_path)
        if self._last_meta_md_time is None or self._last_meta_md_time != last_meta_md_time:
            with open(self._meta_path, 'r', encoding='utf-8') as f:
                line = ''
                for line in f:
                    pass
                line = line.strip()
                if len(line) != 0:
                    try:
                        _dict = json.loads(line)['meta']
                        if 'state' in _dict and _dict['state'] in ('finish', 'error'):
                            return True
                    except:
                        pass
        self._last_meta_md_time = last_meta_md_time
        return False
    
    @staticmethod
    def read_update_single_log(filepaths: List[str], ranges: dict) -> dict:
        """
        调用这个函数，获取filepaths中满足range_min, range_max的log
        
        :param filepaths: 完整的path路径
        :param ranges: {'metric':[min, max] }
        :return: 返回值的结构如下。loss这个list是进行了step排序的
                ::
                
                    {
                    loss: [dict('step':x, key:value, 'loss':{})],
                    metric:[dict('step':x, key:value, 'metric':)]
                    }
                
        """
        updates = defaultdict(list)
        
        for filepath in filepaths:
            filename = os.path.basename(filepath).split('.')[0]
            range_min = int(ranges[filename][0])
            range_max = int(ranges[filename][1])
            
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.endswith('\n'):  # 结尾不是回车，说明没有读完
                        pass
                    else:
                        if line.startswith('S'):
                            step = int(line[line.index(':') + 1:line.index('\t')])
                            if range_min <= step <= range_max:
                                line = line[line.index('\t') + 1:].strip()
                            try:
                                _dict = json.loads(line)
                                updates[filename].append(_dict)
                            except:
                                pass
                if filename in updates and len(updates[filename]) != 0:  # 对step排序，保证不要出现混乱
                    updates[filename].sort(key=lambda x: x['step'])
        return updates
    
    def read_update(self, only_once: bool = False) -> dict:
        """
        调用这个函数，获取新的更新
        
        :param only_once: 是否只读取内容一次
        :return: 返回值的结构如下
                ::
        
                    {
                        loss: [dict('step':x, key:value, 'loss':{})],
                        metric:[dict('step':x, key:value, 'metric':)],
                        finish:bool(not every time),
                        total_steps:int(only the first access)
                    }
                
        """
        updates = {}
        if not self._quit:
            flag = False
            self._create_file_handler()
            updates = defaultdict(list)
            if self._last_access_time is None:
                filepath = os.path.join(self.save_log_dir, 'progress.log')
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        line = f.readline()
                        try:
                            _dict = json.loads(line.strip())
                            if 'total_steps' in _dict:
                                self._total_steps = _dict['total_steps']
                                updates['total_steps'] = _dict['total_steps']
                        except:
                            pass
                flag = True
            self._last_access_time = time.time()
            for filename, handler in self._file_handlers.items():
                for line in handler.readlines():
                    if filename in self.unfinish_lines:
                        line = self.unfinish_lines.pop(filename) + line
                    if not line.endswith('\n'):  # 结尾不是回车，说明没有读完
                        self.unfinish_lines[filename] = line
                    else:
                        if line.startswith('S'):
                            line = line[line.index('\t') + 1:].strip()
                            try:
                                _dict = json.loads(line)
                                updates[filename].append(_dict)
                            except:
                                pass
                if filename in updates and len(updates[filename]) != 0:  # 对step排序，保证不要出现混乱
                    updates[filename].sort(key=lambda x: x['step'])
            if not only_once:
                if len(updates) == 0:
                    self._no_update_count += 1
                else:
                    self._no_update_count = 0
                if flag:
                    self.start()
            else:  # 如果确定只读一次，则直接关闭。应该是finish了
                self._close_file_handler()
                updates['finish'] = True
        if self._quit or self._no_update_count > self.max_no_update:
            updates = {'finish': True}
        if self._is_finish_in_meta():
            updates['finish'] = True
        if 'finish' in updates:
            self._quit = True
            self.stop()
        
        return updates
    
    def _close_file_handler(self):
        for key in list(self._file_handlers.keys()):
            handler = self._file_handlers[key]
            handler.close()
        self._file_handlers.clear()
    
    def stop(self):
        """
        如果手动停止某个任务
        
        :return:
        """
        self._stop_flag = True
        self._close_file_handler()
        count = 0
        while not self._quit:
            time.sleep(1)
            if count > 3:
                raise RuntimeError("Multi-thread bug here. It should not run twice.")
            count += 1
    
    def run(self):
        """
        重载了多线程的运行函数
        
        :return:
        """
        while time.time() - self._last_access_time < self._wait_seconds and not self._stop_flag and \
                self._no_update_count < self.max_no_update:
            time.sleep(0.5)
        self._quit = True
        self._close_file_handler()
