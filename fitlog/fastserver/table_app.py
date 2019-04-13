from flask import Flask, render_template

from flask import request, jsonify, redirect, url_for
import uuid
import os

from fitlog.fastserver.server.table_utils import prepare_data, prepare_incremental_data
from fitlog.fastserver.server.table_utils import replace_with_extra_data
from fitlog.fastserver.server.app_utils import cmd_parser
from fitlog.fastserver.server.app_utils import get_usage_port

from fitlog.fastserver.server.server_config import save_config
from fitlog.fastserver.server.server_config import save_extra_data
from fitlog.fastserver.server.data_container import all_data
from fitlog.fastserver.server.data_container import all_handlers, handler_watcher
from fitlog.fastgit import committer
from fitlog.fastlog import log_reader

from fitlog.fastserver.chart_app import chart_page

app = Flask(__name__)

app.register_blueprint(chart_page)

all_data['debug'] = False # when in debug mode, no call to other modules will be initialized.
log_dir = ''
log_config_path = ''
first_time_access_table = True

@app.route('/')
def hello_world():
    return redirect(url_for('table'))
    # return render_template('index.html')

@app.route('/table/table')
def get_table():
    global all_data, first_time_access_table, log_dir, log_config_path
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

@app.route('/table/refresh', methods=['POST'])
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

@app.route('/table/delete_records', methods=['POST'])
def delete_records():
    res = check_uuid(all_data['uuid'], request.json['uuid'])
    if res != None:
        return jsonify(res)
    ids = request.json['ids']
    for id in ids:
        all_data['deleted_rows'][id] = 1
    all_data['data'] = {log['id']:log for log in all_data['data'] if log['id'] not in all_data['deleted_rows']}

    return jsonify(status='success', msg='')

@app.route('/table/edit', methods=['POST'])
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

@app.route('/table/reset', methods=['POST'])
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

@app.route('/table/settings', methods=['POST'])
def settings():
    res = check_uuid(all_data['uuid'], request.json['uuid'])
    if res!=None:
        return jsonify(res)
    settings = request.json['settings']
    all_data['settings'].update({key.replace(' ', '_'):value for key, value in settings.items()})

    return jsonify(status='success', msg='')

@app.route('/table/hidden_rows', methods=['POST'])
def hidden_ids():
    res = check_uuid(all_data['uuid'], request.json['uuid'])
    if res!=None:
        return jsonify(res)
    ids = request.json['ids']
    all_data['hidden_rows'].clear()
    for id in ids:
        all_data['hidden_rows'][id] = 1

    return jsonify(status='success', msg='')

@app.route('/table/hidden_columns', methods=['POST'])
def hidden_columns():
    res = check_uuid(all_data['uuid'], request.json['uuid'])
    if res!=None:
        return jsonify(res)
    hidden_columns = request.json['hidden_columns']
    all_data['hidden_columns'] = hidden_columns
    return jsonify(status='success', msg='')

@app.route('/table/column_order', methods=['POST'])
def column_order():
    res = check_uuid(all_data['uuid'], request.json['uuid'])
    if res != None:
        return jsonify(res)
    column_order = request.json['column_order']
    all_data['column_order'] = column_order
    return jsonify(status='success', msg='')

@app.route('/table')
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


if __name__ == '__main__':
    parser = cmd_parser()
    args = parser.parse_args()

    start_port = args.port
    log_dir = args.log_dir
    cwd = os.path.abspath('.')
    if not os.path.isabs(log_dir):
        log_dir = os.path.join(cwd, log_dir)
    if not os.path.isdir(log_dir):
        raise IsADirectoryError("{} is not a directory.".format(log_dir))

    log_dir = os.path.abspath(log_dir)
    all_data['root_log_dir'] = log_dir # will be used by chart_app.py
    if os.path.dirname(args.log_config_name)!='':
        raise ValueError("log_config_name can only be a filename.")

    log_config_path = os.path.join(log_dir, args.log_config_name)

    log_reader.set_log_dir(log_dir)
    all_data['log_reader'] = log_reader

    # 准备数据
    all_data.update(prepare_data(log_reader, log_dir, log_config_path, all_data['debug']))
    print("Finish preparing data. Found {} records in {}.".format(len(all_data['data']), log_dir))
    all_data['uuid'] = str(uuid.uuid1())

    port = get_usage_port(start_port=start_port)
    app.run(host='0.0.0.0', port=port)

    save_all_data(all_data, log_dir, log_config_path)
    handler_watcher.stop()