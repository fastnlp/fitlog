# 这个文件主要是用于响应summary以及计算summary等


from flask import render_template
import traceback

from flask import request, jsonify
from flask import Blueprint
from .server.data_container import all_data
from .server.server_config import _get_config_names
from .server.summary_utils import _get_all_summuries
from .server.summary_utils import check_uuid_summary
from .server.summary_utils import get_summary_selection_from_logs
from .server.summary_utils import read_logs
from .server.summary_utils import generate_summary_table
from .server.summary_utils import _summary_eq
from .server.summary_utils import read_summary
from ..fastgit.committer import _colored_string
from .server.summary_utils import save_summary
from werkzeug.utils import secure_filename
from .server.summary_utils import  delete_summary
from .server.utils import stringify_dict_key

summary_page = Blueprint('summary_page', __name__, template_folder='templates')

SUMMARIES = {}

@summary_page.route('/summary', methods=['GET', 'POST'])
def summary_index():
    # 这种情况直接寻找当前的default_config, check是否有summary
    ids = {}
    if request.method=='POST':
        # 应该table传入ids，{‘ids':[xxx]}
        #  一个list的ids,
        for id in  request.values['ids'].split(','):
            ids[id] = 1

    return render_template('summary.html',  server_uuid=all_data['uuid'], log_names=ids,
                           settings={key.replace('_', ' '):value for key, value in all_data['settings'].items()})

# 获取可选的config与summary与所有的summaries
@summary_page.route('/summary/summary_config', methods=['POST'])
def summaries_configs():
    res = check_uuid_summary(all_data['uuid'], request.json['uuid'])
    if res != None:
        return jsonify(res)
    root_log_dir = all_data['root_log_dir']
    config_names = {}
    for name in _get_config_names(root_log_dir):
        if name == all_data['log_config_name']:
            config_names[name] = 1
        else:
            config_names[name] = 0

    summary_names = {key:0 for key in _get_all_summuries(root_log_dir)}
    summary_names['Create New Summary'] = 1
    return jsonify({'status':'success',
                    'summary_names':summary_names,
                    'config_names':config_names})

@summary_page.route('/summary/summary_json', methods=['POST'])
def summary_json():
    # 获取某个summary的内容
    res = check_uuid_summary(all_data['uuid'], request.json['uuid'])
    if res != None:
        return jsonify(res)
    summary_name = request.json['summary_name']
    summary_names = _get_all_summuries(all_data['root_log_dir'])
    if summary_names.index(summary_name)==-1:
        return jsonify(status='fail', msg='There is no summary named `{}`.'.format(summary_name))
    else:
        summary = read_summary(all_data['root_log_dir'], summary_name)
        summary.pop('extra_data', None)
        return jsonify(status='success', summary=summary)

@summary_page.route('/summary/selections', methods=['POST'])
def summary_selections():
    # 根据数据生成axis与metric的选项
    res = check_uuid_summary(all_data['uuid'], request.json['uuid'])
    if res != None:
        return jsonify(res)
    try:
        if 'config_name' in request.json:
            logs = read_logs(request.json['config_name'], all_data['root_log_dir'])
        elif 'log_names' in request.json:
            logs = read_logs(request.json['log_names'], all_data['root_log_dir'], all_data['extra_data'])
        else:
            raise ValueError("Corrupted request.")
        if isinstance(logs, dict):
            return jsonify(logs)
        if len(logs)==0:
            return jsonify(status='fail', msg='No valid log found.')
        axises, metrics = get_summary_selection_from_logs(logs)
        if len(metrics)==0:
            return jsonify(status='fail', msg='No valid metric.')
        if len(axises)==0:
            return jsonify(status='fail', msg='No valid hypers or others')

        return jsonify(status='success', metrics=metrics, axises=axises)
    except Exception as e:
        print(e)
        return jsonify(status='fail', msg="Unknown error from the server.")

@summary_page.route('/summary/new_summary', methods=['POST'])
def new_summary():
    # 根据前端发送的数据生成新的summary
    res = check_uuid_summary(all_data['uuid'], request.json['uuid'])
    if res != None:
        return jsonify(res)
    try:
        vertical = request.json['vertical']
        horizontals = request.json['horizontals']
        method = request.json['method']
        criteria = request.json['criteria']
        results = request.json['results']
        result_maps = request.json['result_maps']
        selected_data = request.json['selected_data']
        summary_name = request.json['summary_name']
        extra_summary = []
        summary_names = _get_all_summuries(all_data['root_log_dir'])
        if summary_name in summary_names:
            request_summary = {'vertical': vertical,
                               'horizontals': horizontals,
                               'method': method,
                               'criteria':criteria,
                               'results': results,
                               'result_maps':result_maps}
            summary = read_summary(all_data['root_log_dir'], summary_name)
            if _summary_eq(request_summary, summary):
                extra_summary = summary.pop('extra_data', {})
        # {'data': data, 'unchanged_columns':unchange_columns, 'column_order': new_column_order, 'column_dict':new_column_dict,
        #            'hidden_columns': new_hidden_columns, 'status':}
        summary_table = generate_summary_table(vertical, horizontals, method, criteria, results, result_maps, selected_data,
                     all_data['root_log_dir'], all_data['extra_data'], extra_summary)

        # 为了修复不能以bool为key的bug
        summary_table = stringify_dict_key(summary_table)
        def change_order_keys_to_str(_dict):
            for key, value in _dict.copy().items():
                if key == 'OrderKeys':
                    value = list(map(str, value))
                    _dict[key] = value
                if isinstance(value, dict):
                    change_order_keys_to_str(value)
        change_order_keys_to_str(summary_table)

        return jsonify(summary_table)

    except Exception as e:
        print(e)
        traceback.print_exc()
        return jsonify(status='fail', msg="Please refer to your server for exception reason.")

@summary_page.route('/summary/save_summary', methods=['POST'])
def save_summary_api():
    res = check_uuid_summary(all_data['uuid'], request.json['uuid'])
    if res != None:
        return jsonify(res)
    summary = request.json['summary']
    summary_name = request.json['summary_name']
    try:
        summary_name = secure_filename(summary_name)
        save_summary(all_data['root_log_dir'], summary_name, summary)
        return jsonify(status='success', summary_name=summary_name)
    except Exception as e:
        print(_colored_string("Save summary failed.", 'red'))
        print(e)
        return jsonify(status='fail', msg='Fail to save summary, check server log.')

@summary_page.route('/summary/delete_summary', methods=['POST'])
def delete_summary_api():
    res = check_uuid_summary(all_data['uuid'], request.json['uuid'])
    if res != None:
        return jsonify(res)
    summary_names = request.json['summary_names']
    fail_to_delete = summary_names.copy()
    for summary_name in summary_names[::-1]:
        try:
            flag = delete_summary(all_data['root_log_dir'], summary_name)
            if flag:
                fail_to_delete.pop(-1)
        except Exception as e:
            print(_colored_string("Delete summary {} encountered an error.".format(summary_name), 'red'))
            print(repr(e))
            fail_to_delete.append(summary_name)

    if fail_to_delete:
        return jsonify(status='fail', msg="Fail to delete {}.".format(fail_to_delete))
    else:
        return jsonify(status='success')

