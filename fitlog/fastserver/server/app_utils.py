

import os
import argparse
import socket
from fitlog.fastserver.server.server_config import read_extra_data
from fitlog.fastserver.server.server_config import read_server_config
from fitlog.fastserver.server.table_utils import generate_columns
from fitlog.fastserver.server.test import generate_data

from fitlog.fastlog2.log_reader import read_logs

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



def prepare_data(log_dir, log_config_path, debug=False): # 准备好需要的数据， 应该包含从log dir中读取数据
    """

    :param log_dir: str, 哪里是存放所有log的大目录
    :param log_config_path: 从哪里读取config
    :param debug: 是否在debug，如果debug的话，就不调用非server的接口
    :return:
    """
    print("Start preparing data.")
    # 1. 从log读取数据

    log_dir = os.path.abspath(log_dir)
    log_config_path = os.path.abspath(log_config_path)

    if debug:
        logs = generate_data(num_records=100)
    else:
        logs = read_logs(log_dir)

    if len(logs)==0:
        raise ValueError("No valid log found in {}.".format(log_dir))

    # 读取log_setting_path
    all_data = read_server_config(log_config_path)

    # read extra_data
    extra_data_path = os.path.join(log_dir, 'log_extra_data.txt')
    extra_data = {}
    if os.path.exists(extra_data_path):
        extra_data = read_extra_data(extra_data_path)
    all_data['extra_data'] = extra_data

    # 1. 删除不要的
    deleted_rows = all_data['deleted_rows']
    new_logs = []
    for log in logs:
        if log['id'] not in deleted_rows:
            new_logs.append(log)

    if len(logs)!=0 and len(new_logs)==0:
        raise ValueError("It seems like all logs are included in deleted_logs.")

    # 2. 取出其他settings
    hidden_columns = all_data['hidden_columns']
    column_order = all_data['column_order']
    editable_columns = all_data['editable_columns']
    exclude_columns = all_data['exclude_columns']
    ignore_unchanged_columns = all_data['basic_settings']['ignore_unchanged_columns']
    str_max_length = all_data['basic_settings']['str_max_length']
    round_to = all_data['basic_settings']['round_to']

    new_all_data = generate_columns(logs=new_logs, hidden_columns=hidden_columns, column_order=column_order,
                                editable_columns=editable_columns,
                     exclude_columns=exclude_columns, ignore_unchanged_columns=ignore_unchanged_columns,
                     str_max_length=str_max_length, round_to=round_to)
    all_data.update(new_all_data)

    replace_with_extra_data(all_data['data'], extra_data)

    return all_data

def replace_with_extra_data(data, extra_data):
    # 将数据进行替换
    if len(extra_data)!=0:
        for d in data:
            if d['id'] in extra_data:
                for key, value in extra_data[d['id']].items():
                    d[key] = value