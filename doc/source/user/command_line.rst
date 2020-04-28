==============
命令行工具
==============


fitlog
------

fitlog 安装后会在系统的命令行中添加fitlog 命令，我们可以使用该命令初始化项目、启动日志网页等等。
fitlog 命令主要有init（初始化项目）、revert（版本回退）和log（启动日志网页）三种功能，需要用不同的参数进行启动。

.. code:: shell

    Usage:
        fitlog <command> [<args>...]
        fitlog -h|--help

    Supported commands
        init            Initialize a fitlog project
        revert          Revert to a specific version
        log             Visualize logs by a server.

    See "fitlog help <command>" for more information on a specific command

fitlog init
-----------

fitlog init 可以指定项目名称<name>，或者默认把当前文件夹变成 fitlog 项目。它同时给了--hide选项来隐藏.fitconfig 文件；
还有--no-git选项，表示在创建 fitlog 时不创建常规的 git。

.. code:: shell

    Usage:
        fitlog init [<name>] [--hide] [--no-git]

    Arguments:
        name                    Name of the fitlog project

    Options:
        --hide                  Hide .fitconfig inside .fitlog folder
        --not-git               Not initialize with a standard git

    Examples:
        fitlog init project     Create a your project named project
        fitlog init             Init the current directory with fitlog

.. note::

    假设你在命令行中的 workspace 目录下使用 ``fitlog init project`` 命令，那么屏幕上会显示如下的内容（一般情况下是彩色的）。

    .. code:: shell

        Initialized empty Git repository in workspace/project/.git/
        Auto commit by fitlog
        Initialized empty Git repository in workspace/project/.git/
        Fitlog project project is initialized.

    前两行表示 fitlog 生成了一个 git 仓库，并将其转化成了隐藏的 fitlog 仓库。第三行表示 fitlog 又帮你生成了
    一个明面上的 git 仓库，如果你只想使用 fitlog 而不想手动进行 git 管理，可以使用 ``--not-git`` 参数控制。

    项目初始化后 project 目录下就会有 **.git** 、 **.fitlog** 、 **logs** 三个文件夹，和 **.gitignore** ， **.fitconfig** 、 **main.py** 三个文件：
    **.git** 和 **.fitlog** 都是用于版本控制的文件夹，你不需要详细了解； **.gitignore** 里记录了不会被 commit 的文件和文件夹，
    为了防止 fitlog 和 git 互相管理、产生混乱，里面已有的内容请不要删除； **main.py** 是使用 fitlog 的一个样例，您可以对它进行删除、改名，只要运行的代码中使用了 fitlog 即可。

    **.fitconfig** 是 fitlog 的配置文件，具体的选项参见 :doc:`配置文件 </user/configs>`  。您可以在生成项目时使用 ``--hide`` 参数，
    让它生成在 **.fitlog** 文件夹内。**logs** 文件夹是 fitlog 记录的实验日志的默认目录，
    您可以通过修改 **.fitconfig** 中的选项来改变记录的实验日志的目录，修改后可以删除 **logs** 文件夹。



fitlog revert
-------------

你可以使用 fitlog revert 命令来进行版本回退，但我们更希望你使用 fitlog 提供的网页工具来完成这项任务。

.. code:: shell

    Usage:
        fitlog revert <fit_id>  [<path>] [--id-suffix]

    Arguments:
        fit_id                  The id of the commit you want to revert
        path                    The path to revert the old commit version

    Options:
        --id-suffix             Use commit id as the suffix of reverted folder

fitlog log
----------

你可以使用 fitlog log 命令来启动一个管理日志的网页，你必须提供参数<log-dir>来表示日志存放的位置，项目初始化时会生成符合条件的 logs 文件夹。
你还可以指定配置文件的名称、网页对应的端口号和服务器停止的时间。

.. code:: shell

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