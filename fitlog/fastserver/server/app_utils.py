

import argparse
import socket


def cmd_parser():
    # 返回为app.py准备的command line parser
    parser = argparse.ArgumentParser(description="To display your experiment logs in html.")

    parser.add_argument('-d', '--log_dir', help='Where to read logs. This directory should include a lot of logs.',
                         required=True, type=str)
    parser.add_argument('-l', '--log_config_name',
                        help="Log config name. Will try to find it in {log_dir}/{log_config_name}. Default is "
                             "default_cfg.txt",
                        required=False,
                        type=str, default='default_cfg.config')
    parser.add_argument('-p', '--port', help='What port to use. Default 5000, but when it is blocked, pick 5001 ...',
                         required=False, type=int, default=5000)

    return parser

def get_usage_port(start_port):
    # 给定一个start_port, 依次累加直到找到一个可用的port
    while start_port<65535:
        if net_is_used(start_port):
            start_port += 1
        else:
            return start_port

def net_is_used(port, ip='0.0.0.0'):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, port))
        s.shutdown(2)
        return True
    except:
        return False


