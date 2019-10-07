from flask import render_template

from flask import request
from flask import Blueprint
from .server.data_container import all_data
from .server.table_utils import generate_columns
from .server.table_utils import expand_dict
from collections import defaultdict


line_page = Blueprint('line_page', __name__, template_folder='templates')

@line_page.route('/line', methods=['POST'])
def line_index():
    ids = request.values['ids']
    #  取出所有的logs
    flat_logs = [all_data['data'][id].copy() for id in ids.split(',')]
    hidden_columns = all_data['hidden_columns'].copy()

    #  删除不是共有的部分
    value_dict_count = defaultdict(list) # 每个key有多少个
    for log in flat_logs:
        for key in log.keys():
            value_dict_count[key] += [log[key]]
    for key, _lst in list(value_dict_count.items()):
        if len(_lst) != len(flat_logs):  # 有些没有这个值
            for log in flat_logs:
                log.pop(key, None)
        if len(set(_lst)) == 1: # 只有一个值
            hidden_columns[key] = 1

    logs = [expand_dict([log])[0] for log in flat_logs]
    # column_order, column_dict, hidden_columns, settings, logs
    hidden_columns['id'] = 1
    hidden_columns['memo'] = 1
    hidden_columns['meta'] = 1
    res = generate_columns(logs, hidden_columns=hidden_columns, column_order=all_data['column_order'], editable_columns={},
                     exclude_columns={}, ignore_unchanged_columns=False,
                     str_max_length=20, round_to=6, num_extra_log=0)

    column_order = res['column_order']
    column_order.pop('id')
    column_order['OrderKeys'].remove('id')
    if 'metric' in column_order:  # 将metric放在第一的位置
        column_order['OrderKeys'].remove('metric')
        column_order['OrderKeys'].insert(0, 'metric')
    column_dict = res['column_dict']
    column_dict.pop('id')
    hidden_columns = res['hidden_columns']
    data = res['data']
    for key, log in data.items():
        log.pop('id')

    return render_template('line.html',  data=data, column_order=column_order, column_dict=column_dict,
                           hidden_columns=hidden_columns)

