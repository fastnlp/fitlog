

import argparse
import socket
import time
from urllib import request as urequest
import threading

def cmd_parser():
    # 返回为app.py准备的command line parser
    parser = argparse.ArgumentParser(description="To display your experiment logs in html.")

    parser.add_argument('-d', '--log_dir', help='Where to read logs. This directory should include a lot of logs.',
                         required=True, type=str)
    parser.add_argument('-l', '--log_config_name',
                        help="Log config name. Will try to find it in {log_dir}/{log_config_name}. Default is "
                             "default.cfg",
                        required=False,
                        type=str, default='default.cfg')
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

class ServerWatcher(threading.Thread):
    def __init__(self, LEAST_REQUEST_TIMESTAMP):
        super().__init__()
        self.deque = LEAST_REQUEST_TIMESTAMP
        self._stop_flag = False

    def set_server_wait_seconds(self, server_wait_seconds):
        self.server_wait_seconds = server_wait_seconds

    def run(self):
        while (time.time() - self.deque[0])<self.server_wait_seconds and not self._stop_flag:
            time.sleep(1)
        print("This server is going to shut down.")
        try:
            if not self._stop_flag:  # 不是手动关闭的
                req = urequest.Request('http://127.0.0.1:5000/kill', headers={}, data=''.encode('utf-8'))
                page = urequest.urlopen(req).read().decode('utf-8')
        except Exception as e:
            print(e)
            raise RuntimeError("Error occurred when try to automatically shut down server.")

    def stop(self):
        self._stop_flag = True

