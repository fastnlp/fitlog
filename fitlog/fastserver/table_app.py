from flask import render_template

from flask import request, jsonify
from flask import Blueprint

from .server.table_utils import prepare_data, prepare_incremental_data

from .server.data_container import all_data
from ..fastgit import committer
from .server.utils import replace_nan_inf
from .server.utils import check_uuid
from .server.table_utils import save_all_data
from .server.table_utils import replace_with_extra_data

from werkzeug.utils import secure_filename
import glob

table_page = Blueprint("table_page", __name__, template_folder='templates')

first_time_access = True

@table_page.route('/table/table')
def get_table():
    global first_time_access
    if not first_time_access:
        log_dir = all_data['root_log_dir']
        log_config_name = all_data['log_config_name']
        log_reader = all_data['log_reader']
        log_reader.set_log_dir(log_dir)
        all_data.update(prepare_data(log_reader, log_dir, log_config_name, all_data))

    first_time_access = False
    data = all_data['data'].copy() # all_data['data'] 只包含从硬盘的读取的log的信息
    replace_with_extra_data(data, all_data['extra_data'], all_data['filter_condition'], all_data['deleted_rows'])
    replace_nan_inf(data)

    return jsonify(column_order=all_data['column_order'], column_dict=all_data['column_dict'],
                   hidden_columns=all_data['hidden_columns'],
                   data=data,
                   settings={key.replace('_', ' '):value for key, value in all_data['settings'].items()},
                   uuid=all_data['uuid'],
                   hidden_rows=list(all_data['hidden_rows'].keys()),
                   unchanged_columns=all_data['unchanged_columns'],
                   log_config_name=all_data['log_config_name'])

@table_page.route('/table/refresh', methods=['POST'])
def refresh_table():
    res = check_uuid(all_data['uuid'], request.json['uuid'])
    if res != None:
        return jsonify(res)
    log_reader = all_data['log_reader']
    new_logs = log_reader.read_logs(all_data['deleted_rows'])
    try:
        if len(new_logs)==0:
            return jsonify(status='success', msg='Update successfully, no update found.', new_logs=[], updated_logs=[])
        else:
            new_logs, updated_logs = prepare_incremental_data(all_data['data'], new_logs, all_data['field_columns'])
            replace_nan_inf(new_logs)
            replace_nan_inf(updated_logs)
            return jsonify(status='success', msg='Update successfully, {} log have updates, {} newly added.'\
                           .format(len(updated_logs), len(new_logs)),
                           new_logs=new_logs, updated_logs=updated_logs)
    except:
        return jsonify(status='fail', msg="Unknown error from server.")

@table_page.route('/table/delete_records', methods=['POST'])
def delete_records():
    res = check_uuid(all_data['uuid'], request.json['uuid'])
    if res != None:
        return jsonify(res)
    ids = request.json['ids']
    for id in ids:
        if id in all_data['data']:
            all_data['deleted_rows'][id] = 1
        elif id in all_data['extra_data']:
            # all_data['extra_data'].pop(id)
            all_data['deleted_rows'][id] = 1

    return jsonify(status='success', msg='')

@table_page.route('/table/edit', methods=['POST'])
def table_edit():
    try:
        # 包含field, id, new_field_value三个值
        res = check_uuid(all_data['uuid'], request.json['uuid'])
        if res != None:
            return jsonify(res)
        id = request.json['id']
        field = request.json['field']
        new_field_value = request.json['new_field_value']
        if id in all_data['extra_data']:
            all_data['extra_data'][id][field] = new_field_value
        else:
            all_data['extra_data'][id] = {field:new_field_value}

        return jsonify(status='success', msg='')
    except Exception as e:
        print(e)
        return jsonify(status='fail', msg='Unknown error fail to save edit results.')

@table_page.route('/table/reset', methods=['POST'])
def table_reset():
    try:
        res = check_uuid(all_data['uuid'], request.json['uuid'])
        if res != None:
            return jsonify(res)
        fit_id = request.json['fit_id']
        _suffix = request.json['suffix']
        response = committer.fitlog_revert(fit_id, all_data['root_log_dir'], _suffix)
        if response['status'] == 0:
            return jsonify(status='success', msg=response['msg'])
        else:
            return jsonify(status='fail', msg=response['msg'])
    except Exception as e:
        print(e)
        return jsonify(status='fail', msg='Unknown error from server.')

@table_page.route('/table/settings', methods=['POST'])
def settings():
    res = check_uuid(all_data['uuid'], request.json['uuid'])
    if res!=None:
        return jsonify(res)
    settings = request.json['settings']
    all_data['settings'].update({key.replace(' ', '_'):value for key, value in settings.items()})

    return jsonify(status='success', msg='')

@table_page.route('/table/save_config_name', methods=['POST'])
def save_config_name():
    res = check_uuid(all_data['uuid'], request.json['uuid'])
    if res!=None:
        return jsonify(res)
    log_config_name = request.json['save_config_name']
    log_config_name = secure_filename(log_config_name)
    if len(log_config_name)!=0:
        if all_data['log_config_name']!=log_config_name:
            all_data['log_config_name'] = log_config_name
        return jsonify(status='success', msg=log_config_name)
    else:
        return jsonify(status='fail', msg='Invalid file name')

@table_page.route('/table/hidden_rows', methods=['POST'])
def hidden_ids():
    res = check_uuid(all_data['uuid'], request.json['uuid'])
    if res!=None:
        return jsonify(res)
    ids = request.json['ids']
    all_data['hidden_rows'].clear()
    for id in ids:
        all_data['hidden_rows'][id] = 1

    return jsonify(status='success', msg='')

@table_page.route('/table/hidden_columns', methods=['POST'])
def hidden_columns():
    res = check_uuid(all_data['uuid'], request.json['uuid'])
    if res!=None:
        return jsonify(res)
    hidden_columns = request.json['hidden_columns']
    all_data['hidden_columns'] = hidden_columns
    return jsonify(status='success', msg='')

@table_page.route('/table/column_order', methods=['POST'])
def column_order():
    res = check_uuid(all_data['uuid'], request.json['uuid'])
    if res != None:
        return jsonify(res)
    column_order = request.json['column_order']
    all_data['column_order'] = column_order
    return jsonify(status='success', msg='')

@table_page.route('/table/row', methods=['POST'])
def add_row():
    res = check_uuid(all_data['uuid'], request.json['uuid'])
    if res != None:
        return jsonify(res)
    new_row = request.json['row']
    if new_row['id'] not in all_data['data']:
        all_data['data'][new_row['id']] = new_row
        all_data['extra_data'][new_row['id']] = new_row
        return jsonify(status='success', msg='')
    else:
        return jsonify(status='fail', msg='Duplicated id.')

@table_page.route('/table/save_settings', methods=['POST'])
def save():
    res = check_uuid(all_data['uuid'], request.json['uuid'])
    if res != None:
        return jsonify(res)
    if 'condition' in request.json:
        condition = request.json['condition'] # {'key': 'value'}
        all_data['filter_condition'].update(condition)
    log_dir = all_data['root_log_dir']
    log_config_name = all_data['log_config_name']
    save_all_data(all_data, log_dir, log_config_name)
    return jsonify(status='success', msg='')

@table_page.route('/table')
def table():
    if all_data['token'] != None:
        return jsonify(msg='This url needs a token to access. If you did not specify a token when start the server, '
                           'you may access the wrong ip or port. If you specify a token when start the server, '
                           'use http://{your server ip}:{port}/table/{token} to access.')
    return render_template('table.html')

@table_page.route('/table/<token>')
def table_with_token(token):
    if token!=all_data['token'] or all_data['token'] is None:
        return jsonify(msg='Wrong token or you are not using a token')
    return render_template('table.html')

@table_page.route('/table/configs', methods=['POST'])
def table_configs():
    res = check_uuid(all_data['uuid'], request.json['uuid'])
    if res != None:
        return jsonify(res)
    # 读取当前可以使用的config有哪些

