from flask import Flask, render_template

from flask import request, jsonify, redirect, url_for
import os
from flask import Blueprint

from fitlog.fastserver.server.table_utils import prepare_data, prepare_incremental_data
from fitlog.fastserver.server.table_utils import replace_with_extra_data

from fitlog.fastserver.server.data_container import all_data
from fitlog.fastgit import committer
from fitlog.fastserver.server.server_config import save_config
from fitlog.fastserver.server.server_config import save_extra_data

table_page = Blueprint("table_page", __name__, template_folder='templates')

first_time_access_table = True

@table_page.route('/table/table')
def get_table():
    global first_time_access_table
    log_dir = all_data['root_log_dir']
    log_config_path = all_data['log_config_path']
    if not first_time_access_table:
        if all_data['settings']['Refresh_from_disk']:
            save_all_data(all_data, log_dir, log_config_path)
            log_reader = all_data['log_reader']
            log_reader.set_log_dir(log_dir)
            all_data.update(prepare_data(log_reader, log_dir, log_config_path, all_data['debug']))
        else:
            replace_with_extra_data(all_data['data'], all_data['extra_data'])

    first_time_access_table = False
    data = all_data['data']

    return jsonify(column_order=all_data['column_order'], column_dict=all_data['column_dict'],
                   hidden_columns=all_data['hidden_columns'], data=data,
                   settings={key.replace('_', ' '):value for key, value in all_data['settings'].items()},
                   uuid=all_data['uuid'],
                   hidden_rows=list(all_data['hidden_rows'].keys()),
                   unchanged_columns=all_data['unchanged_columns'])

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
        all_data['deleted_rows'][id] = 1
    all_data['data'] = {id:log for id, log in all_data['data'].items() if id not in all_data['deleted_rows']}

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
        if not all_data['debug']:
            fit_id = request.json['fit_id']
            _suffix = request.json['suffix']
            response = committer.fitlog_revert(fit_id, all_data['root_log_dir'], _suffix)
            if response['status'] == 0:
                return jsonify(status='success', msg=response['msg'])
            else:
                return jsonify(status='fail', msg=response['msg'])
        return jsonify(status='success', msg="")
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

@table_page.route('/table')
def table():
    return render_template('table.html')

def check_uuid(gold_uuid, _uuid):
    if gold_uuid==_uuid:
        return None
    else:
        return {'status': 'fail',
                'msg': "The data are out-of-date, please refresh this page."}

def save_all_data(all_data, log_dir, log_config_path):
    if all_data['settings']['Save_settings'] and not all_data['debug']:  # 如果需要保存
        save_config(all_data, config_path=log_config_path)

        # save editable columns
        if len(all_data['extra_data']) != 0:
            extra_data_path = os.path.join(log_dir, 'log_extra_data.txt')
            save_extra_data(extra_data_path, all_data['extra_data'])

        print("Settings are saved to {}.".format(log_config_path))
