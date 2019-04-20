
import os
import uuid

from flask import Flask, url_for, redirect
from fitlog.fastserver.chart_app import chart_page
from fitlog.fastserver.table_app import table_page
from fitlog.fastserver.server.table_utils import save_all_data
from fitlog.fastserver.server.app_utils import get_usage_port
from fitlog.fastserver.server.data_container import all_data
from fitlog.fastserver.server.data_container import handler_watcher
from fitlog.fastlog import log_reader
from fitlog.fastserver.server.table_utils import prepare_data
from flask import request
import time
from fitlog.fastserver.server.app_utils import ServerWatcher
from flask import send_from_directory

from collections import deque

app = Flask(__name__)

app.register_blueprint(chart_page)
app.register_blueprint(table_page)

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
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return "stopping"

@app.route('/table.ico')
def get_table_ico():
    return send_from_directory(os.path.join('.', 'static', 'img'), 'table.ico')

@app.route('/chart.ico')
def get_chart_ico():
    return send_from_directory(os.path.join('.', 'static', 'img'), 'chart.ico')

def start_app(log_dir, log_config_name, start_port, standby_hours):
    os.chdir(os.path.dirname(os.path.abspath(__file__))) # 可能需要把运行路径移动到这里
    all_data['root_log_dir'] = log_dir # will be used by chart_app
    server_wait_seconds = int(standby_hours*3600)
    all_data['log_config_name'] = log_config_name
    log_reader.set_log_dir(log_dir)
    all_data['log_reader'] = log_reader

    # 准备数据
    all_data.update(prepare_data(log_reader, all_data['root_log_dir'], all_data['log_config_name']))
    print("Finish preparing data. Found {} records in {}.".format(len(all_data['data']), log_dir))
    all_data['uuid'] = str(uuid.uuid1())

    port = get_usage_port(start_port=start_port)
    server_watcher.set_server_wait_seconds(server_wait_seconds)
    server_watcher.start()
    app.run(host='0.0.0.0', port=port, debug=False)

    # TODO 输出访问的ip地址
    print("Shutting down server...")
    save_all_data(all_data,  all_data['root_log_dir'], all_data['log_config_name'])
    handler_watcher.stop()
    server_watcher.stop()

if __name__ == '__main__':
    from fitlog.fastserver.server.app_utils import cmd_parser
    parser = cmd_parser()
    args =parser.parse_args()

    start_app(args.log_dir, args.log_config_name, args.port, 1)



