"""
fastgit（简称 fit） 是 fitlog 的一部分，用于帮助用户进行自动 commit。自动 commit 的文件在 .fitlog 文件夹中，与 .git 文件夹类似。
用户需要使用 fitlog 命令行工具初始化项目，项目默认会生成一个名为 .fitconfig 的配置文件，可以配置监控文件的规则等参数。

"""
from .committer import Committer

committer = Committer()


def commit(file: str, commit_message: str = None):
    """用户用该方法进行 commit，期望使用方法为::
        
        from fitlog import fitlog
        fitlog.commit(__file__,"commit_message")
    
    :param file: 执行文件路径，期望传入用户程序中的 __file__
    :param commit_message: 自动 commit 的 commit-message
    :return: 采取保守策略。不返回 Info 信息，但在命令行中给出提示
    """
    _ = committer.commit(file, commit_message)
