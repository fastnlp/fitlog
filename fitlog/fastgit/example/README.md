### fitlog说明


### 配置文件.fitlog_config
在项目根目录下，或在项目根目录下的.fitlog的文件夹内
```
*.py
ex.*
useless-*.java
data/code
logs/results.txt
```

`*.py`表示所有子目录下以`.py`结尾的文件
`ex.*`表示所有子目录下以`ex.`开头的文件
`useless-*.java`表示所有以`useless-`开头,并且以`.java`结尾的文件
你还可以指定特定文件夹，如`data/code`，或特定文件夹中的文件，如`logs/results.txt`

除此之外，fitlog不支持其它复杂的选择方式。

在一般的初始化中，我们默认只将`*.py`做为监控的文件类型

我们推荐你选择项目根目录或者代码根目录（不含数据）做为fitlog的根目录


### 在python代码中使用

```python
import fitlog
fitlog.commit()
```


### 初始化方法
```shell
python -m fitlog init
```


```
Usage:
    fitlog init <name> [--hide] [--no-git] [-e | --example]
    fitlog revert <commit_id>  [<path>] [--local]
    fitlog log [--show] [--last=<last_num>]
    fitlog -h | --help
    fitlog -v | --version

Arguments:
    name                    Name of the fitlog project
    commit_id               The id of the commit you want to revert
    path                    The path to revert the old commit version
    last_num                The number of logs to display
    
Options:
    -h --help               Show this screen.
    -v --version            Show version.
    -e --example            Initialize an example project
    --hide                  Hide .fitlog_config inside .fitlog folder
    --not-git               Not initialize with a standard git
    --local                 Not create a new folder for reverted version
    --show                  Show the head commit of fitlog

Examples:
    fitlog init --example      (create a example named example_fitlog)
    fitlog init your_project   (create a your project named your_project)
    fitlog init                (init the current directory with fitlog)

```