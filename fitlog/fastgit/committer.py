import os
import sys
import configparser
from datetime import datetime
from fnmatch import fnmatch
import subprocess

_commit_flag = '-------commit-------\n'
_system_flag = '-------system-------\n'
_arguments_flag = '------arguments-----\n'


def make_info(status, msg):
    return {
        "status": status,
        "msg": msg
    }


def colored_string(string: str, color: str or int) -> str:
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
    
    def __init__(self):
        self.__included_files = None
        self.work_dir = None
        self.config_file_path = None
        self.revert_with_commit_id = False
        self.watched_files = []
        self.commits = []
        self.last_commit = None
    
    def __get_work_dir(self):
        work_dir = os.path.dirname(self.config_file_path)
        if work_dir.endswith(".fitlog"):
            work_dir = work_dir[:-8]
        self.work_dir = work_dir
    
    def __find_config_file(self, run_file_path=None, cli=True):
        config_file_name = '.fitconfig'
        if run_file_path is None:
            path = os.getcwd()
        else:
            path = os.path.abspath(run_file_path)
        home_path = os.path.expanduser('~')
        root_path = "/"
        depth_cnt = 0
        max_depth = 8
        while 1:
            depth_cnt += 1
            if max_depth == depth_cnt:
                if cli:
                    print(colored_string("Folder depth out of limitation.", "red"))
                    print(colored_string("Can not find the config file.", "red"))
                return None
            if os.path.isfile(path + "/" + config_file_name):
                self.config_file_path = path + "/" + config_file_name
                return
            if os.path.isfile(path + "/.fitlog/" + config_file_name):
                self.config_file_path = path + "/.fitlog/" + config_file_name
                return
            if path == home_path or path == root_path:
                if cli:
                    print(colored_string("Reach the root or home.", "red"))
                    print(colored_string("Can not find the config file.", "red"))
                return
            path = os.path.dirname(path)

    def __read_config(self):
        config = configparser.ConfigParser()
        config.read(self.config_file_path)
        self.config = config
        if 'fit_settings' in config:
            if 'watched_files' in config['fit_settings']:
                tmp = config['fit_settings']['watched_files']
                self.watched_files = [each.strip() for each in tmp.split(',') if len(each) > 1]
            if 'revert_with_commit_id' in config['fit_settings']:
                tmp = config['fit_settings']['revert_with_commit_id']
                if tmp in ['False', 'false']:
                    self.revert_with_commit_id = False
                elif tmp in ["True", 'true']:
                    self.revert_with_commit_id = True
                else:
                    print(colored_string("The config field 'revert_with_commit_id' (value: %s) error."%tmp, "yellow"))
    
    def __get_watched_files(self):
        rules = self.watched_files
        watched = []
        to_match = []
        for rule in rules:
            t = rule.count('*')
            if t == 0:
                watched.append(rule)
            elif t == 1:
                to_match.append(rule)
        for parent, _, file_names in os.walk(self.work_dir):
            for file_name in file_names:
                for each in to_match:
                    if fnmatch(file_name, each):
                        watched.append(os.path.join(parent, file_name))
                        break
        return watched
    
    @staticmethod
    def __switch_to_fast_git(work_dir):
        commands = ["cd " + work_dir]
        if os.path.exists(work_dir + "/.git"):
            commands.append("mv .git .git_backup")
        if os.path.isfile(work_dir + "/.gitignore"):
            commands.append("mv .gitignore .gitignore_backup")
        commands.append("mv .fitlog .git")
        commands.append("mv .git/.gitignore .")
        command = " && ".join(commands)
        return os.popen(command).readlines()
    
    @staticmethod
    def __switch_to_standard_git(work_dir):
        commands = ["cd " + work_dir, "mv .git .fitlog"]
        commands += ["mv .gitignore .fitlog/"]
        if os.path.exists(work_dir + "/.git_backup"):
            commands.append("mv .git_backup .git", )
        if os.path.isfile(work_dir + "/.gitignore_backup"):
            commands.append("mv .gitignore_backup .gitignore")
        command = " && ".join(commands)
        return os.popen(command).readlines()
    
    @staticmethod
    def __check_directory(work_dir, display=True):
        if os.path.exists(work_dir + "/.fitlog"):
            if display:
                print(colored_string("Fitlog project has been initialized. ", "red"))
            return True
        return False

    def __commit_files(self, watched_files, commit_message):
        commands = ["cd " + self.work_dir]
        for file in watched_files:
            commands.append("git add " + file)
        commands.append("git add .gitignore")
        commands.append("git commit -m \"%s\"" % commit_message)
        command = " && ".join(commands)
        return os.popen(command).readlines()
    
    def __save_log(self, logs):
        with open(self.work_dir + "/.fitlog/fit_logs", "a")as file_out:
            file_out.writelines(logs)
    
    def __get_commits(self, cli=False):
        if cli:
            work_dir = os.path.abspath('.')
        else:
            if self.work_dir is None:
                return make_info(1, "Error: Have not set the work directory")
            work_dir = self.work_dir
        try:
            master = work_dir + "/.fitlog/logs/refs/heads/master"
            with open(master, "r") as fin:
                lines = fin.readlines()
            
            commit_ids = []
            for line in lines:
                commit_ids.append(line.split()[1])
            return make_info(0, commit_ids)
        except FileNotFoundError:
            return make_info(1, "Error: Some error occurs")
    
    def __get_last_commit(self, cli=False):
        info = self.__get_commits(cli)
        if info["status"] == 1:
            return make_info(1, "Error: Not a git repository (or no commit)")
        else:
            commit_ids = info["msg"]
            if len(commit_ids) >= 1:
                return make_info(0, commit_ids[-1])
            else:
                return make_info(1, "Error: Not a git repository (or no commit)")
    
    def __revert(self, commit_id, path=None, cli=False, id_suffix=False):
        if cli:
            work_dir = os.path.abspath('.')
        else:
            if self.work_dir is None:
                return make_info(1, "Error: Have not set the work directory")
            work_dir = self.work_dir
        if len(commit_id) < 6:
            if cli:
                print(colored_string("Commit-id's length is at least 6", "red"))
            return make_info(1, "Error: Commit-id's length is at least 6")
        if self.__check_directory(work_dir, display=False):
            commit_ids = self.__get_commits()['msg']
            flag = False
            # print(commit_ids)
            for full_commit_id in commit_ids:
                if full_commit_id.startswith(commit_id):
                    flag = True
                    commit_id = full_commit_id
                    break
            if not flag:
                if cli:
                    print(colored_string('Can not find the commit %s' % commit_id, 'red'))
                return make_info(1, 'Error: Can not find the commit %s' % commit_id)
            else:
                if path is None:
                    path = work_dir + "-revert"
                else:
                    path = os.path.abspath(path)
                if self.revert_with_commit_id or id_suffix:
                    path += "-" + commit_id[:6]
                
                if os.path.abspath(path).startswith(work_dir + '/'):
                    if cli:
                        print(colored_string("The <path> can't in your project directory.", "red"))
                    return make_info(1, "Error: The <path> can't in your project directory.")
                else:
                    ret_code = os.system("mkdir -p %s && /bin/cp -rf %s/.fitlog %s/.fitlog" % (path, work_dir, path))
                    if ret_code != 0:
                        if cli:
                            print(colored_string("Some error occurs in cp", "red"))
                        return make_info(1, "Error: Some error occurs in cp")
                self.__switch_to_fast_git(path)
                ret_code = os.system("cd %s && git reset --hard %s" % (path, commit_id))
                self.__switch_to_standard_git(path)
                if ret_code != 0:
                    if cli:
                        print(colored_string("Some error occurs in git reset", "red"))
                    return "Error: Some error occurs in git reset"
                if cli:
                    print("Your code is reverted to " + colored_string(path, "green"))
                return make_info(0, "Your code is reverted to " + path)
        else:
            if cli:
                print(colored_string('Not in a fitlog directory', 'red'))
            return make_info(1, "Error: Not in a fitlog directory")
    
    def commit(self, file, commit_message=None):
        if commit_message is None:
            commit_message = "Commit by fitlog"
        if self.config_file_path is None:
            self.__find_config_file(file)
            if self.config_file_path is None:
                return make_info(1, "Error: Config file is not found")
            self.__read_config()
            self.__get_work_dir()
            if not os.path.exists(self.work_dir + "/.fitlog"):
                print(colored_string(".fitlog folder is not found", "red"))
                return make_info(1, "Error: .fitlog folder is not found")
        commit_files = self.__get_watched_files()
        if commit_files is None:
            return make_info(1, "Error: no file matches the rules")
        logs = [_arguments_flag, "Run ", " ".join(sys.argv), "\n"]
        logs += [_system_flag]
        logs += self.__switch_to_fast_git(self.work_dir)
        commit_files = self.__get_watched_files()
        msg = self.__commit_files(commit_files, commit_message)
        logs += msg
        if msg:
            print(colored_string('Auto commit by fitlog', 'blue'))
        logs += self.__switch_to_standard_git(self.work_dir)
        commit_id = self.__get_last_commit()['msg']
        self.last_commit = [commit_id, commit_message]
        self.commits.append(self.last_commit)
        logs = [commit_id, '\n'] + logs
        logs = [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "\n"] + logs
        logs = [_commit_flag] + logs
        self.__save_log(logs + ['\n\n'])
        return make_info(0, commit_id)
    
    # PACKAGE FUNCTIONS
    def fitlog_last_commit(self):
        return self.last_commit
    
    def fitlog_commits(self):
        return self.commits
    
    @staticmethod
    def git_last_commit(work_dir):
        work_dir = os.path.abspath(work_dir)
        try:
            # 忽略错误信息
            lines = subprocess.Popen("cd %s && git log --oneline"%work_dir, shell=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.readlines()
            if len(lines)!=0:
                line = lines[0].decode('utf-8')
                git_id = line[:line.index(' ')]
                git_msg = line[line.index(' ')+1:].strip()
            else:
                git_id = None
                git_msg = None
            return make_info(0, [git_id, git_msg])
        except FileNotFoundError:
            return make_info(1, "Error: Some error occurs")

    def get_config(self, run_file_path=None):
        self.__find_config_file(run_file_path, cli=False)
        if self.config_file_path is None:
            return make_info(1, "Error: Config file is not found")
        self.__read_config()
        self.__get_work_dir()
        return make_info(0, self.work_dir)

    def fitlog_revert(self, commit_id, run_file_path=None, id_suffix=False):
        if self.work_dir is None:
            info = self.get_config(run_file_path)
            if info['status'] == 1:
                return info
        return self.__revert(commit_id, id_suffix=id_suffix, cli=False)
    
    # CLI FUNCTIONS
    def revert_to_directory(self, commit_id, path, id_suffix):
        self.__revert(commit_id, path, cli=True, id_suffix=id_suffix)
    
    def init_example(self, pj_name):
        if pj_name is None:
            pj_name = 'example_fitlog'
        self.init_project(pj_name, version="example")
    
    def init_project(self, pj_name, version="normal", hide=False, git=True):
        if pj_name == '.':
            if os.path.exists(".fitlog"):
                print(colored_string("Fitlog project existed.", "red"))
                return 0
            if os.path.exists(".git"):
                self.__switch_to_fast_git(os.path.abspath(pj_name))
        elif os.path.exists(pj_name + "/.fitlog"):
            print(colored_string("Fitlog project %s existed." % pj_name, "red"))
            return 0
        tools_path = os.path.realpath(__file__)[:-len("committer.py")]
        commands = [
            "cd " + pj_name,
            "cp -r %s/. ." % (tools_path + version),
            "git init",
            "git add .",
            "git commit -m \"Project initialized.\""]
        if pj_name != '.':
            commands = ["mkdir " + pj_name] + commands
        if hide:
            commands.append("mv .fitconfig .git")
        ret_code = os.system(" && ".join(commands))
        if ret_code != 0:
            print(colored_string("Some error occurs.", "red"))
            return ret_code
        self.__switch_to_standard_git(os.path.abspath(pj_name))
        
        if git:
            if pj_name == '.' and os.path.exists("/.git"):
                if hide:
                    open('.gitignore', 'a').write(".fitlog\n")
                else:
                    # TODO 可能存在一个问题是，如果.gitignore已经被git管理
                    open('.gitignore', 'a').write(".fitlog\n.fitconfig\nlogs\n.gitignore\n")
            else:
                commands = [
                    "cd " + pj_name,
                    "git init"]
                if hide:
                    commands += ["echo .fitlog > .gitignore"]
                else:
                    commands += ["echo \".gitignore\\n.fitlog/\\n.fitconfig\\nlogs/\" > .gitignore"]
                # commands += [
                #     # "git add .gitignore *",
                #     # "git commit -m \"Project initialized.\"",
                # ]
                ret_code = os.system(" && ".join(commands))
                if ret_code != 0:
                    print(colored_string("Some error occurs.", "red"))
                    return ret_code
        print(colored_string("Fitlog project %s is initialized." % pj_name, "green"))
        return 0
    
    def short_logs(self, show_now=False, last_num=None):
        head_id, log = None, None
        if self.__check_directory(os.path.abspath('.'), display=False):
            try:
                if show_now:
                    work_dir = os.path.abspath('.')
                    head_id = self.__get_last_commit(work_dir)["msg"]
                with open('.fitlog/fit_logs', 'r') as fin:
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
                            log.append("commit_id   " + colored_string(line, "green"))
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
                        print(colored_string("<last_num> must be an integer.", 'red'))
                show = []
                for log in show_logs:
                    for each in log:
                        show.append(each)
                    show.append("\n")
                print("".join(show))
                if show_now:
                    print(colored_string('Head is ' + head_id, "green"), "\n")
            except FileNotFoundError:
                print("No fitlog records here.")
        else:
            print(colored_string('Not in a fitlog directory', 'red'))
