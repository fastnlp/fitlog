"""
fastgit（简称 fit） 是 fitlog 的一部分，用于帮助用户进行自动 commit。自动 commit 的文件在 .fitlog 文件夹中，与 .git 文件夹类似。
用户需要使用 fitlog 命令行工具初始化项目，项目默认会生成一个名为 .fitconfig 的配置文件，可以配置监控文件的规则等参数。

"""
from .committer import Committer

committer = Committer()
