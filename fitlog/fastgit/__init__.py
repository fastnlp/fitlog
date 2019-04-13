from .committer import Committer

committer = Committer()


def commit(file, commit_message=None):
    committer.commit(file, commit_message)
