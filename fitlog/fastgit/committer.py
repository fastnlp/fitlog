import os
import sys
import shutil
import configparser
from datetime import datetime
from fnmatch import fnmatch
import time
from typing import List, Union
from git import Repo

_commit_flag = '-------commit-------\n'
_system_flag = '-------system-------\n'
_arguments_flag = '------arguments-----\n'


class Commit(list):
    """Commit 是一个有两个元素的 list，第一个元素是commit-id，第二个元素是commit-message

    :param commit_id: 本次 commit 的 commit-id
    :param msg: 本次 commit 的 commit-message
    :return:
    """

    def __init__(self, commit_id: str, msg: str):
        list.__init__(self)
        self.append(commit_id)
        self.append(msg)


class Info(dict):
    """Info 是一个dict，有 status 和 msg 两个字段, 用于给返回信息加上状态码

    :param status: 状态码，0表示没有错误
    :param msg: 返回信息
    :return:
    """

    def __init__(self, status: int, msg: Union[str, Commit, List[str], List[Commit]]):
        dict.__init__(self)
        self["status"] = status
        self["msg"] = msg


def _colored_string(string: str, color: str or int) -> str:
    """在终端中显示一串有颜色的文字

    :param string: 在终端中显示的文字
    :param color: 文字的颜色
    :return:
    """
    if isinstance(color, str):
        color = {
            "black": 30,
            "red": 31,
            "green": 32,
            "yellow": 33,
            "blue": 34,
            "purple": 35,
            "cyan": 36,
            "white": 37
        }[color]
    return "\033[%dm%s\033[0m" % (color, string)


class Committer:
    """
    用于自动 commit 的类，fastgit子模块使用此类实现单例模式。实例化后的对象会记录工作目录，配置文件路径等信息。
    对外只暴露有用的接口，内部处理函数的文档请在代码中查看。

    """

    def __init__(self):
        self.work_dir = None
        self.config_file_path = None
        self.watched_rules = []  # 记录被监控文件的规则
        self.commits = []  # 自动 commit 的历史记录
        self.last_commit = None  # 上一次 commit 的历史记录

    def _find_config_file(self, run_file_path: str = None, cli: bool = True) -> str:
        """

        :param run_file_path: 执行 commit 操作文件的目录
        :param cli: 是否在命令行内执行。如果在命令行中执行，则对用户进行提示
        :return: 返回 work_dir ，同时在 self.config_file_path 中存储配置文件路径
        """
        config_file_name = '.fitconfig'
        if run_file_path is None:
            path = os.getcwd()
        else:
            path = os.path.abspath(run_file_path)
        home_path = os.path.expanduser('~')
        root_path = os.path.abspath("/")
        depth_cnt = 0
        max_depth = 8
        while 1:
            depth_cnt += 1
            if max_depth == depth_cnt:
                if cli:
                    print(_colored_string("Folder depth out of limitation.", "red"))
                    print(_colored_string("Can not find the config file.", "red"))
                return "Error"
            if os.path.isfile(os.path.join(path, config_file_name)):
                self.config_file_path = os.path.join(path, config_file_name)
                self.work_dir = path
                return path
            if os.path.isfile(os.path.join(path, ".fitlog", config_file_name)):
                self.config_file_path = os.path.join(path, ".fitlog", config_file_name)
                self.work_dir = path
                return path
            if path == home_path or path == root_path:
                if cli:
                    print(_colored_string("Reach the root or home.", "red"))
                    print(_colored_string("Can not find the config file.", "red"))
                return "Error"
            path = os.path.dirname(path)

    def _read_config(self):
        """在获取配置文件路径后，读取其中的配置。采取保守策略，遇到错误自动跳过。

        :return:
        """
        config = configparser.ConfigParser()
        config.read(self.config_file_path)
        self.config = config
        if 'fit_settings' in config:
            if 'watched_rules' in config['fit_settings']:
                tmp = config['fit_settings']['watched_rules']
                self.watched_rules = [each.strip() for each in tmp.split(',') if len(each) > 1]

    def _get_watched_files(self) -> List[str]:
        """在获取监管文件的规则后，获取具体的文件列表

        :return: 即将被 commit 的文件的列表
        """
        rules = self.watched_rules
        watched_files = []
        to_match = []
        for rule in rules:
            t = rule.count('*')
            if t == 0:
                watched_files.append(rule)
            elif t == 1:
                to_match.append(rule)
        for parent, _, file_names in os.walk(self.work_dir):
            for file_name in file_names:
                for each in to_match:
                    if fnmatch(file_name, each):
                        watched_files.append(os.path.join(parent, file_name))
                        break
        return watched_files

    @staticmethod
    def _switch_to_fast_git(work_dir: str):
        """将工作目录从通常的 git 模式切换成 fastgit 模式

        :param work_dir: 工作目录的绝对路径
        """
        fitlog_path = os.path.join(work_dir, ".fitlog")
        git_path = os.path.join(work_dir, ".git")
        git_backup_path = os.path.join(work_dir, ".git_backup")
        gitignore_path = os.path.join(work_dir, ".gitignore")
        gitignore_backup_path = os.path.join(work_dir, ".gitignore_backup")
        if os.path.exists(git_path):
            shutil.move(git_path, git_backup_path)
        if os.path.isfile(gitignore_path):
            shutil.move(gitignore_path, gitignore_backup_path)
        if os.path.exists(fitlog_path):
            shutil.move(fitlog_path, git_path)
        if os.path.isfile(os.path.join(git_path, ".gitignore")):  # 使用 .fitlog 下的 .gitignore
            shutil.move(os.path.join(git_path, ".gitignore"), work_dir)

    @staticmethod
    def _switch_to_standard_git(work_dir: str):
        """将工作目录从 fastgit 模式切换成通常的 git 模式

        :param work_dir: 工作目录的绝对路径
        """
        fitlog_path = os.path.join(work_dir, ".fitlog")
        git_path = os.path.join(work_dir, ".git")
        git_backup_path = os.path.join(work_dir, ".git_backup")
        gitignore_path = os.path.join(work_dir, ".gitignore")
        gitignore_backup_path = os.path.join(work_dir, ".gitignore_backup")
        if os.path.exists(git_path):
            shutil.move(git_path, fitlog_path)
        if os.path.exists(gitignore_path):  # 把 .gitignore 移动到 .fitlog 下
            shutil.move(gitignore_path, os.path.join(fitlog_path, ""))
        if os.path.exists(git_backup_path):
            shutil.move(git_backup_path, git_path)
        if os.path.isfile(gitignore_backup_path):
            shutil.move(gitignore_backup_path, gitignore_path)

    @staticmethod
    def _check_directory(work_dir: str, cli: bool = True) -> bool:
        """检查指定目录是否已经存在 fitlog 项目，同时会修复可能错误的存在

        :param work_dir: 工作目录的绝对路径
        :param cli: 是否在命令行内执行。如果在命令行中执行，则对用户进行提示
        :return: 返回是否存在 fitlog 项目
        """
        fitlog_path = os.path.join(work_dir, ".fitlog")
        git_path = os.path.join(work_dir, ".git")
        git_backup_path = os.path.join(work_dir, ".git_backup")
        if os.path.exists(fitlog_path) or os.path.exists(git_backup_path):
            if os.path.exists(fitlog_path) and os.path.exists(git_backup_path):
                shutil.move(git_backup_path, git_path)
            elif os.path.exists(git_path) and os.path.exists(git_backup_path):
                shutil.move(git_path, fitlog_path)
                shutil.move(git_backup_path, git_path)
            if cli:
                print(_colored_string("Fitlog project has been initialized. ", "red"))
            return True
        return False

    def _commit_files(self, watched_files: List[str], commit_message: str):
        """利用当前 git（如果运行正常，应该是 fitlog 模式）进行一次 commit

        :param watched_files: 即将被 commit 的文件的列表
        :param commit_message: commit的message
        """
        repo = Repo(self.work_dir)
        for file in watched_files:
            repo.index.add(file)
        repo.index.add(".gitignore")
        repo.index.commit(commit_message)

    def _save_log(self, logs: List[str]):
        """ 将要存储的信息存储到默认的 fitlog

        :param logs: 要存储的信息
        :return:
        """
        with open(os.path.join(self.work_dir, ".fitlog", "fit_logs"), "a", encoding='utf8')as file_out:
            file_out.writelines(logs)

    def _get_commits(self, cli: bool = False) -> Info:
        """从项目目录下的记录获取 fastgit 的所有 commit-id

        :param cli: 是否在命令行内执行。如果在命令行中执行，则对用户进行提示
        :return: 返回带状态码的信息。如果成功，信息为 fastgit 的所有 commit-id 的数组
        """
        if cli:
            work_dir = os.path.abspath('.')
        else:
            if self.work_dir is None:
                return Info(1, "Error: Have not set the work directory")
            work_dir = self.work_dir
        try:
            master = os.path.join(work_dir, *"/.fitlog/logs/refs/heads/master".split('/'))
            with open(master, "r", encoding='utf8') as fin:
                lines = fin.readlines()
            commit_ids = []
            for line in lines:
                commit_ids.append(line.split()[1])
            return Info(0, commit_ids)
        except FileNotFoundError:
            return Info(1, "Error: Some error occurs")

    def _get_last_commit(self, cli: bool = False) -> Info:
        """从项目目录下的记录获取 fastgit 的上一次 commit-id

        :param cli: 是否在命令行内执行。如果在命令行中执行，则对用户进行提示
        :return: 返回带状态码的信息。如果成功，信息为 fastgit 的上一次 commit-id
        """
        info = self._get_commits(cli)
        if info["status"] == 1:
            return Info(1, "Error: Not a git repository (or no commit)")
        else:
            commit_ids = info["msg"]
            if len(commit_ids) >= 1:
                return Info(0, commit_ids[-1])
            else:
                return Info(1, "Error: Not a git repository (or no commit)")

    def _revert(self, commit_id: str, path: str = None, cli: bool = False, id_suffix: bool = False) -> Info:
        """回退 fastgit 的一个目标版本到指定放置路径

        :param commit_id: 回退版本的 commit-id
        :param path: 回退版本的指定放置路径
        :param cli: 是否在命令行内执行。如果在命令行中执行，则对用户进行提示
        :param id_suffix: 回退版本的放置文件夹是否包含 commit-id 做为后缀
        :return: 返回带状态码的信息。如果成功，信息为回退版本的放置路径
        """
        if cli:
            work_dir = os.path.abspath('.')
        else:
            if self.work_dir is None:
                return Info(1, "Error: Have not set the work directory")
            work_dir = self.work_dir
        if len(commit_id) < 6:
            if cli:
                print(_colored_string("Commit-id's length is at least 6", "red"))
            return Info(1, "Error: Commit-id's length is at least 6")
        if self._check_directory(work_dir, cli=False):
            commit_ids = self._get_commits(cli=cli)['msg']
            flag = False
            for full_commit_id in commit_ids:
                if full_commit_id.startswith(commit_id):
                    flag = True
                    commit_id = full_commit_id
                    break
            if not flag:
                if cli:
                    print(_colored_string('Can not find the commit %s' % commit_id, 'red'))
                return Info(1, 'Error: Can not find the commit %s' % commit_id)
            else:
                if path is None:
                    path = work_dir + "_revert"
                else:
                    path = os.path.abspath(path)
                if id_suffix:
                    path += "_" + commit_id[:6]

                if os.path.abspath(path).startswith(os.path.join(work_dir, "")):
                    if cli:
                        print(_colored_string("The <path> can't in your project directory.", "red"))
                    return Info(1, "Error: The <path> can't in your project directory.")
                core_path = os.path.join(path, ".fitlog")
                if os.path.exists(path):
                    shutil.rmtree(path, ignore_errors=True)
                os.makedirs(path)
                shutil.rmtree(core_path, ignore_errors=True)
                shutil.copytree(os.path.join(work_dir, ".fitlog"), core_path)
                self._switch_to_fast_git(path)
                repo = Repo(path)
                repo.head.reset(commit=commit_id, working_tree=True)
                if cli:
                    print("Your code is reverted to " + _colored_string(path, "green"))
                return Info(0, path)
        else:
            if cli:
                print(_colored_string('Not in a fitlog directory', 'red'))
            return Info(1, "Error: Not in a fitlog directory")

    # 对用户暴露的接口
    def commit(self, file: str, commit_message: str = None) -> Info:
        """用户用该方法进行 commit

        :param file: 执行文件路径，期望传入用户程序中的 __file__
        :param commit_message: 自动 commit 的 commit-message
        :return: 返回带状态码的信息。如果成功，信息为 commit-id
        """
        if commit_message is None:
            commit_message = "Commit by fitlog"
        if self.config_file_path is None:
            # 第一次执行 commit
            self._find_config_file(file)
            if self.config_file_path is None:
                return Info(1, "Error: Config file is not found")
            self._read_config()
            if not os.path.exists(os.path.join(self.work_dir, ".fitlog")):
                print(_colored_string(".fitlog folder is not found", "red"))
                return Info(1, "Error: .fitlog folder is not found")
        else:
            # 后续执行 commit
            self._check_directory(self.work_dir, cli=False)
        commit_files = self._get_watched_files()
        if commit_files is None:
            return Info(1, "Error: no file matches the rules")
        logs = [_arguments_flag, "Run ", " ".join(sys.argv), "\n"]
        logs += [_system_flag]
        sleep_cnt = 0
        while os.path.isdir(os.path.join(self.work_dir, ".git_backup")) or \
                os.path.isfile(os.path.join(self.work_dir, ".gitignore_backup")):
            time.sleep(1)
            sleep_cnt += 1
            if sleep_cnt == 10:
                raise TimeoutError("One auto-commit must run after another. Please run again a few seconds later."
                                   "\nIf you fail several times, please refer to our documents.")
        self._switch_to_fast_git(self.work_dir)
        try:
            commit_files = self._get_watched_files()
            self._commit_files(commit_files, commit_message)
            print(_colored_string('Auto commit by fitlog', 'blue'))
        except BaseException as e:
            print(_colored_string('Some error occurs during committing.', 'red'))
            self._switch_to_standard_git(self.work_dir)
            raise e
        self._switch_to_standard_git(self.work_dir)
        commit_id = self._get_last_commit()['msg']
        self.last_commit = Commit(commit_id, commit_message)
        self.commits.append(self.last_commit)
        logs = [commit_id, '\n'] + logs
        logs = [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "\n"] + logs
        logs = [_commit_flag] + logs
        self._save_log(logs + ['\n\n'])
        return Info(0, commit_id)

    # 对包内组件暴露的接口
    def get_config(self, run_file_path: str = None) -> Info:
        """通过执行文件的路径获取配置信息

        :param run_file_path: 执行文件的路径
        :return: 返回带状态码的信息。如果成功，信息为工作目录的路径
        """
        self._find_config_file(run_file_path, cli=False)
        if self.config_file_path is None:
            return Info(1, "Error: Config file is not found")
        self._read_config()
        return Info(0, self.work_dir)

    def fitlog_last_commit(self) -> Commit:
        """返回 self.last_commit 中记录的上一次的commit

        :return: Commit是一个元组，第一个参数为 commit-id，第二个参数为 commit-message
        """
        return self.last_commit

    def fitlog_commits(self) -> List[Commit]:
        """返回 self.commits 中记录的所有的commit

        :return: 返回一个 Commit 类型的数组
        """
        return self.commits

    @staticmethod
    def _read_id_from_file(path: str) -> Info:
        with open(path, "r", encoding='utf8') as fin:
            lines = fin.readlines()
        cuts = lines[-1].strip().split()
        msg = "\t"
        for each in cuts:
            if msg[0] != "\t":
                msg += each + " "
            if each.startswith("commit"):
                msg = " "
        return Info(0, Commit(cuts[1], msg.strip()))

    @staticmethod
    def git_last_commit_info(work_dir: str) -> Info:
        """获取 work_dir 或其祖其先目录上标准 git 的上一次 commit 的信息

        :param work_dir: 工作目录的路径
        :return: 返回带状态码的信息。如果成功，信息为一个 Commit 类型的 commit 信息
        """
        if work_dir is None:
            work_dir = '.'
        work_dir = os.path.abspath(work_dir)
        try:
            max_step = 10
            step = 0
            while not os.path.isdir(os.path.join(work_dir, '.git')):
                work_dir = os.path.join(work_dir, '..')
                if step > max_step or work_dir == os.path.abspath(os.sep):
                    break
                step += 1
            master = os.path.join(work_dir, *"/.git/logs/refs/heads/master".split('/'))
            return Committer._read_id_from_file(master)
        except FileNotFoundError:
            return Info(1, "Error: Some error occurs")

    @staticmethod
    def fit_last_commit_info(work_dir: str) -> Info:
        """获取 work_dir 或其祖其先目录上 fitlog 的上一次 commit 信息

        :param work_dir: 工作目录的路径
        :return: 返回带状态码的信息。如果成功，信息为一个 Commit 类型的 commit 信息
        """
        if work_dir is None:
            work_dir = '.'
        work_dir = os.path.abspath(work_dir)
        try:
            master = os.path.join(work_dir, *"/.fitlog/logs/refs/heads/master".split('/'))
            return Committer._read_id_from_file(master)
        except FileNotFoundError:
            return Info(1, "Error: Some error occurs")

    # 命令行操作所需的组件
    def revert_to_directory(self, commit_id: str, path: str, id_suffix: bool):
        """命令行用来回退 fastgit 的一个目标版本到指定放置路径

        :param commit_id: 回退版本的 commit-id
        :param path: 回退版本的指定放置路径
        :param id_suffix: 回退版本的放置文件夹是否包含 commit-id 做为后缀
        :return:
        """
        self._revert(commit_id, path, cli=True, id_suffix=id_suffix)

    def init_project(self, pj_name: str, version: str = "normal", hide: bool = False, git: bool = True) -> int:
        """命令行用来初始化一个 fitlog 项目

        :param pj_name: 项目名称
        :param version: 项目初始化文件夹的版本，目前只有 normal 这一种
        :param hide: 是否隐藏 .fitconfig 文件到 .fitlog 文件夹中
        :param git: 是否在初始化 fitlog 的同时为项目初始化 git
        :return: 状态码。0表示正常完成，其它错误码与系统相关
        """

        if pj_name == '.':
            pj_path = os.path.realpath('.')
        else:
            pj_path = os.path.join(os.path.realpath('.'), pj_name)
        # 如果没有项目目录，则创建
        if not os.path.exists(pj_path):
            os.makedirs(pj_path, exist_ok=True)
        # 如果已有 fitlog 项目，则检查是否需要修复
        if self._check_directory(pj_path):
            return 0
        # 如果已有 git 项目，则切换模式
        if os.path.exists(os.path.join(pj_path, ".git")):
            self._switch_to_fast_git(pj_path)

        tools_path = os.path.realpath(__file__)[:-len("committer.py")] + version
        if not os.path.isdir(os.path.join(pj_path, "logs")):
            shutil.copytree(os.path.join(tools_path, "logs"), os.path.join(pj_path, "logs"))
        elif not os.path.exists(os.path.join(pj_path, "logs", "default.cfg")):
            shutil.copy(os.path.join(tools_path, "logs", "default.cfg"), os.path.join(pj_path, "logs"))
        for file in [".fitconfig", ".gitignore", "main"]:
            if not os.path.exists(os.path.join(pj_path, file)):
                shutil.copy(os.path.join(tools_path, file), pj_path)
        if not os.path.exists(os.path.join(pj_path, "main.py")):
            shutil.move(os.path.join(pj_path, "main"), os.path.join(pj_path, "main.py"))
        else:
            os.remove(os.path.join(pj_path, "main"))
        Repo.init(path=pj_path)
        if hide:
            shutil.move(os.path.join(pj_path, ".fitconfig"), os.path.join(pj_path, ".git", ""))
        self._switch_to_standard_git(pj_path)
        # 以上完成 fitlog 的初始化，切换模式

        self.commit(os.path.join(pj_path, "main.py"), "Project initialized.")

        # 新建普通的 git
        if git:
            if not os.path.exists(os.path.join(pj_path, ".git")):
                Repo.init(path=pj_path)
            # 添加 ignore 的内容
            if hide:
                write_text = ".fitlog\nlogs\n"
            else:
                write_text = ".fitlog\n.fitconfig\nlogs\n"
            gitignore_path = os.path.join(pj_path, '.gitignore')
            if os.path.exists(gitignore_path):
                open(gitignore_path, 'a', encoding='utf8').write("\n" + write_text)
            else:
                open(gitignore_path, 'w', encoding='utf8').write(write_text)
        print(_colored_string("Fitlog project %s is initialized." % pj_name, "green"))
        return 0

    def short_logs(self, show_now: bool = False, last_num: int = None):
        """在命令行用来查看 fastgit 的自带 logs

        :param show_now: 是否显示当前版本在 logs 中的位置
        :param last_num: 显示最近的 {last_num} 条记录
        :return:
        """
        head_id, log = None, None
        if self._check_directory(os.path.abspath('.'), cli=False):
            try:
                if show_now:
                    head_id = self._get_last_commit()["msg"]
                with open(os.path.join('.fitlog', 'fit_logs'), 'r', encoding='utf8') as fin:
                    lines = fin.readlines()
                cnt = 0
                show_logs = []
                for line in lines:
                    if line == _commit_flag:
                        cnt = 0
                    elif cnt == 1:
                        log = ["date&time   " + line]
                    elif cnt == 2:
                        if show_now and line.strip() == head_id:
                            log.append("commit_id   " + _colored_string(line, "green"))
                        else:
                            log.append("commit_id   " + line)
                    elif cnt == 4:
                        log.append("arguments   " + line)
                        show_logs.append(log)
                    cnt += 1
                if last_num is not None:
                    try:
                        if int(last_num) < len(show_logs):
                            show_logs = show_logs[-int(last_num):]
                    except ValueError:
                        print(_colored_string("<last_num> must be an integer.", 'red'))
                show = []
                for log in show_logs:
                    for each in log:
                        show.append(each)
                    show.append("\n")
                print("".join(show))
                if show_now:
                    print(_colored_string('Head is ' + head_id, "green"), "\n")
            except FileNotFoundError:
                print("No fitlog records here.")
        else:
            print(_colored_string('Not in a fitlog directory', 'red'))

    def fitlog_revert(self, commit_id: str, run_file_path: str = None, id_suffix: bool = False) -> Info:
        """fitlog 调用此接口进行版本回退

        :param commit_id: 需要回退版本的 commit-id
        :param run_file_path: 执行文件的路径
        :param id_suffix: 回退版本的放置文件夹是否包含 commit-id 做为后缀
        :return: 返回带状态码的信息。如果成功，信息为回退版本的放置路径
        """
        if self.work_dir is None:
            info = self.get_config(run_file_path)
            if info['status'] == 1:
                return info
        return self._revert(commit_id, id_suffix=id_suffix, cli=False)
