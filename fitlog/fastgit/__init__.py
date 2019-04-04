from .utils import _commit, _revert, _get_commit_id, _get_commit_ids, make_info, short_logs
from .utils import _init_example as init_example, _init_project as init_project, _revert as revert_to_directory


# for other parts of fitlog
def revert(commit_id, work_dir, path=None, local=False):
    return _revert(commit_id, work_dir=work_dir, path=path, local=local, show=False)


def get_commit_id(work_dir):
    return _get_commit_id(work_dir)


def get_commit_ids(work_dir):
    return _get_commit_ids(work_dir)


# for user
def commit(commit_message=None, config_file=".fitconfig"):
    return _commit(commit_message=commit_message, config_file=config_file)
