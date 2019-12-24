"""
fitlog是一款集成了自动版本管理和自动日志记录两种功能的 Python 包，它可以帮助你在进行实验时方便地保存当前的代码、参数和结果。
fitlog提供给用户的 API 有如下几个：

"""
__all__ = ["commit", "set_log_dir", "finish", "add_best_metric", "add_metric", "add_loss", "add_hyper", "add_other",
           "add_to_line", "set_rng_seed", "add_hyper_in_file", "get_commit_id", "get_fit_id"]
from .fastlog import logger as _logger
from .fastgit import Committer, committer as _committer
from typing import Union
import argparse
from configparser import ConfigParser

__version__ = '0.3.1'


def get_commit_id(file):
    """用户用此命令获取上一次 Git 记录的 id, 期望的使用方法如下::
        
        id = fitlog.get_commit_id(__file__)
        
    :param file: 以该路径往上寻找.fitlog所在文件夹。一般传入__file__即可:
    :return: Git 的上次记录的 commit-id 的前七位；错误时返回 `error`
    """
    work_dir = _committer._find_config_file(file)
    res = Committer.git_last_commit_info(work_dir)
    if res['status'] == 0:
        return res['msg'][0]
    else:
        return 'error'


def get_fit_id(file):
    """用户用此命令获取上一次 fitlog 自动记录 commit 的 id, 期望的使用方法如下::
        
        id = fitlog.get_fit_id(__file__)
        
    
    :param file: 以该路径往上寻找.fitlog所在文件夹。一般传入__file__即可
    :return: Fitlog 的上次自动记录的 commit-id 的前七位；错误时返回 `error`
    """
    work_dir = _committer._find_config_file(file)
    res = Committer.fit_last_commit_info(work_dir)
    if res['status'] == 0:
        return res['msg'][0]
    else:
        return 'error'


def commit(file: str, fit_msg: str = None):
    """
    用户用此命令进行自动 commit, 期望的使用方法如下::
        
        import fitlog
        
        fitlog.commit(__file__)
        \"\"\"
        Your training code
        \"\"\"
        fitlog.finish()

    :param file: 以该路径往上寻找.fitlog所在文件夹。一般传入__file__即可
    :param fit_msg: 针对该实验的说明
    """
    _logger.commit(file, fit_msg)


def set_log_dir(log_dir: str, new_log:bool=False):
    """
    设定log 文件夹的路径(在进行其它操作前必须先指定日志路径)。如果你已经顺利执行了 fitlog.commit()命令，
    log 文件夹会自动设定为.fitconfig 文件中的 default_log_dir 字段的值。在某些情况下，可能需要继续往同
    一个log中写入数据(比如继续训练之前以及保存的模型)，可以通过将log_dir设置为具体的log名。但需要保证
    step的顺序与之前已有的内容是不冲突的，因为相同的step在fitlog中是覆盖的。

    Example::

        # 假设当前的文件结构为
        # logs/
        #    log_20190417_140311
        #    ...
        # main.py
        #以下是main.py中三种设置log位置的方式
        fitlog.commit() # 如果commit成功，则不需要设置logs文件夹了
        fitlog.set_log_dir('logs/') # 设置log文件夹为'logs/', fitlog在每次运行的时候会默认以时间戳的方式在里面生成新的log
        fitlog.set_log_dir('logs/log_20190417_140311') # fitlog将log继续写入到log_20190417_140311里。

    :param log_dir: log 文件夹的路径
    :param new_log: 是否重新创建一个log，仅在同一次python启动但是需要记录多个log时使用(但是只能分阶段地用，即同一时间
        只会有一个logger存在，设置new_log为True时，仅仅是开了一个新的logger，但同时前一个就关闭了。)同一次启动中fit_id以及
        git_id只会在第一次启动时获取，之后的新log只是使用第一次提交的fit_id与git_id
    """
    _logger.set_log_dir(log_dir, new_log)


def debug(flag=True):
    """
    调用该方法之后，所有的fitlog方法都不会产生任何作用。可用于调试代码时避免输出大量无用的信息。

    Example::

        fitlog.debug()
        fitlog.commit()
        fitlog.add_metric(0.3, f1)

    由于有fitlog.debug(), commit()和add_metric()都不会实际执行的。

    :return:
    """
    _logger.debug(flag=flag)


def finish(status: int = 0):
    """
        使用此方法告知 fitlog 你的实验已经正确结束。你可以使用此方法来筛选出失败的实验。

        :param int status: 告知当前实验的状态。0: 结束了; 1: 发生了错误
    """
    _logger.finish(status)


def add_metric(value: Union[int, str, float, dict], step: int, name: str = None, epoch: int = None):
    """
    用于添加 metric 。用此方法添加的值不会显示在表格中，但可以在单次训练的详情曲线图中查看。

    :param value: 类型为 int, float, str, dict中的一种。如果类型为 dict，它的键的类型只能为 str，
            它的键值的类型可以为int, float, str 或符合同样条件的 dict
    :param step: 用于和 loss 对应的 step
    :param name: 如果你传入 name 参数，你传入的 value 参数会被看做形如 {name:value} 的字典
    :param epoch: 前端显示需要记录 epoch
    :return:
    """
    _logger.add_metric(value, step, name, epoch)


def add_loss(value: Union[int, str, float, dict], step: int, name: str = None, epoch: int = None):
    """
    用于添加 loss。用此方法添加的值不会显示在表格中，但可以在单次训练的详情曲线图中查看。

    :param value: 类型为 int, float, str, dict中的一种。如果类型为 dict，它的键的类型只能为 str，
            它的键值的类型可以为int, float, str 或符合同样条件的 dict
    :param step: 用于和 loss 对应的 step
    :param name: 如果你传入 name 参数，你传入的 value 参数会被看做形如 {name:value} 的字典
    :param epoch: 前端显示需要记录 epoch
    :return:
    """
    _logger.add_loss(value, step, name, epoch)


def add_best_metric(value: Union[int, str, float, dict], name: str = None):
    """
    用于添加最好的 metric 。用此方法添加的值，会被显示在表格中的 metric 列及其子列中。相同key的内容将只保留最后一次传入的值。

    :param value: 类型为 int, float, str, dict中的一种。如果类型为 dict，它的键的类型只能为 str，
            它的键值的类型可以为int, float, str 或符合同样条件的 dict
    :param name: 如果你传入 name 参数，你传入的 value 参数会被看做形如 {name:value} 的字典

    .. warning ::
        如果你在同时记录多个数据集上的performance, 请注意使用不同的名称进行区分

    """
    _logger.add_best_metric(value, name)


def add_hyper(value: Union[int, str, float, dict, argparse.Namespace, ConfigParser], name=None):
    """
    用于添加超参数。用此方法添加到值，会被放置在表格中的 hyper 列及其子列中

    :param value: 类型为 int, float, str, dict, argparse.Namespace(即ArgumentParser传入的内容), ConfigParser中的一种
            。如果类型为 dict，它的键的类型只能为 str，它的键值的类型可以为int, float, str 或符合同样条件的 dict
    :param name: 如果你传入 name 参数，你传入的 value 参数会被看做形如 {name:value} 的字典
    :return:
    """
    _logger.add_hyper(value, name)


def add_hyper_in_file(file_path: str):
    """
    从文件读取参数。如下面的文件所示，两行"#####hyper"(至少5个#)之间的参数会被读取出来，并组成一个字典。每个变量最多只能出现在一行中，
    如果多次出现，只会记录第一次出现的值。demo.py::
    
        from numpy as np
        import fitlog
        # do something

        fitlog.add_hyper_in_file(__file__)  # 会把本python文件的hyper加入进去
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

    :param file_path: 文件路径。如果是读取本python文件中的hyper parameter可以直接fitlog.add_hyper_in_file(__file__)
    """
    _logger.add_hyper_in_file(file_path)


def add_other(value: Union[int, str, float, dict], name: str = None):
    """
    用于添加其它参数。用此方法添加到值，会被放置在表格中的 other 列及其子列中。相同key的内容将只保留最后一次传入的值。

    :param value: 类型为 int, float, str, dict中的一种。如果类型为 dict，它的键的类型只能为 str，
            它的键值的类型可以为int, float, str 或符合同样条件的 dict
    :param name: 如果你传入 name 参数，你传入的 value 参数会被看做形如 {name:value} 的字典
    """
    _logger.add_other(value, name)


def add_progress(total_steps: int = None):
    """
    传入总的step数量，用于前端计算进度。

    :param total_steps: int, 总共有多少个step
    """
    _logger.add_progress(total_steps)


def add_to_line(line:Union[str, dict]):
    """
    将str记录到文件中，前端可以从网页跳转打开文件。每次记录是append到之前的记录之后的。

    :param line: 字符串类型或字典类型的数据，将直接写到文件中
    :return:
    """
    _logger.add_to_file(line)


def create_log_dir():
    """
    默认是生成第一个loss或者metric的时候才会在设置的log文件夹下创建一个新的文件夹，如果需要在代码运行时就创建该文件夹，可以通过
        调用该接口。

    :return:
    """
    _logger.create_log_dir()

def set_rng_seed(rng_seed:int = None, random:bool = True, numpy:bool = True,
                     pytorch:bool=True, deterministic:bool=True):
    """
    设置模块的随机数种子。由于pytorch还存在cudnn导致的非deterministic的运行，所以一些情况下可能即使seed一样，结果也不一致
        在fitlog.set_log_dir()之后调用本函数将自动记录rng_seed到log中。
    :param int rng_seed: 将这些模块的随机数设置到多少，默认为随机生成一个0-1000,000的随机数。
    :param bool, random: 是否将python自带的random模块的seed设置为rng_seed.
    :param bool, numpy: 是否将numpy的seed设置为rng_seed.
    :param bool, pytorch: 是否将pytorch的seed设置为rng_seed(设置torch.manual_seed和torch.cuda.manual_seed_all).
    :param bool, deterministic: 是否将pytorch的torch.backends.cudnn.deterministic设置为True。如果该值不为True，有时候即使
        全部随机数种子都一样也不能跑出相同的结果; 关掉的话可能会有一点性能损失。
    """
    return _logger.set_rng_seed(rng_seed, random, numpy, pytorch, deterministic)
