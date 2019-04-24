"""
fastlog 是 fitlog 的一部分，用于帮助用户进行日志管理。fastlog 默认使用工作目录下的 logs 文件做为存储和配置路径。
默认配置文件为default.cfg。用户可以使用 fitlog 命令行工具初始化项目，启动服务器，并在网页上查看日志。
"""
from .log_read import LogReader
from .logger import Logger

logger = Logger()
log_reader = LogReader()
