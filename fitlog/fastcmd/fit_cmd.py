"""
Usage:
    fitlog init [<name>] [--hide] [--no-git]
    fitlog revert <fit_id>  [<path>] [--id-suffix]
    fitlog -h | --help

Arguments:
    name                    Name of the fitlog project
    fit_id                  The id of the commit you want to revert
    path                    The path to revert the old commit version

Options:
    -h --help               Show this screen.
    -v --version            Show version.
    --hide                  Hide .fitconfig inside .fitlog folder
    --not-git               Not initialize with a standard git
    --id-suffix             Use commit id as the suffix of reverted folder

Examples:
    fitlog init project     Create a your project named project
    fitlog init             Init the current directory with fitlog

"""
from docopt import docopt
from fitlog.fastgit import committer


def fit_cmd(argv=None):
    if argv:
        args = docopt(__doc__, version='fitlog v1.0', argv=argv)
    else:
        args = docopt(__doc__, version='fitlog v1.0')
    if args['init']:
        name = args['<name>'] if args['<name>'] else '.'
        committer.init_project(name, hide=args["--hide"], git=not args["--no-git"])
    elif args['revert']:
        committer.revert_to_directory(args["<fit_id>"], args["<path>"], args["--id-suffix"])


if __name__ == '__main__':
    fit_cmd()