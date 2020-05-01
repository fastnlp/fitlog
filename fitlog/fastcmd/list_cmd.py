"""
Usage:
    fitlog list [<num>] [--show-now]
    fitlog -h | --help

Arguments:
    num                     The number of recent commits you want to list

Options:
    -h --help               This is a command to list committed versions
    --show-now              Show the current version with green font

Examples:
    fitlog list 10          List recent 10 commits
    fitlog list --show-now  List all commits (the current one is green)
"""
from docopt import docopt
from fitlog.fastgit import committer


def list_cmd(argv=None):
    args = docopt(__doc__, argv=argv)

    committer.short_logs(args["--show-now"], args["<num>"])
