"""
Usage:
    fitlog <command> [<args>...]
    fitlog -h|--help
    fitlog --version

Supported commands
    init            Initialize a fitlog project
    revert          Revert to a specific version
    log             Visualize logs by a server.
    
See "fitlog help <command>" for more information on a specific command
"""
import sys
from docopt import docopt
from .fit_cmd import fit_cmd
from .log_cmd import log_cmd


def main_cmd():
    argv = sys.argv[1:2] if len(sys.argv) > 2 else sys.argv[1:]
    args = docopt(__doc__, version='fitlog v1.0', argv=argv, help=False)
    argv = sys.argv[1:]
    if args['<command>'] in ('init', 'revert'):
        if args['--help'] or args['-h']:
            fit_cmd(['-h'])
        else:
            fit_cmd(argv)
    elif args['<command>'] == 'log':
        if args['--help'] or args['-h']:
            log_cmd(['-h'])
        else:
            log_cmd(argv)
    elif args['<command>'] in ['help', None]:
        if len(argv) > 1:
            cmd = argv[1]
            if cmd == 'log':
                log_cmd(['-h'])
            elif cmd in ('init', 'revert'):
                fit_cmd(['-h'])
            else:
                print("Unknown command `{}`, only support [log, init, revert].".format(cmd))
                print(__doc__)
        else:
            print("You have to specify a command, support [log, init, revert].")
            print(__doc__)
    else:
        print("Unknown command: {}.".format(args['<command>']))
        print(__doc__)
