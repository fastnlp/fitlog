from flask import render_template
from flask import request, jsonify
import random
import os
from flask import Blueprint
from .server.data_container import all_data, all_handlers, handler_watcher
from ..fastlog.log_read import is_log_dir_has_step, is_log_record_finish
from .server.chart_utils import MultiChartStepLogHandler
from .server.utils import check_uuid

import uuid

multi_chart_page = Blueprint("multi_chart_page", __name__, template_folder='templates')

@multi_chart_page.route('/multi_chart', methods=['POST'])
def chart():
    res = check_uuid(all_data['uuid'], request.values['uuid'])
    if res != None:
        return jsonify(res)

    logs = request.values['ids'].split(',')  # []
    titles = request.values['titles'].split(',')  # TODO 如何对比loss呢
    root_log_dir = all_data['root_log_dir']

    # check是否具有metric的记录
    has_step_logs = []
    finish_logs = []
    for log in logs:
        full_log_path = os.path.join(root_log_dir, log)
        if is_log_dir_has_step(full_log_path, ('metric.log',)):
            has_step_logs.append(log)
        if is_log_record_finish(full_log_path):
            finish_logs.append(log)

    msg = ''
    results = {}
    multi_chart_uuid = str(uuid.uuid1())
    find_titles = []
    if len(has_step_logs)>1:  # 至少得有两个吧
        # 需要读取数据
        update_every = all_data['chart_settings']['update_every']
        wait_seconds = update_every * 5  # 如果本来应该收到三次更新，但是却没有收到，则自动关闭
        max_no_updates = all_data['chart_settings']['max_no_updates']

        handler = MultiChartStepLogHandler(root_log_dir, has_step_logs, multi_chart_uuid,
                                 titles=titles, round_to=all_data['basic_settings']['round_to'],
                                 wait_seconds=wait_seconds, max_no_updates=max_no_updates)
        results = handler.update_logs(handler_names=('metric',))
        all_handlers[multi_chart_uuid] = handler
        if not handler_watcher._start:
            handler_watcher.start()

        for title in titles:
            if title in results:
                find_titles.append(title)
        if len(find_titles)==0:
            msg = 'No log has step information.'

        results['update_every'] = update_every
        results['max_no_updates'] = max_no_updates
        results['multi_chart_uuid'] = multi_chart_uuid

    else:
        # 没有的话怎么办
        msg = 'Less than 2 logs have step information.'

    return render_template('multi_chart.html', data=results, message=msg, multi_chart_uuid=multi_chart_uuid,
                           titles=','.join(find_titles), logs=request.values['ids'])


@multi_chart_page.route('/multi_chart/new_step', methods=['POST'])
def chart_new_step():
    # 获取某个log_dir的更新
    multi_chart_uuid = request.json['multi_chart_uuid']

    try:
        results = {}
        if multi_chart_uuid in all_handlers:
            handler = all_handlers[multi_chart_uuid]
            results = handler.update_logs()
        print(results)
        return jsonify(data=results, status='success')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status':'fail', 'message':f"Exception occurred in the server: {str(e)}."})

