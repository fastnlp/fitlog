==============
命令行工具
==============

fitlog 安装后会在系统的命令行中添加fitlog 命令，我们可以使用该命令初始化项目、启动日志网页等等。
fitlog 命令主要有init（初始化项目）、list（查看已有记录）、revert（版本回退）和log（启动日志网页）四种功能，需要用不同的参数进行启动。

.. code:: text

    Usage:
        fitlog <command> [<args>...]
        fitlog help <command>
        fitlog -h | --help
        fitlog --version

    Supported commands
        init            Initialize a fitlog project
        list            List committed versions
        revert          Revert to a specific version
        log             Visualize logs by a server

    See "fitlog help <command>" for more information on a specific command

fitlog init
-----------

*fitlog init* 可以指定项目名称 ``<name>`` ，或者默认把当前文件夹变成 fitlog 项目。它同时给了--hide选项来隐藏.fitconfig 文件；
还有--no-git选项，表示在创建 fitlog 时不创建常规的 git。

.. code:: text

    Usage:
        fitlog init [<name>] [--hide] [--no-git]
        fitlog -h | --help

    Arguments:
        name                    Name of the fitlog project

    Options:
        -h --help               This is a command to initialize a fitlog project
        --hide                  Hide .fitconfig inside .fitlog folder
        --no-git                Not initialize with a standard git

    Examples:
        fitlog init project     Create a your project named project
        fitlog init             Init the current directory with fitlog

.. note::

    假设你在命令行中的 **/workspace** 目录下使用 ``fitlog init project`` 命令，那么屏幕上会显示如下的内容：

    .. code:: text

        Initialized empty Git repository in /workspace/project/.git/
        Auto commit by fitlog
        Initialized empty Git repository in /workspace/project/.git/
        Fitlog project project is initialized.

    前两行表示 fitlog 生成了一个 git 仓库，并将其转化成了隐藏的 fitlog 仓库。第三行表示 fitlog 又帮你生成了
    一个明面上的 git 仓库，如果你只想使用 fitlog 而不想手动进行 git 管理，可以使用 ``--no-git`` 参数控制。

    项目初始化后 project 目录下就会有 **.git** 、 **.fitlog** 、 **logs** 三个文件夹，和 **.gitignore** ， **.fitconfig** 、 **main.py** 三个文件。

    **.git** 和 **.fitlog** 都是用于版本控制的文件夹，你不需要详细了解； **.gitignore** 里记录了不会被 commit 的文件和文件夹，
    为了防止 fitlog 和 git 互相管理、产生混乱，里面已有的内容请不要删除； **main.py** 是使用 fitlog 的一个样例，您可以对它进行删除、改名，只要运行的代码中使用了 fitlog 即可。

    **.fitconfig** 是 fitlog 的配置文件，具体的选项参见 :doc:`配置文件 </user/configs>`  。您可以在生成项目时使用 ``--hide`` 参数，
    让它生成在 **.fitlog** 文件夹内。**logs** 文件夹是 fitlog 记录的实验日志的默认目录，
    您可以通过修改 **.fitconfig** 中的选项来改变记录的实验日志的目录，修改后可以删除 **logs** 文件夹。


fitlog list & revert
--------------------

你可以使用 *fitlog list* 查看自动存储的版本，并使用 *fitlog revert* 来进行版本回退，但我们更希望你使用 fitlog 提供的 :doc:`/user/website` 来完成这项任务。

.. code:: text

    Usage:
        fitlog list [<num>] [--show-now]
        fitlog revert <fit_id>  [<path>] [--id-suffix]

    Arguments:
        num                     The number of recent commits you want to list
        fit_id                  The id of the commit you want to revert
        path                    The path to revert the old commit version

    Options:
        --show-now              Show the current version
        --id-suffix             Use commit id as the suffix of reverted folder

.. note::

    假设你在命令行中的 **/workspace/project** 目录下，使用 ``fitlog list 2 --show-now`` 命令，看到了最近两次自动 commit 的记录，
    并知道了当前版本为 *fc0af5* 。其中 ``--show-now`` 显示当前版本。

    .. code-block:: text

        date&time   2020-05-01 18:06:55
        commit_id   ab762510af8046f1e913c854d84171ba5b8f8d9a
        arguments   Run main.py

        date&time   2020-05-01 18:10:05
        commit_id   fc0af540e41e13b22e24f59959a43a434b525db6
        arguments   Run main.py

        Head is fc0af540e41e13b22e24f59959a43a434b525db6

    假设你想回退到上个版本 *ab7625* 。使用 ``fitlog revert ab7625`` 命令， 一个 *ab7625* 版本的项目就会出现在
    **/workspace/project_revert** 的位置。您可以通过指定 ``<path>`` 的方式改变回退目录（例如：指定为 **/workspace/project_v1**），
    也可以使用 ``--id-suffix`` 参数使回退目录含有版本号后缀，变为 **/workspace/project_revert_ab7625** 。

    注意！使用版本回退功能可能会覆盖目标文件夹（如  **/workspace/project_revert** ）中的文件。

fitlog log
----------

你可以使用 fitlog log 命令来启动一个管理日志的网页，你必须提供参数<log-dir>来表示日志存放的位置，项目初始化时会生成符合条件的 logs 文件夹。
你还可以指定配置文件的名称、网页对应的端口号和服务器停止的时间。

.. code:: text

    Usage:
        fitlog log <log-dir> [--log-config-name=L] [--port=P] [--standby-hours=S] [--token=T] [--ip=I]

    Arguments:
        log-dir                 Where to find logs.

    Options:
        -h --help               This is a command to start fitlog server to visualize logs.
        -l=L --log-config-name  Log server config name. Must under the folder of <log-dir>. [default: default.cfg]
        -p=P --port             Which port to start to looking for usable port.[default: 5000]
        -s=S --standby-hours    How long to wait before the server . [default: 48]
        -t=T --token            If this is used, your have to specify the token when accessing. Default no token.
        -i=I --ip               Which ip to bind to. Default is 0.0.0.0 [default: 0.0.0.0]

