"""
Usage:
    fitlog init [<name>] [--hide] [--no-git]
    fitlog -h | --help

Arguments:
    name                    Name of the fitlog project

Options:
    -h --help               This is a command to initialize a fitlog project
    --hide                  Hide .fitconfig inside .fitlog folder
    --no-git                Not initialize with a standard git

Examples:
    fitlog init project     Create a your project named project
    fitlog init             Init the current directory with fitlog
"""
from docopt import docopt
from fitlog.fastgit import committer


def init_cmd(argv=None):
    args = docopt(__doc__, argv=argv)

    name = args['<name>'] if args['<name>'] else '.'
    committer.init_project(name, hide=args["--hide"], git=not args["--no-git"])
