from .utils import _commit, _revert, _get_last_commit, _get_commits, make_info, short_logs
from .utils import _init_example as init_example, _init_project as init_project, _revert as revert_to_directory


# for other parts of fitlog
def revert(commit_id, work_dir, default_path=False, path=None, id_suffix=False):
    if default_path or path is None:
        return _revert(commit_id, work_dir=work_dir, id_suffix=id_suffix, cli=False)
    else:
        return _revert(commit_id, work_dir=work_dir, path=path, cli=False)
        

def fitlog_last_commit(work_dir):
    return _get_last_commit(work_dir)


def fitlog_commits(work_dir):
    return _get_commits(work_dir)


def git_last_commit(work_dir):
    return _get_last_commit(work_dir, git=True)


# for user
def commit(commit_message=None, config_file=".fitconfig"):
    return _commit(commit_message=commit_message, config_file=config_file)
