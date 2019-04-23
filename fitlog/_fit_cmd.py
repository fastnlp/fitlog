from docopt import docopt
from fitlog.fastgit import committer

__doc__ = """
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
    --show                  Show the head commit of fitlog

Examples:
    fitlog init your_project   (create a your project named your_project)
    fitlog init                (init the current directory with fitlog)

"""

if __name__ == '__main__':
    args = docopt(__doc__, version='fitlog v1.0')
    if args['init']:
        name = args['<name>'] if args['<name>'] else '.'
        committer.init_project(name, hide=args["--hide"], git=not args["--no-git"])
    elif args['revert']:
        committer.revert_to_directory(args["<fit_id>"], args["<path>"], args["--id-suffix"])
