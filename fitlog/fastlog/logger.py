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
import warnings
import numpy as np
import numbers

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
            raise RuntimeError("You have to call `logger.set_log_dir()` to set where to save log first.")
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
        self.fit_msg = None
        self.git_id = None
        self.git_msg = None
        
        self._log_dir = None  # 这是哪个大的log文件, 比如logs/
        self._save_log_dir = None  # 存在哪个文件内的，比如log_20191020_193021/。如果
    
    def debug(self, flag=True):
        """
        再引入logger之后就调用，本次运行不会记录任何东西。所有函数无任何效用
        
        :return:
        """
        self._debug = flag
    
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
            self.fit_id = committer.last_commit[0]
            self.fit_msg = committer.last_commit[1]
            self.default_log_dir = os.path.join(committer.work_dir, config.get('log_settings', 'default_log_dir'))
            self.save_on_first_metric_or_loss = config.getboolean('log_settings', 'save_on_first_metric_or_loss')
            if not self.save_on_first_metric_or_loss:
                self.create_log_dir()
        else:
            raise RuntimeError("It seems like you are not running under a folder governed by fitlog.\n" + msg['msg'])
    
    @_check_debug
    @_check_log_dir
    def create_log_dir(self):
        """
        默认是生成第一个loss或者metric的时候才会在设置的log文件夹下创建一个新的文件夹，如果需要在代码运行时就创建该文件夹，可以通过
            调用该接口。

        :return:
        """
        self._create_log_files()
    
    @_check_debug
    def set_log_dir(self, log_dir: str, new_log: bool=False):
        """
        设定log 文件夹的路径，在进行其它操作前必须先指定日志路径

        :param log_dir: log 文件夹的路径
        :param new_log: 是否开始新的一条log记录. 一般用于同一次实验需要记录多个数据集的performance
        :return:
        """
        if new_log:
            self._clear()

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
            warnings.warn("Append to an already exist log.")
            self._log_dir = os.path.dirname(log_dir)
            self._save_log_dir = log_dir
            self.initialized = True
            self.create_log_dir()
        else:
            self._log_dir = log_dir
        
        if not os.access(log_dir, os.W_OK):
            raise PermissionError("write is not allowed in `{}`. Check your permission.".format(log_dir))
        
        self.initialized = True
        try:
            if self.git_id is None:
                res = committer.git_last_commit_info(log_dir)
                if res['status'] == 0:
                    self.git_id = res['msg'][0]
                    self.git_msg = res['msg'][1]
        except BaseException as e:
            pass

        if not self.save_on_first_metric_or_loss:
            self.create_log_dir()

    def _clear(self):
        """
        内部函数，将logger置为未初始化
        :return:
        """
        # self._save()
        self.initialized = False
        self._cache = []
        for attr_name in ['total_steps']:
            if hasattr(self, attr_name):
                delattr(self, attr_name)
        for attr_name in ['_save_log_dir', '_log_dir']:
            setattr(self, attr_name, None)

        for logger_name in ['meta_logger', 'hyper_logger', 'metric_logger', 'other_logger', 'progress_logger',
                          'loss_logger', "best_metric_logger", "file_logger"]:
            if hasattr(self, logger_name):
                logger = getattr(self, logger_name)
                handlers = logger.handlers[:]
                for handler in handlers:
                    handler.close()
                    handler.flush()
                    logger.removeHandler(handler)
                delattr(self, logger_name)

    def _create_log_files(self):
        """
        创建日志文件
        """
        if not hasattr(self, 'meta_logger'):
            if self._save_log_dir is None:
                now = datetime.now().strftime('%Y%m%d_%H%M%S')
                self._save_log_dir = os.path.join(self._log_dir, 'log_' + now)
                while os.path.exists(self._save_log_dir):
                    time.sleep(1)
                    now = datetime.now().strftime('%Y%m%d_%H%M%S')
                    self._save_log_dir = os.path.join(self._log_dir, 'log_' + now)
                os.mkdir(self._save_log_dir)
            # prepare logger
            self.meta_logger = logging.getLogger('fitlog_meta')
            self.hyper_logger = logging.getLogger('fitlog_hyper')
            self.metric_logger = logging.getLogger('fitlog_metric')
            self.other_logger = logging.getLogger('fitlog_other')
            self.loss_logger = logging.getLogger('fitlog_loss')
            self.progress_logger = logging.getLogger('fitlog_progress')
            self.best_metric_logger = logging.getLogger('fitlog_best_metric')
            self.file_logger = logging.getLogger('fitlog_file')
            
            formatter = logging.Formatter('%(message)s')  # 只保存记录的时间与记录的内容
            meta_handler = logging.FileHandler(os.path.join(self._save_log_dir, 'meta.log'), encoding='utf-8')
            hyper_handler = logging.FileHandler(os.path.join(self._save_log_dir, 'hyper.log'), encoding='utf-8')
            metric_handler = logging.FileHandler(os.path.join(self._save_log_dir, 'metric.log'), encoding='utf-8')
            best_metric_handler = logging.FileHandler(os.path.join(self._save_log_dir, 'best_metric.log'), encoding='utf-8')
            loss_handler = logging.FileHandler(os.path.join(self._save_log_dir, 'loss.log'), encoding='utf-8')
            other_handler = logging.FileHandler(os.path.join(self._save_log_dir, 'other.log'), encoding='utf-8')
            progress_handler = logging.FileHandler(os.path.join(self._save_log_dir, 'progress.log'), encoding='utf-8')
            file_handler = logging.FileHandler(os.path.join(self._save_log_dir, 'file.log'), encoding='utf-8')
            
            for handler in [meta_handler, hyper_handler, metric_handler, other_handler, loss_handler, progress_handler,
                            best_metric_handler, file_handler]:
                handler.setFormatter(formatter)
            
            for _logger, _handler in zip([self.meta_logger, self.hyper_logger, self.metric_logger, self.other_logger,
                                    self.loss_logger, self.progress_logger, self.best_metric_logger, self.file_logger],
                                         [meta_handler, hyper_handler, metric_handler, other_handler, loss_handler,
                                          progress_handler, best_metric_handler, file_handler]):
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
        if self.fit_id is None: # 没有获取过
            if committer.last_commit is not None:
                self.fit_id = committer.last_commit[0]
                self.fit_msg = committer.last_commit[1]

        _dict = {}
        for value, name in zip([self.fit_id, self.git_id, self.fit_msg, self.git_msg],
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
    def finish(self, status:int=0):
        """
        使用此方法告知 fitlog 你的实验已经正确结束。你可以使用此方法来筛选出失败的实验。

        :param int status: 告知当前实验的状态。0: 结束了; 1: 发生了错误
        """
        if status not in (0, 1):
            raise ValueError("status only supports 0,1 to stand for 'finish','error'.")
        if hasattr(self, 'meta_logger'):
            if status==0:
                _dict = {'meta': {'state': 'finish'}}
            else:
                _dict = {'meta': {'state': 'error'}}
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
        
        self._write_to_logger(json.dumps(_dict), 'best_metric_logger')

    @_check_debug
    @_check_log_dir
    def add_to_file(self, value:Union[str, dict]):
        """
        将str记录到文件中，前端可以从网页跳转打开文件。记录是append到之前的记录之后

        :param value: 字符串类型的数据，将直接写到文件中
        :return:
        """
        assert isinstance(value, (str, dict)), "Only str or dict allowed, not {}.".format(type(value))
        if isinstance(value, dict):
            value = json.dumps(value, indent=2)
        self._write_to_logger(value, 'file_logger')

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
        用于添加 loss。用此方法添加的值，可以通过曲线看出去变化趋势。
        
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
    def add_hyper(self, value: Union[int, str, float, dict, argparse.Namespace, ConfigParser], name=None):
        """
        用于添加超参数。用此方法添加到值，会被放置在 hyper 这一列中

        :param value: 类型为 int, float, str, dict, argparse.Namespace(即ArgumentParser传入的内容), ConfigParser中的一种
                。如果类型为 dict，它的键的类型只能为 str，它的键值的类型可以为int, float, str 或符合同样条件的 dict
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
        :param name: 如果你传入 name 参数，你传入的 value 参数会被看做形如 {name:value} 的字典  
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
        从文件读取参数。如demo.py所示，两行"#######hyper"(至少5个#)之间的参数会被读取出来，并组成一个字典。每个变量最多只能出现在一行中，
        如果多次出现，只会记录第一次出现的值。demo.py::
        
            from numpy as np
            # do something
    
            ############hyper
            lr = 0.01 # some comments
            char_embed = word_embed = 300
    
            hidden_size = 100
            # num_layers = 3 # 这个值不会被记录，通过#注释掉的行将被忽略
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
                if len(re.findall('^#####+hyper$', line)) != 0:
                    between = not between
                elif between:
                    if len(line) != 0 and not line.startswith('#'):
                        line = re.sub(r'#[^#]*$', '', line).strip()  # 删除结尾的注释
                        # replace space before an after =
                        line = re.sub(r'\s*=\s*', '=', line)
                        values = line.split('=')
                        # 删除str开头结尾的'"
                        last_value = values[-1].rstrip("'").rstrip('"').lstrip("'").lstrip('"')
                        if last_value=='False':
                            last_value = False
                        elif last_value == 'True':
                            last_value = True
                        for value in values[:-1]:
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
        if hasattr(self, 'total_steps'):
            raise RuntimeError("Cannot set total_steps twice.")
        self.total_steps = total_steps
        self._write_to_logger(json.dumps({"total_steps": total_steps}), 'progress_logger')

    def set_rng_seed(self, rng_seed:int = None, random:bool = True, numpy:bool = True,
                     pytorch:bool=True, deterministic:bool=True):
        """
        设置模块的随机数种子。由于pytorch还存在cudnn导致的非deterministic的运行，所以一些情况下可能即使seed一样，结果也不一致
            需要在fitlog.commit()或fitlog.set_log_dir()之后运行才会记录该rng_seed到log中
        :param int rng_seed: 将这些模块的随机数设置到多少，默认为随机生成一个。
        :param bool, random: 是否将python自带的random模块的seed设置为rng_seed.
        :param bool, numpy: 是否将numpy的seed设置为rng_seed.
        :param bool, pytorch: 是否将pytorch的seed设置为rng_seed(设置torch.manual_seed和torch.cuda.manual_seed_all).
        :param bool, deterministic: 是否将pytorch的torch.backends.cudnn.deterministic设置为True
        """
        if rng_seed is None:
            import time
            import math
            rng_seed = int(math.modf(time.time())[0]*1000000)
        if random:
            import random
            random.seed(rng_seed)
        if numpy:
            try:
                import numpy
                numpy.random.seed(rng_seed)
            except:
                pass
        if pytorch:
            try:
                import torch
                torch.manual_seed(rng_seed)
                torch.cuda.manual_seed(rng_seed)
                torch.cuda.manual_seed_all(rng_seed)
                if deterministic:
                    torch.backends.cudnn.deterministic = True
            except:
                pass
        if self.initialized:
            self.add_other(rng_seed, 'rng_seed')
        os.environ['PYTHONHASHSEED'] = str(rng_seed)  # 为了禁止hash随机化，使得实验可复现。
        return rng_seed

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
        if self._save_log_dir is None:
            if logger_name in ('metric_logger', 'best_metric_logger', 'loss_logger'):
                self._create_log_files()
                self._save()  # 将之前的内容存下来
        if logger_name not in ('file_logger'):
            _str = re.sub('-(?!\d)', '_', _str.replace('\n', ' '))
        if hasattr(self, logger_name):
            logger = getattr(self, logger_name)
            logger.info(_str)
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
    
    if isinstance(value, (int, float, str, bool)) or value is None:
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
        if isinstance(value, (np.str, str)) or isinstance(value, numbers.Number) or value is None:
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


