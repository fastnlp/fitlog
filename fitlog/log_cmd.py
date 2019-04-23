"""
Usage:
    fitlog log <log-dir> [--log-config-name L] [--port P] [--standby-hours S]

arguments:
    log-dir         Where to find logs.

options:
    -h --help       This is a command to start fitlog server to visualize logs.
    -l=L --log-config-name        Log server config name. Must under the folder of <log-dir>. [default: default.cfg]
    -p=P --port     Which port to start to looking for usable port.[default: 5000]
    -s=S --standby-hours    How long to wait before the server . [default: 48]

"""
from docopt import docopt
import os
from .fastserver.app import start_app


def log_cmd(argv):
    args = docopt(__doc__, argv=argv, version='fitlog v1.0')
    start_port = int(args['--port'])
    log_dir = args['<log-dir>']
    log_config_name = args['--log-config-name']
    standby_hours = int(args['--standby-hours'])
    if not os.path.isabs(log_dir):
        cwd = os.getcwd()
        log_dir = os.path.join(cwd, log_dir)
    
    if not os.path.exists(log_dir):
        raise RuntimeError("{} is not exist.".format(log_dir))
    
    if not os.path.isdir(log_dir):
        raise NotADirectoryError("{} is not a directory.".format(log_dir))
    
    log_dir = os.path.abspath(log_dir)
    if os.path.dirname(log_config_name) != '':
        raise ValueError("log_config_name can only be a filename.")
    
    start_app(log_dir, log_config_name, start_port, standby_hours)


if __name__ == '__main__':
    args = docopt(__doc__, version='fitlog v1.0')
