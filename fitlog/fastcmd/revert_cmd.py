"""
Usage:
    fitlog revert <fit_id>  [<path>] [--id-suffix]
    fitlog -h | --help

Arguments:
    fit_id                  The id of the commit you want to revert
    path                    The path to revert the old commit version

Options:
    -h --help               Revert to a specific version
    --id-suffix             Use commit id as the suffix of reverted folder
"""
from docopt import docopt
from fitlog.fastgit import committer


def revert_cmd(argv=None):
    args = docopt(__doc__, argv=argv)
    committer.revert_to_directory(args["<fit_id>"], args["<path>"], args["--id-suffix"])
