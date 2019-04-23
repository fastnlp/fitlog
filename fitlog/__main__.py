"""
Usage:
    fitlog <command> [<args>...]

Supported commands
    init        initialize a fitlog project
    revert      revert to a specific version
    log         visualize logs by a server.

See "fitlog help <command>" for more information on a specific command

"""
from docopt import docopt
from subprocess import call
import os

from .log_cmd import log_cmd


def main():
    file_dir = os.path.dirname(__file__)
    fit_path = os.path.join(file_dir, 'fit_cmd.py')
    log_path = os.path.join(file_dir, 'log_cmd.py')
    args = docopt(__doc__, version='fitlog v1.0')
    argv = [args['<command>']] + args['<args>']
    if args['<command>'] in ('init', 'revert'):
        call(['python', fit_path] + argv)
    elif args['<command>'] == 'log':
        log_cmd(argv)
    elif args['<command>'] in ['help', None]:
        if len(args['<args>']) != 0:
            cmd = args['<args>'][0]
            if cmd == 'log':
                call(['python', log_path, '-h'])
            elif cmd in ('init', 'revert'):
                call(['python', fit_path, '-h'])
            else:
                print("Unknown command `{}`, only support [log, init, revert].".format(cmd))
                print(__doc__)
        else:
            print("You have to specify a command, support [log, init, revert].")
            print(__doc__)
    else:
        print("Unknown command: {}.".format(args['<command>']))
        print(__doc__)


if __name__ == '__main__':
    main()
