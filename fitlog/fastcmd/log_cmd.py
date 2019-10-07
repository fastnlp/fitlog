"""
Usage:
    fitlog log <log-dir> [--log-config-name=L] [--port=P] [--standby-hours=S] [--token=T] [--ip=I]

Arguments:
    log-dir                 Where to find logs.

Options:
    -h --help               This is a command to start fitlog server to visualize logs.
    -l=L --log-config-name  Log server config name. Must under the folder of <log-dir>. [default: default.cfg]
    -p=P --port             Which port to start to looking for usable port.[default: 5000]
    -s=S --standby-hours    How long to wait before the server . [default: 48]
    -t=T --token            If this is used, your have to specify the token when accessing. Default no token.
    -i=I --ip               Which ip to bind to. Default is 0.0.0.0 [default: 0.0.0.0]
"""
from docopt import docopt
import os
from ..fastserver.app import start_app


def log_cmd(argv=None):
    if argv:
        args = docopt(__doc__, version='fitlog v1.0', argv=argv)
    else:
        args = docopt(__doc__, version='fitlog v1.0')

    log_dir = args['<log-dir>']
    start_port = int(args['--port'])
    log_config_name = args['--log-config-name']
    standby_hours = int(args['--standby-hours'])
    ip = args['--ip']
    token = args['--token']
    if token is False:
        token = None
    if not os.path.isabs(log_dir):
        cwd = os.getcwd()
        log_dir = os.path.join(cwd, log_dir)

    if log_config_name!=None and not log_config_name.endswith('.cfg'):
        raise RuntimeError("log_config_name has to end with .cfg.")

    if not os.path.exists(log_dir):
        raise RuntimeError("{} is not exist.".format(log_dir))
    
    if not os.path.isdir(log_dir):
        raise NotADirectoryError("{} is not a directory.".format(log_dir))
    
    log_dir = os.path.abspath(log_dir)
    if os.path.dirname(log_config_name) != '':
        raise ValueError("log_config_name can only be a filename.")
    
    start_app(log_dir, log_config_name, start_port, standby_hours, ip, token)


if __name__ == '__main__':
    log_cmd()
