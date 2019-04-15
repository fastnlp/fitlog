
import os
import uuid

from flask import Flask, url_for, redirect
from fitlog.fastserver.chart_app import chart_page
from fitlog.fastserver.table_app import table_page, save_all_data
from fitlog.fastserver.server.app_utils import cmd_parser
from fitlog.fastserver.server.app_utils import get_usage_port
from fitlog.fastserver.server.data_container import all_data
from fitlog.fastserver.server.data_container import all_handlers, handler_watcher
from fitlog.fastlog import log_reader
from fitlog.fastserver.server.table_utils import prepare_data
from flask import request
import time
from fitlog.fastserver.server.app_utils import ServerWatcher

from collections import deque

all_data['debug'] = False  # when in debug mode, no call to other modules will be initialized.

app = Flask(__name__)

app.register_blueprint(chart_page)
app.register_blueprint(table_page)

LEAST_REQUEST_TIMESTAMP = deque(maxlen=1)
LEAST_REQUEST_TIMESTAMP.append(time.time())
# TODO 修改为配置项
server_wait_seconds = 60

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


def start_app(log_dir, log_config_name, start_port, standby_hours):
    os.chdir(os.path.dirname(os.path.abspath(__file__))) # 可能需要把运行路径移动到这里
    all_data['root_log_dir'] = log_dir # will be used by chart_app
    server_wait_seconds = int(standby_hours*3600)
    log_config_path = os.path.join(log_dir, log_config_name)
    all_data['log_config_path'] = log_config_path
    log_reader.set_log_dir(log_dir)
    all_data['log_reader'] = log_reader

    # 准备数据
    all_data.update(prepare_data(log_reader, log_dir, log_config_path, all_data['debug']))
    print("Finish preparing data. Found {} records in {}.".format(len(all_data['data']), log_dir))
    all_data['uuid'] = str(uuid.uuid1())

    port = get_usage_port(start_port=start_port)
    server_watcher.set_server_wait_seconds(server_wait_seconds)
    server_watcher.start()
    app.run(host='0.0.0.0', port=port)

    # TODO 输出访问的ip地址

    save_all_data(all_data, log_dir, log_config_path)
    handler_watcher.stop()
    server_watcher.stop()

if __name__ == '__main__':
    from fitlog.fastserver.server.app_utils import cmd_parser
    parser = cmd_parser()
    args =parser.parse_args()

    start_app(args.log_dir, args.log_config_name, args.port, 1)



