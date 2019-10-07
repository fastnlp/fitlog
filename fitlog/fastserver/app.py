
import os
import uuid

from flask import Flask, url_for, redirect
from .chart_app import chart_page
from .table_app import table_page
from .summary_app import summary_page
from .line_app import line_page
from .server.table_utils import save_all_data
from .server.app_utils import get_usage_port
from .server.data_container import all_data
from .server.data_container import handler_watcher
from ..fastlog import log_reader
from .server.table_utils import prepare_data
from flask import request
import time
from .server.app_utils import ServerWatcher
from flask import send_from_directory
from urllib import request as urequest
from threading import Timer
from flask import jsonify
from .server.utils import check_uuid
from ..fastgit.committer import _colored_string

from collections import deque

app = Flask(__name__)

app.register_blueprint(chart_page)
app.register_blueprint(table_page)
app.register_blueprint(summary_page)
app.register_blueprint(line_page)

LEAST_REQUEST_TIMESTAMP = deque(maxlen=1)
LEAST_REQUEST_TIMESTAMP.append(time.time())

server_watcher = ServerWatcher(LEAST_REQUEST_TIMESTAMP)

@app.route('/')
def index():
    return redirect(url_for('table_page.table'))

@app.before_request
def update_last_request_ms():
    global LEAST_REQUEST_TIMESTAMP
    LEAST_REQUEST_TIMESTAMP.append(time.time())

@app.route('/kill', methods=['POST'])
def seriouslykill():
    time.sleep(1)
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return "stopping"

@app.route('/arange_kill', methods=['POST'])
def arange_kill():
    res = check_uuid(all_data['uuid'], request.json['uuid'])
    if res!=None:
        return jsonify(res)
    def shutdown():
        req = urequest.Request('http://127.0.0.1:{}/kill'.format(all_data['port']), headers={}, data=''.encode('utf-8'))
        page = urequest.urlopen(req).read().decode('utf-8')
    print("Shutting down from the frontend...")
    Timer(1.0, shutdown).start()
    return jsonify(status='success', msg='')

@app.route('/table.ico')
def get_table_ico():
    return send_from_directory(os.path.join('.', 'static', 'img'), 'table.ico')

@app.route('/chart.ico')
def get_chart_ico():
    return send_from_directory(os.path.join('.', 'static', 'img'), 'chart.ico')

def start_app(log_dir, log_config_name, start_port, standby_hours, ip='0.0.0.0', token=None):
    os.chdir(os.path.dirname(os.path.abspath(__file__))) # 可能需要把运行路径移动到这里
    all_data['root_log_dir'] = log_dir # will be used by chart_app
    server_wait_seconds = int(standby_hours*3600)
    print("This server will automatically shutdown if no api access for {} hours.".format(standby_hours))
    all_data['log_config_name'] = log_config_name
    all_data['log_reader'] = log_reader
    if token is None:
        all_data['token'] = None
    else:
        all_data['token'] = str(token)

    # 准备数据
    all_data.update(prepare_data(log_reader, all_data['root_log_dir'], all_data['log_config_name']))
    print("Finish preparing data. Found {} records in {}.".format(len(all_data['data']), log_dir))
    all_data['uuid'] = str(uuid.uuid1())

    port = get_usage_port(start_port=start_port)
    server_watcher.set_server_wait_seconds(server_wait_seconds)
    server_watcher.start()
    if all_data['token']!=None:
        print(_colored_string("You specify token:{}, remember to add this token when access your table.".format(all_data['token']),
                              color='red'))
    all_data['port'] = port
    app.run(host=ip, port=port, debug=False, threaded=True)

    # TODO 输出访问的ip地址
    print("Shutting down server...")
    save_all_data(all_data,  all_data['root_log_dir'], all_data['log_config_name'])
    handler_watcher.stop()
    server_watcher.stop()

if __name__ == '__main__':
    from .server.app_utils import cmd_parser
    parser = cmd_parser()
    args =parser.parse_args()

    start_app(args.log_dir, args.log_config_name, args.port, 1, '123')



