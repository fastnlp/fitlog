import logging
import os
from datetime import datetime
import argparse
import json
import time
import re
from typing import Union, Dict
from configparser import ConfigParser

from .log_read import is_dirname_log_record
from ..fastgit import committer


def _check_debug(func):
    """
    函数闭包，只有非 debug 模式才会执行原始函数
    
    :param func: 原始函数，函数的第一个参数必须为 Logger 对象
    :return: 加上闭包后的函数
    """
    
    def wrapper(*args, **kwargs):
        if args[0]._debug:
            return
        else:
            return func(*args, **kwargs)
    
    return wrapper


def _check_log_dir(func):
    """
    函数闭包，检查原始函数执行所需的条件是否满足，只有满足才会执行
    
    1 如果没有initialize, 说明还没有设置
    
    2 如果default_log_dir不为None，设置使用default_log_dir调用set_log_dir
    
    3 否则报错
    
    :param func: 原始函数，函数的第一个参数必须为 Logger 对象
    :return: 加上闭包后的函数
    """
    
    def wrapper(*args, **kwargs):
        if not args[0].initialized and args[0].default_log_dir is not None:
            args[0].set_log_dir(args[0].default_log_dir)
        elif not args[0].initialized:
            raise RuntimeError("You have to call `logger.set_log_dir()` to set where to _save log first.")
        return func(*args, **kwargs)
    
    return wrapper


class Logger:
    """
    用于处理日志的类，fitlog 的核心
    """
    
    def __init__(self):
        self.initialized = False
        self.save_on_first_metric_or_loss = True
        self.default_log_dir = None
        self._cache = []
        self._debug = False
        self.fit_id = None
        self.git_id = None
        
        self._save_log_dir = None
        self._log_dir = None
    
    def debug(self):
        """
        再引入logger之后就调用，本次运行不会记录任何东西。所有函数无任何效用
        
        :return:
        """
        self._debug = True
    
    @_check_debug
    def commit(self, file: str, fit_msg: str = None):
        """
        调用 committer.commit 进行自动 commit

        :param file: 以该路径往上寻找.fitlog所在文件夹。一般传入__file__即可
        :param fit_msg: 针对该实验的说明
        :return:
        """
        msg = committer.commit(file=file, commit_message=fit_msg)
        if msg['status'] == 0:  # 成功了
            config = committer.config
            self.fit_id = msg['msg']
            self.save_on_first_metric_or_loss = config.getboolean('log_settings', 'save_on_first_metric_or_loss')
            self.default_log_dir = os.path.join(committer.work_dir, config.get('log_settings', 'default_log_dir'))
        else:
            raise RuntimeError("It seems like you are not running under a folder governed by fitlog.\n" + msg['msg'])
    
    @_check_debug
    def set_save_on_first_metric_or_loss(self, flag: bool = True):
        """
        是否只在 metric操作后创建 log 文件
        
            1 If False, then any record action will create log files. But usually this is not necessary.
            
            2 If True, only when at least one metric(calling logger.add_metric()) is recorded, it will create log files.
        
        :param flag:
        :return:
        """
        assert isinstance(flag, bool)
        self.save_on_first_metric_or_loss = flag
    
    @_check_debug
    def set_log_dir(self, log_dir: str):
        """
        设定log 文件夹的路径，在进行其它操作前必须先指定日志路径

        :param log_dir: log 文件夹的路径
        :return:
        """
        if self.initialized:
            if self._log_dir != log_dir:
                raise RuntimeError("Don't set log dir again.")
            else:
                return
        
        if not os.path.exists(log_dir):
            raise NotADirectoryError("`{}` is not exist.".format(log_dir))
        if not os.path.isdir(log_dir):
            raise FileExistsError("`{}` is not a directory.".format(log_dir))
        
        # prepare file directory
        if is_dirname_log_record(log_dir):
            print("Append to already exist log.")
            self._log_dir = os.path.dirname(log_dir)
            self._save_log_dir = log_dir
        else:
            self._log_dir = log_dir
        
        if not os.access(log_dir, os.W_OK):
            raise PermissionError("write is not allowed in `{}`. Check your permission.".format(log_dir))
        
        self.initialized = True
    
    def _create_log_files(self):
        """
        创建日志文件
        """
        if not hasattr(self, 'meta_logger'):
            if not hasattr(self, '_save_log_dir'):
                now = datetime.now().strftime('%Y%m%d_%H%M%S')
                self._save_log_dir = os.path.join(self._log_dir, 'log_' + now)
                while os.path.exists(self._save_log_dir):
                    time.sleep(1)
                    now = datetime.now().strftime('%Y%m%d_%H%M%S')
                    self._save_log_dir = os.path.join(self._log_dir, 'log_' + now)
                os.mkdir(self._save_log_dir)
            # prepare logger
            self.meta_logger = logging.getLogger('meta')
            self.hyper_logger = logging.getLogger('hyper')
            self.metric_logger = logging.getLogger('metric')
            self.other_logger = logging.getLogger('other')
            self.loss_logger = logging.getLogger('loss')
            self.progress_logger = logging.getLogger('progress')
            
            formatter = logging.Formatter('%(message)s')  # 只保存记录的时间与记录的内容
            meta_handler = logging.FileHandler(os.path.join(self._save_log_dir, 'meta.log'), encoding='utf-8')
            hyper_handler = logging.FileHandler(os.path.join(self._save_log_dir, 'hyper.log'), encoding='utf-8')
            metric_handler = logging.FileHandler(os.path.join(self._save_log_dir, 'metric.log'), encoding='utf-8')
            loss_handler = logging.FileHandler(os.path.join(self._save_log_dir, 'loss.log'), encoding='utf-8')
            other_handler = logging.FileHandler(os.path.join(self._save_log_dir, 'other.log'), encoding='utf-8')
            progress_handler = logging.FileHandler(os.path.join(self._save_log_dir, 'progress.log'), encoding='utf-8')
            
            for handler in [meta_handler, hyper_handler, metric_handler, other_handler, loss_handler, progress_handler]:
                handler.setFormatter(formatter)
            
            for _logger, _handler in zip([self.meta_logger, self.hyper_logger, self.metric_logger, self.other_logger,
                                          self.loss_logger, self.progress_logger],
                                         [meta_handler, hyper_handler, metric_handler, other_handler, loss_handler,
                                          progress_handler]):
                _handler.setLevel(logging.INFO)
                _logger.setLevel(logging.INFO)
                _logger.addHandler(_handler)
            
            self.__add_meta()
    
    @_check_debug
    @_check_log_dir
    def __add_meta(self):
        """
        logger自动调用此方法添加meta信息
        """
        fit_id = None
        fit_msg = None
        if committer.last_commit is not None:
            fit_id = committer.last_commit[0]
            fit_msg = committer.last_commit[1]
        git_id = None
        git_msg = None
        res = committer.git_last_commit(self._log_dir)
        if res['status'] == 0:
            git_id = res['msg'][0]
            git_msg = res['msg'][1]
            self.git_id = res['msg'][0]
        
        _dict = {}
        for value, name in zip([fit_id, git_id, fit_msg, git_msg],
                               ['fit_id', 'git_id', 'fit_msg', 'git_msg']):
            if value is not None:
                if 'id' in name:
                    value = value[:8]
                _dict[name] = value
        
        _dict["state"] = 'running'
        _dict = {'meta': _dict}
        self._write_to_logger(json.dumps(_dict), 'meta_logger')
    
    @_check_debug
    @_check_log_dir
    def finish(self):
        """
        使用此方法告知 fitlog 你的实验已经正确结束。你可以使用此方法来筛选出失败的实验。
        """
        if hasattr(self, 'meta_logger'):
            _dict = {'meta': {'state': 'finish'}}
            self._write_to_logger(json.dumps(_dict), 'meta_logger')
    
    @_check_debug
    @_check_log_dir
    def add_best_metric(self, value: Union[int, str, float, dict], name: str = None):
        """
        用于添加最好的 metric 。用此方法添加的值，会被显示在 metric 这一列中。

        :param value: 类型为 int, float, str, dict中的一种。如果类型为 dict，它的键的类型只能为 str，
                它的键值的类型可以为int, float, str 或符合同样条件的 dict
        :param name: 如果你传入的 value 不是字典，你需要传入 value 对应的名字。
        
        .. warning ::
            如果你在同时记录多个数据集上的performance, 请注意使用不同的名称进行区分

        """
        _dict = _parse_value(value, name=name, parent_name='metric')
        
        self._write_to_logger(json.dumps(_dict), 'metric_logger')
    
    @_check_debug
    @_check_log_dir
    def add_metric(self, value: Union[int, str, float, dict], step: int, name: str = None, epoch: int = None):
        """
        用于添加 metric 。用此方法添加的值，会被记录在 metric 这一列中
        
        :param value: 类型为 int, float, str, dict中的一种。如果类型为 dict，它的键的类型只能为 str，
                它的键值的类型可以为int, float, str 或符合同样条件的 dict
        :param step: 用于和 loss 对应的 step
        :param name: 如果你传入的 value 不是字典，你需要传入 value 对应的名字
        :param epoch: 前端显示需要记录 epoch
        :return:
        """
        assert isinstance(step, int) and step > -1, "Only positive integer is allowed to be `step`."
        _dict = _parse_value(value, name, parent_name='metric')
        _dict['step'] = step
        if epoch is not None:
            assert isinstance(epoch, int) and epoch > -1, "Only positive integer is allowed to be `epoch`."
            _dict['epoch'] = epoch
        _str = json.dumps(_dict)
        _str = 'Step:{}\t'.format(step) + _str
        self._write_to_logger(_str, 'metric_logger')
    
    @_check_debug
    @_check_log_dir
    def add_loss(self, value: Union[int, str, float, dict], step: int, name: str = None, epoch: int = None):
        """
        用于添加 loss。用此方法添加的值，会被记录在 loss 这一列中
        
        :param value: 类型为 int, float, str, dict中的一种。如果类型为 dict，它的键的类型只能为 str，
                它的键值的类型可以为int, float, str 或符合同样条件的 dict
        :param step: 用于和 loss 对应的 step
        :param name: 如果你传入的 value 不是字典，你需要传入 value 对应的名字
        :param epoch: 前端显示需要记录 epoch
        :return:
        """
        assert isinstance(step, int) and step > -1, "Only positive integer is allowed to be `step`."
        _dict = _parse_value(value, name, parent_name='loss')
        if epoch is not None:
            assert isinstance(epoch, int) and epoch > -1, "Only positive integer is allowed to be `epoch`."
            _dict['epoch'] = epoch
        _dict['step'] = step
        _str = json.dumps(_dict)
        _str = 'Step:{}\t'.format(step) + _str
        self._write_to_logger(_str, 'loss_logger')  # {'loss': {}, 'step':xx, 'epoch':xx}
    
    @_check_debug
    @_check_log_dir
    def add_hyper(self, value: Union[int, str, float, dict], name=None):
        """
        用于添加超参数。用此方法添加到值，会被放置在 hyper 这一列中

        :param value: 类型为 int, float, str, dict中的一种。如果类型为 dict，它的键的类型只能为 str，
                它的键值的类型可以为int, float, str 或符合同样条件的 dict
        :param name: 如果你传入的 value 不是字典，你需要传入 value 对应的名字
        :return:
        """
        if isinstance(value, argparse.Namespace):
            value = vars(value)
            _check_dict_value(value)
        elif isinstance(value, ConfigParser):
            value = _convert_configparser_to_dict(value)  # no need to check
        
        _dict = _parse_value(value, name=name, parent_name='hyper')
        
        self._write_to_logger(json.dumps(_dict), 'hyper_logger')
    
    @_check_debug
    @_check_log_dir
    def add_other(self, value: Union[int, str, float, dict], name: str = None):
        """
        用于添加其它参数

        :param value: 类型为 int, float, str, dict中的一种。如果类型为 dict，它的键的类型只能为 str，
                它的键值的类型可以为int, float, str 或符合同样条件的 dict
        :param name: 参数的名字，当value不是字典时需要传入
        :return:
        """
        if name in ('meta', 'hyper', 'metric', 'loss') and not isinstance(value, dict):
            raise KeyError("Don't use {} as a name. Use logger.add_{}() to _save it.".format(name, name))
        
        _dict = _parse_value(value, name=name, parent_name='other')
        self._write_to_logger(json.dumps(_dict), 'other_logger')
    
    @_check_debug
    @_check_log_dir
    def add_hyper_in_file(self, file_path: str):
        """
        从文件读取参数。如demo.py所示，两行"#######hyper"之间的参数会被读取出来，并组成一个字典。每个变量最多只能出现在一行中，
        如果多次出现，只会记录第一次出现的值。demo.py::
        
            from numpy as np
            # do something
    
            ############hyper
            lr = 0.01 # some comments
            char_embed = word_embed = 300
    
            hidden_size = 100
            ....
            ############hyper
    
            # do something
            model = Model(xxx)
        
        如果你把 demo.py 的文件路径传入此函数，会转换出如下字典，并添加到参数中::
        
            {
                'lr': '0.01',
                'char_embed': '300'
                'word_embed': '300'
                'hidden_size': '100'
            }
        

        :param file_path: 文件路径
        :return:
        """
        file_path = os.path.abspath(file_path)
        if not os.path.isfile(file_path):
            raise RuntimeError("{} is not a regular file.".format(file_path))
        if not file_path.endswith('.py'):
            raise RuntimeError("{} is not a python file.".format(file_path))
        _dict = {}
        between = False
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if len(re.findall('^#######+hyper$', line)) != 0:
                    between = not between
                elif between:
                    if len(line) != 0 and not line.startswith('#'):
                        line = re.sub('#[^#]*$', '', line).strip()  # 删除结尾的注释
                        # replace space before an after =
                        line = re.sub('\s*=\s*', '=', line)
                        values = line.split('=')
                        last_value = values[-1].rstrip("'").rstrip('"').lstrip("'").lstrip('"')
                        for value in values[:-1]:
                            # 删除str开头的'"
                            _dict[value] = last_value
        if len(_dict) != 0:
            self.add_hyper(_dict)
    
    @_check_debug
    @_check_log_dir
    def add_progress(self, total_steps: int = None):
        """
        用于前端显示当前进度条。传入总的step数量
        
        :param total_steps: int, 总共有多少个step
        :return:
        """
        assert isinstance(total_steps, int) and total_steps > 0
        if hasattr(self, '_total_steps'):
            raise RuntimeError("Cannot set total_steps twice.")
        self.total_steps = total_steps
        self._write_to_logger(json.dumps({"total_steps": total_steps}), 'progress_logger')
    
    @_check_debug
    @_check_log_dir
    def _save(self):
        if len(self._cache) != 0:
            self._create_log_files()
            for value, logger_name in self._cache:
                logger = getattr(self, logger_name)
                logger.info(value)
            self._cache = []
    
    def _write_to_logger(self, _str: str, logger_name: str):
        """
        把记录的内容写到logger里面`
        
        :param _str: 要记录的内容
        :param logger_name: 所用logger的名称
        :return:
        """
        assert isinstance(logger_name, str) and isinstance(_str, str)
        if self.save_on_first_metric_or_loss:
            if logger_name == 'metric_logger' or logger_name == 'loss_logger':
                self._create_log_files()
                self._save()  # 将之前的内容存下来
        if hasattr(self, logger_name):
            logger = getattr(self, logger_name)
            logger.info(_str.replace('\n', ' '))
        else:  # 如果还没有初始化就先cache下来
            self._cache.append([_str, logger_name])


def _convert_configparser_to_dict(config: ConfigParser) -> dict:
    """
    将ConfigParser类型的对象转成字典
    
    :param config: 代转换的对象
    :return: 转换成的字典
    """
    _dict = {}
    for section in config.sections():
        __dict = {}
        options = config.options(section)
        for option in options:
            __dict[option] = config.get(section, option)
        _dict[section] = __dict
    
    return _dict


def _parse_value(value: Union[int, str, float, dict], name: str, parent_name: str = None) -> dict:
    """
    检查传入的value是否是符合要求的。并返回dict
    
    1 如果value是基本类型，则name不为None
    2 如果value是dict类型，则保证所有value是可以转为(int, str, float)的
    
    :param value: int, float, str或者dict类型
    :param name:
    :param parent_name:
    :return:
    """
    if name is not None:
        assert isinstance(name, str), "name can only be `str` type, not {}.".format(name)
    _dict = {}
    
    if isinstance(value, (int, float, str)):
        if name == None:
            raise RuntimeError("When value is {}, you must pass `name`.".format(type(value)))
        if parent_name != None:
            _dict = {parent_name: {name: value}}
    elif isinstance(value, dict):
        _check_dict_value(value)
    if parent_name != None and name != None:
        _dict = {parent_name: {name: value}}
    elif parent_name != None:
        _dict = {parent_name: value}
    elif name != None:
        _dict = {name: value}
    else:
        _dict = value
    return _dict


def _check_dict_value(_dict: dict, prefix: str = ''):
    """
    递归检查字典中任意字段的值是否符合要求
    
    :param _dict: 被检查的字典
    :param prefix: 递归时键值的前缀
    :return:
    """
    keys = list(_dict.keys())
    for key in keys:
        value = _dict[key]
        if isinstance(value, (int, float, str)):
            continue
        elif isinstance(value, dict):
            _check_dict_value(value, prefix=prefix + ':' + key)
        elif 'torch.Tensor' in str(type(value)):
            try:
                value = value.item()
                _dict[key] = value
            except:
                raise RuntimeError("For {}. Tensor with only one element is allowed.".format(prefix + ':' + key))
        elif 'numpy.ndarray' in str(type(value)):
            total_ele = 1
            for dim in value.shape:
                total_ele *= dim
            if total_ele != 1:
                raise RuntimeError("For {}. It should only have one element.".format(prefix + ':' + key))
            _dict[key] = value.reshape(1)[0]
        else:
            raise TypeError("Only str, int, float, one element torch Tensor or numpy.ndarray"
                            " are allowed.")


