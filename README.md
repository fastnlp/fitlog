# fitlog
[![Pypi](https://img.shields.io/pypi/v/fitlog.svg)](https://pypi.org/project/fitlog)
[![Documentation Status](https://readthedocs.org/projects/fitlog/badge/?version=latest)](http://fitlog.readthedocs.io/?badge=latest)

fitlog = fast + git + log, 是一款用于辅助用户记录日志和管理代码的工具，主要支持 Linux 和 macOS，也支持在 Windows 的 Git Bash 中使用。 

[fitlog中文文档](https://fitlog.readthedocs.io/zh/latest/)

## file structure
```
|-setup.py
|-docs
|-fitlog
|  |--- init
|  |--- fastlog
|  |--- fastgit
|  |--- server
|-test
  
```

## update schedule

filog 是我们实验室内部使用的一款工具，大部分功能口口相传，文档和教程还没有特别全。感谢大家的尝试使用，遇到问题可以在 Issues 处提出，我们也会在五一假期结束前更新一系列文档和教程。

更新计划包括：

- [ ] 增加更多的使用案例
- [x] 检查并更详细地介绍 [命令行工具](https://fitlog.readthedocs.io/zh/latest/user/command_line.html) 的使用方法
- [ ] 完成[网页服务](https://fitlog.readthedocs.io/zh/latest/user/website.html)的详细介绍


## 一些使用说明
1. 如果在debug阶段，不希望fitlog发生任何作用，那么直接在入口代码处加入fitlog.debug()
就可以让所有的fitlog调用不起任何作用，debug结束再注释掉这一行就可以了。  
2. fitlog默认只有在产生了第一个metric或loss的时候才会创建log文件夹，防止因为其它bug还没运行
到model就崩溃产生大量无意义的log。
3. 如果使用了分布式训练，一般只需要主进程记录fitlog就好。这个时候可以通过将非主进程的fitlog设置fitlog.debug()
    ```python
    import torch
    import fitlog
    
    if torch.distributed.get_rank()>0:
        fitlog.debug()
    ```
4. 不要通过多进程使用fitlog，即multiprocessing模块。
5. fitlog.commit()只需要在某个python文件调用就可以了，一般就在入口python文件即可。 
6. 传入到fitlog的各种参数、metric的名称，请 **避免特殊符号（例如$%!#@空格），请只使用
_与各种字母的组合** ，因为特殊符号可能导致网页端显示不正常。
