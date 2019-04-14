
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


app = Flask(__name__)

app.register_blueprint(chart_page)
app.register_blueprint(table_page)

@app.route('/')
def index():
    return redirect(url_for('table_page.table'))

if __name__ == '__main__':
    all_data['debug'] = False  # when in debug mode, no call to other modules will be initialized.
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
    all_data['root_log_dir'] = log_dir # will be used by chart_app
    if os.path.dirname(args.log_config_name)!='':
        raise ValueError("log_config_name can only be a filename.")

    log_config_path = os.path.join(log_dir, args.log_config_name)
    all_data['log_config_path'] = log_config_path
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