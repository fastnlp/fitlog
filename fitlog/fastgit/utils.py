import os, sys
from datetime import datetime
from fnmatch import fnmatch

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


def _get_work_dir(config_file):
    work_dir = os.path.dirname(config_file)
    if work_dir.endswith(".fitlog"):
        work_dir = work_dir[:-8]
    return work_dir


def _find_config_file(config_file, cli=True):
    path = os.getcwd()
    home_path = os.path.abspath("~")
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
        if os.path.isfile(path + "/" + config_file):
            config_file = path + "/" + config_file
            break
        if os.path.isfile(path + "/.fitlog/" + config_file):
            config_file = path + "/.fitlog/" + config_file
            break
        if path == home_path or path == root_path:
            if cli:
                print(colored_string("Reach the root or home.", "red"))
                print(colored_string("Can not find the config file.", "red"))
            return None
        path = os.path.dirname(path)
    return config_file


def _get_watched_files(config_file, work_dir):
    with open(work_dir + '/' + config_file, "r") as fin:
        lines = [line.strip() for line in fin.readlines()]
    rules = []
    for line in lines:
        rules.append(line)
    watched = []
    to_match = []
    for rule in rules:
        t = rule.count('*')
        if t == 0:
            watched.append(rule)
        elif t == 1:
            to_match.append(rule)
    for parent, _, file_names in os.walk(work_dir):
        for file_name in file_names:
            for each in to_match:
                if fnmatch(file_name, each):
                    watched.append(os.path.join(parent, file_name))
                    break
    return watched


def _switch_to_fast_git(work_dir):
    commands = ["cd " + work_dir]
    if os.path.exists(work_dir + "/.git"):
        commands.append("mv .git .git_backup")
    if os.path.isfile(work_dir + "/.gitignore"):
        commands.append("mv .gitignore .gitignore_backup")
    commands.append("mv .fitlog .git")
    commands.append("mv .git/.gitignore .")
    command = " && ".join(commands)
    return os.popen(command).readlines()


def _switch_to_standard_git(work_dir):
    commands = ["cd " + work_dir, "mv .git .fitlog"]
    commands += ["mv .gitignore .fitlog/"]
    if os.path.exists(work_dir + "/.git_backup"):
        commands.append("mv .git_backup .git", )
    if os.path.isfile(work_dir + "/.gitignore_backup"):
        commands.append("mv .gitignore_backup .gitignore")
    command = " && ".join(commands)
    return os.popen(command).readlines()


def _commit_files(work_dir, watched_files, commit_message):
    commands = ["cd " + work_dir]
    for file in watched_files:
        commands.append("git add " + file)
    commands.append("git add .gitignore")
    if commit_message is None:
        commands.append("git commit -m \"Commit by fitlog\"")
    else:
        commands.append("git commit -m \"%s\"" % commit_message)
    command = " && ".join(commands)
    return os.popen(command).readlines()


def _save_log(work_dir, logs):
    with open(work_dir + "/.fitlog/fit_logs", "a")as file_out:
        file_out.writelines(logs)


def _check_directory(work_dir, display=True):
    if os.path.exists(work_dir + "/.fitlog"):
        if display:
            print(colored_string("Fitlog project has been initialized. ", "red"))
        return True
    return False


def _init_example(pj_name):
    if pj_name is None:
        pj_name = 'example_fitlog'
    _init_project(pj_name, version="example")


def _init_project(pj_name, version="normal", hide=False, git=True):
    if pj_name == '.':
        if os.path.exists(".fitlog"):
            print(colored_string("Fitlog project existed.", "red"))
            return 0
        if os.path.exists(".git"):
            _switch_to_fast_git(os.path.abspath(pj_name))
    elif os.path.exists(pj_name + "/.fitlog"):
        print(colored_string("Fitlog project %s existed." % pj_name, "red"))
        return 0
    tools_path = os.path.realpath(__file__)[:-len("utils.py")]
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
    _switch_to_standard_git(os.path.abspath(pj_name))
    
    if git:
        if pj_name == '.' and os.path.exists("/.git"):
            if hide:
                open('.gitignore', 'a').write(".fitlog\n")
            else:
                open('.gitignore', 'a').write(".fitlog\n.fitconfig\n")
        else:
            commands = [
                "cd " + pj_name,
                "git init"]
            if hide:
                commands += ["echo .fitlog > .gitignore"]
            else:
                commands += ["echo \".fitlog/\\n.fitconfig\" > .gitignore"]
            commands += [
                "git add .gitignore *",
                "git commit -m \"Project initialized.\"",
            ]
            ret_code = os.system(" && ".join(commands))
            if ret_code != 0:
                print(colored_string("Some error occurs.", "red"))
                return ret_code
    print(colored_string("Fitlog project %s is initialized." % pj_name, "green"))
    return 0


def _get_commits(work_dir=None, git=False):
    if work_dir is None:
        work_dir = os.path.abspath('.')
    try:
        if git:
            master = work_dir + "/.git/logs/refs/heads/master"
        else:
            master = work_dir + "/.fitlog/logs/refs/heads/master"
        with open(master, "r") as fin:
            lines = fin.readlines()
        commit_ids = []
        for line in lines:
            commit_ids.append(line.split()[1])
        return make_info(0, commit_ids)
    except FileNotFoundError:
        return make_info(1, "Error: Some error occurs")


def _get_last_commit(work_dir=None, git=False):
    if work_dir is None:
        work_dir = os.path.abspath('.')
    info = _get_commits(work_dir, git)
    if info["status"] == 1:
        return make_info(1, "Error: Not a git repository (or no commit)")
    else:
        commit_ids = info["msg"]
        if len(commit_ids) >= 1:
            return make_info(0, commit_ids[-1])
        else:
            return make_info(1, "Error: Not a git repository (or no commit)")


def _revert(commit_id, work_dir=None, path=None, cli=False, id_suffix=False):
    if work_dir is None:
        work_dir = '.'
    work_dir = os.path.abspath(work_dir)
    path = os.path.abspath(path)
    if len(commit_id) < 6:
        if cli:
            print(colored_string("Commit-id's length is at least 6", "red"))
        return make_info(1, "Error: Commit-id's length is at least 6")
    if _check_directory(work_dir, display=False):
        commit_ids = _get_commits(work_dir)['msg']
        flag = False
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
            if id_suffix:
                path += "-" + commit_id[:6]
            if os.path.abspath(path).startswith(work_dir+'/'):
                if cli:
                    print(colored_string("The <path> can't in your project directory.", "red"))
                return make_info(1, "Error: The <path> can't in your project directory.")
            else:
                ret_code = os.system("mkdir -p %s && /bin/cp -rf %s/.fitlog %s/.fitlog" % (path, work_dir, path))
                if ret_code != 0:
                    if cli:
                        print(colored_string("Some error occurs in cp", "red"))
                    return make_info(1, "Error: Some error occurs in cp")
            _switch_to_fast_git(path)
            ret_code = os.system("cd %s && git reset --hard %s" % (path, commit_id))
            _switch_to_standard_git(path)
            if ret_code != 0:
                if cli:
                    print(colored_string("Some error occurs in git reset", "red"))
                return "Error: Some error occurs in git reset"
            print("Your code is reverted at " + colored_string(path, "green"))
            return make_info(0, path)
    else:
        if cli:
            print(colored_string('Not in a fitlog directory', 'red'))
        return make_info(1, "Error: Not in a fitlog directory")


def _commit(commit_message=None, config_file=".fitconfig"):
    config_file_path = _find_config_file(config_file)
    if config_file_path is None:
        return make_info(1, "Error: Config file is not found")
    work_dir = _get_work_dir(config_file_path)
    if not os.path.exists(work_dir + "/.fitlog"):
        print(colored_string(".fitlog folder is not found", "red"))
        return make_info(1, "Error: .fitlog folder is not found")
    watched_files = _get_watched_files(config_file, work_dir)
    if watched_files is None:
        return make_info(1, "Error: no file matches the rules")
    logs = [_arguments_flag, "Run ", " ".join(sys.argv), "\n"]
    logs += [_system_flag]
    logs += _switch_to_fast_git(work_dir)
    msg = _commit_files(work_dir, watched_files, commit_message)
    logs += msg
    if msg:
        print(colored_string('Auto commit by fitlog', 'blue'))
    logs += _switch_to_standard_git(work_dir)
    commit_id = _get_last_commit(work_dir)['msg']
    logs = [commit_id, '\n'] + logs
    logs = [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "\n"] + logs
    logs = [_commit_flag] + logs
    _save_log(work_dir, logs + ['\n\n'])
    return make_info(0, commit_id)


def short_logs(show_now=False, last_num=None):
    if _check_directory(os.path.abspath('.'), display=False):
        try:
            if show_now:
                work_dir = os.path.abspath('.')
                head_id = _get_last_commit(work_dir)["msg"]
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
