
import logging
import os
from datetime import datetime
import argparse
import json
import time
import re

from configparser import ConfigParser

from fitlog.fastlog.log_read import is_dirname_log_record
from fitlog.fastgit import committer


def check_debug(func):
    def wrapper(*args, **kwargs):
        if args[0]._debug:
            return
        else:
            return func(*args, **kwargs)
    return wrapper

def check_log_dir(func):
    def wrapper(*args, **kwargs):
        if not args[0].initialized and args[0]._default_log_dir is not None:
            args[0].set_log_dir(args[0]._default_log_dir)
        elif not args[0].initialized:
            raise RuntimeError("You have to call `logger.set_log_dir()` to set where to save log first.")
        return func(*args, **kwargs)
        # 1. 如果没有initialize, 说明还没有设置
        #   1.1 如果default_log_dir不为None，设置使用default_log_dir调用set_log_dir
        #       否则报错

    return wrapper

class Logger:
    def __init__(self):
        self.initialized = False
        self.save_on_first_metric_or_loss = True
        self._default_log_dir = None
        self._cache = []
        self._debug = False
        self.fit_id = None
        self.git_id = None

    def debug(self):
        """
        再引入logger之后就调用，本次运行不会记录任何东西。所有函数无任何效用
        :return:
        """
        self._debug = True

    @check_debug
    def commit(self, file, fit_msg=None):
        """

        :param file: path, 以该路径往上寻找.git或者.fit所在文件夹。一般传入__file__即可
        :param fit_msg: str, 针对该实验的说明
        :return:
        """
        msg = committer.commit(file=file, commit_message=fit_msg)
        if msg['status']==0:# 成功了
            config = committer.config
            self.fit_id = msg['msg']
            self.save_on_first_metric_or_loss = config.getboolean('log_settings', 'save_on_first_metric_or_loss')
            self._default_log_dir = os.path.join(committer.work_dir, config.get('log_settings', 'default_log_dir'))
        else:
            raise RuntimeError("It seems like you are not running under a folder governed by fitlog.\n" + msg['msg'])

    @check_debug
    def set_save_on_first_metric_or_loss(self, flag=True):
        """
        If False, then any record action will create log files. But usually this is not necessary.
        If True, only when at least one metric(calling logger.add_metric()) is recorded, it will create log files.
        :param flag:
        :return:
        """
        assert isinstance(flag, bool)
        self.save_on_first_metric_or_loss = flag

    @check_debug
    def set_log_dir(self, log_dir):
        """
        Have to be called before any other action can be taken. Specify the log directory, log filepath name will
            generate automatically.

        :param log_dir: directory path, where to save your log.
        :return:
        """
        if self.initialized:
            if self._log_dir!=log_dir:
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
        Only when write happens, create the directory.
        :return:
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

            formatter = logging.Formatter('%(message)s') # 只保存记录的时间与记录的内容
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

    @check_debug
    @check_log_dir
    def __add_meta(self):
        """
        add meta information into logger. Automatically generated by Logger

        :return:
        """
        # TODO 写入fit_id, git_id, git_info
        fit_id = None
        fit_msg = None
        if committer.last_commit!=None:
            fit_id = committer.last_commit[0]
            fit_msg = committer.last_commit[1]
        git_id = None
        git_msg = None
        res = committer.git_last_commit(self._log_dir)
        if res['status']==0:
            git_id = res['msg'][0]
            git_msg = res['msg'][1]
            self.git_id = res['msg'][0]

        _dict = {}
        for value, name in zip([fit_id, git_id, fit_msg, git_msg],
                               ['fit_id', 'git_id', 'fit_msg', 'git_msg']):
            if value != None:
                if 'id' in name:
                    value = value[:8]
                _dict[name] = value

        _dict["state"] = 'running'
        _dict = {'meta': _dict}
        self._write_to_logger(json.dumps(_dict), 'meta_logger')

    @check_debug
    @check_log_dir
    def finish(self):
        """
        Use to inform logger that the program ended as expected. This can be useful when you want to filter out
            unsuccessful experiments.
        :return:
        """
        if hasattr(self, 'meta_logger'):
            _dict = {'meta': {'state': 'finish'}}
            self._write_to_logger(json.dumps(_dict), 'meta_logger')
    @check_debug
    @check_log_dir
    def add_best_metric(self, value, name=None):
        """
        value put in this function will be placed in a column named 'metric'

        :param value: can be int, float, str, dict(it can be nested and have multiple keys, but all value should be
            int, float or str)
        :param name: str, what is your metric name, if your metric is (float, int, str), you need to specify this
            value. But if your metric is a dict, you can ignore this value, we will use the key as the metric name.
            Be careful when you log several datasets performance, you can use name to distinguish them.
        :return:
        """
        _dict = _parse_value(value, name=name, parent_name='metric')

        self._write_to_logger(json.dumps(_dict), 'metric_logger')

    @check_debug
    @check_log_dir
    def add_metric(self, value, step, name=None, epoch=None):
        """

        :param value: value: can be int, float, str, dict(it can be nested and have multiple keys, but all value should be
            int, float or str)
        :param step:int, used to align with loss
        :param name: str, if value is dict, it can be none.
        :param epoch: int, used when need to display in the front page.
        :return:
        """
        assert isinstance(step, int) and step>-1, "Only positive integer is allowed to be `step`."
        _dict = _parse_value(value, name, parent_name='metric')
        _dict['step'] = step
        if epoch is not None:
            assert isinstance(epoch, int) and epoch > -1, "Only positive integer is allowed to be `epoch`."
            _dict['epoch'] = epoch
        _str = json.dumps(_dict)
        _str = 'Step:{}\t'.format(step) + _str
        self._write_to_logger(_str, 'metric_logger')

    @check_debug
    @check_log_dir
    def add_loss(self, value, step, name, epoch=None):
        """

        :param value: value: can be int, float, str, dict(it can be nested and have multiple keys, but all value should be
            int, float or str)
        :param name: str,
        :param step:int, used to align with loss
        :param epoch: int, used when need to display in the front page.
        :return:
        """
        assert isinstance(step, int) and step>-1, "Only positive integer is allowed to be `step`."
        _dict = _parse_value(value, name, parent_name='loss')
        if epoch is not None:
            assert isinstance(epoch, int) and epoch > -1, "Only positive integer is allowed to be `epoch`."
            _dict['epoch'] = epoch
        _dict['step'] = step
        _str = json.dumps(_dict)
        _str = 'Step:{}\t'.format(step) + _str
        self._write_to_logger(_str, 'loss_logger') # {'loss': {}, 'step':xx, 'epoch':xx}

    @check_debug
    @check_log_dir
    def add_hyper(self, value, name=None):
        """
        value put in this function will be placed in a column named 'hyper'

        :param value: can be int, float, str, configparser, dict(it can be nested and have multiple keys, but all value
            should be int, float or str), namedtuple(namely results parsed by ArgumentParser)
        :param name: str, if value is float, int, str, this value is required.
        :return:
        """
        if isinstance(value, argparse.Namespace):
            value = vars(value)
            _check_dict_value(value)
        elif isinstance(value, ConfigParser):
            value = _convert_configparser_to_dict(value) # no need to check

        _dict = _parse_value(value, name=name, parent_name='hyper')

        self._write_to_logger(json.dumps(_dict), 'hyper_logger')

    @check_debug
    @check_log_dir
    def add_other(self, value, name=None):
        """
        value put in this function will be placed in the

        :param value: can be int, float, str, dict(it can be nested and have multiple keys, but all value should be
            int, float or str), namedtuple(namely results parsed by ArgumentParser)
        :param name: str, what is this value'name. If dict is passed, this value can be None.
        :return: use to align between different records. If None, value with the same name will be overwritten.
        """
        if name in ('meta', 'hyper', 'metric', 'loss') and not isinstance(value, dict):
            raise KeyError("Don't use {} as a name. Use logger.add_{}() to save it.".format(name, name))

        _dict = _parse_value(value, name=name, parent_name='other')
        self._write_to_logger(json.dumps(_dict), 'other_logger')

    @check_debug
    @check_log_dir
    def add_hyper_in_file(self, filepath):
        """
        Read parameters from a file. Like the follow example, it will extract equations between two "#######hyper"(at least 7,
            can have more) and transform into dict. Every parameter can have at most one line, if a value spans multiple
            line, it will only record the first line.
        demo.py:
        ```
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
        ```
        if you pass the filepath of demo.py to this function. it will extract parameter as the following dict
        {
            'lr': '0.01',
            'char_embed': '300'
            'word_embed': '300'
        } and add to `name`.

        :param filename: str.
        :return:
        """
        filepath = os.path.abspath(filepath)
        if not os.path.isfile(filepath):
            raise RuntimeError("{} is not a regular file.".format(filepath))
        if not filepath.endswith('.py'):
            raise RuntimeError("{} is not a python file.".format(filepath))
        _dict = {}
        between = False
        with open(filepath, 'r', encoding='utf-8') as f:
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
        if len(_dict)!=0:
            self.add_hyper(_dict)

    @check_debug
    @check_log_dir
    def add_progress(self, total_steps=None):
        """
        用于前端显示当前进度条。传入总的step数量
        :param total_steps: int, 总共有多少个step
        :return:
        """
        assert isinstance(total_steps, int) and total_steps>0
        if hasattr(self, '_total_steps'):
            raise RuntimeError("Cannot set total_steps twice.")
        self.total_steps = total_steps
        self._write_to_logger(json.dumps({"total_steps":total_steps}), 'progress_logger')

    @check_debug
    @check_log_dir
    def save(self):
        if len(self._cache)!=0:
            self._create_log_files()
            for value, logger_name in self._cache:
                logger = getattr(self, logger_name)
                logger.info(value)
            self._cache = []

    def _write_to_logger(self, _str, logger_name):
        assert isinstance(logger_name, str) and isinstance(_str, str)
        if self.save_on_first_metric_or_loss:
            if logger_name=='metric_logger' or logger_name=='loss_logger':
                self._create_log_files()
                self.save() # 将之前的内容存下来
        if hasattr(self, logger_name):
            logger = getattr(self, logger_name)
            logger.info(_str.replace('\n', ' '))
        else: # 如果还没有初始化就先cache下来
            self._cache.append([_str, logger_name])

def _convert_configparser_to_dict(config):
    _dict = {}
    for section in config.sections():
        __dict = {}
        options = config.options(section)
        for option in options:
            __dict[option] = config.get(section, option)
        _dict[section] = __dict

    return _dict


def _parse_value(value, name, parent_name=None):
    """
    检查传入的value是否是符合要求的。并返回dict
        (1) 如果value是基本类型，则name不为None
        (2) 如果value是dict类型，则保证所有value是可以转为(int, str, float)的
    :param value: int, float, str或者dict类型
    :param name:
    :param parent_name:
    :return:
    """
    if name is not None:
        assert isinstance(name, str), "name can only be `str` type, not {}.".format(name)
    _dict = {}

    if isinstance(value, (int, float, str)):
        if name==None:
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


def _check_dict_value(_dict, prefix=''):
    keys = list(_dict.keys())
    for key in keys:
        value = _dict[key]
        if isinstance(value, (int, float, str)):
            continue
        elif isinstance(value, dict):
            _check_dict_value(value, prefix=prefix+':'+key)
        elif 'torch.Tensor' in str(type(value)):
            try:
                value = value.item()
                _dict[key] = value
            except:
                raise RuntimeError("For {}. Tensor with only one element is allowed.".format(prefix+':'+key))
        elif 'numpy.ndarray' in str(type(value)):
            total_ele = 1
            for dim in value.shape:
                total_ele *= dim
            if total_ele!=1:
                raise RuntimeError("For {}. It should only have one element.".format(prefix+':'+key))
            _dict[key] = value.reshape(1)[0]
        else:
            raise TypeError("Only str, int, float, one element torch Tensor or numpy.ndarray"
                            " are allowed.")


logger = Logger()