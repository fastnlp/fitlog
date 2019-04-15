from docopt import docopt
from subprocess import call
import os

from fitlog.log_cmd import log_cmd


__doc__ = """
Usage:
    fitlog <command> [<args>...]

Supported commands
    init        initialize a fitlog project
    revert      revert to a specific version
    log         visualize logs by a server.

See "fitlog help <command>" for more information on a specific command

"""

def main():
    filedir = os.path.dirname(__file__)
    fit_path = os.path.join(filedir, 'fit_cmd.py')
    log_path = os.path.join(filedir, 'log_cmd.py')
    args = docopt(__doc__, version='fitlog v1.0')
    argv = [args['<command>']] + args['<args>']
    if args['<command>'] in ('init', 'revert'):
        # TODO 看是否需要更改一下
        call(['python', fit_path] + argv)
    elif args['<command>']=='log':
        log_cmd(argv)
    elif args['<command>'] in ['help', None]:
        if len(args['<args>'])!=0:
            cmd = args['<args>'][0]
            if cmd == 'log':
                call(['python', log_path, '-h'])
            elif cmd in ('init', 'revert'):
                call(['python', fit_path, '-h'])
            else:
                raise ValueError("Unknown command `{}`, only support [log, init, revert].".format(cmd))
        else:
            raise ValueError("You have to specify a command, support [log, init, revert].")
    else:
        raise RuntimeError("Unknown command: {}.".format(args['<command>']))

if __name__ == '__main__':
    main()
