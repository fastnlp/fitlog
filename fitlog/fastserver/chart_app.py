from flask import render_template


from flask import request, jsonify
import random
import os
from flask import Blueprint
from .server.data_container import all_data, all_handlers, handler_watcher
from ..fastlog.log_read import is_log_dir_has_step, is_log_record_finish
from .server.chart_utils import ChartStepLogHandler
from .server.utils import replace_nan_inf
from .server.utils import check_uuid
from .server.chart_utils import _refine_logs

import uuid

# 用于进行字符替换，以使得字符串变短
full_name_map = {'name':'n', 'epoch':'e', 'value':'v', 'step': 's'}

chart_page = Blueprint("chart_page", __name__, template_folder='templates')

@chart_page.route('/chart', methods=['POST'])
def chart():
    log_dir = request.values['log_dir']
    finish = request.values['finish']
    save_log_dir = os.path.join(all_data['root_log_dir'], log_dir)
    chart_exclude_columns = all_data['chart_settings']['chart_exclude_columns']
    _uuid = str(uuid.uuid1())
    max_points = all_data['chart_settings']['max_points']
    update_every_second = all_data['chart_settings']['update_every']
    wait_seconds = update_every_second*3 # 如果本来应该收到三次更新，但是却没有收到，则自动关闭
    handler = ChartStepLogHandler(save_log_dir, _uuid, round_to=all_data['basic_settings']['round_to'],
                            max_steps=max_points,
                            wait_seconds=wait_seconds,
                            exclude_columns=chart_exclude_columns,
                            max_no_updates=all_data['chart_settings']['max_no_updates'])
    only_once = is_log_record_finish(save_log_dir) or finish=='true'
    points = handler.update_logs(only_once) # {'loss': [{}, {}], 'metric':[{}, {}]}
    total_steps = points.pop('total_steps', None)
    if not only_once:
        all_handlers[_uuid] = handler
        if not handler_watcher._start:
            handler_watcher.start()

    replace_nan_inf(points)

    return render_template('chart.html', log_dir=log_dir, data=points, chart_uuid=_uuid,
                           server_uuid=all_data['uuid'],
                           update_every=update_every_second*1000,
                           max_no_updates=all_data['chart_settings']['max_no_updates'],
                           total_steps=total_steps,
                           short_name_map = {value:key for key,value in full_name_map.items()})

@chart_page.route('/chart/new_step', methods=['POST'])
def chart_new_step():
    # 获取某个log_dir的更新
    _uuid = request.json['chart_uuid']

    # TODO 使用更好的办法解决一下。
    max_point_per_update = 100  # 一次更新只能选取最新的这么多个数据，否则网络传输和前端显示会有问题
    points = {}
    if _uuid in all_handlers:
        handler = all_handlers[_uuid]
        points = handler.update_logs()
        for key, value in points.items():
            if isinstance(value, list):
                if len(value)<max_point_per_update:
                    continue
                # 只选择max_point_per_update个更新
                total_points = len(value)
                cut_values = [v for v in value if random.random()<max_point_per_update/total_points]
                points[key] = cut_values
    else:
        points['finish'] = True

    replace_nan_inf(points)  # points内部是{'loss':[{}, {}, {}],
    #                                       'metric':[{}, {}]}

    return jsonify(steps=points)

@chart_page.route('/chart/have_trends', methods=['POST'])
def have_trends():
    try:
        res = check_uuid(all_data['uuid'], request.json['uuid'])
        if res != None:
            return jsonify(res)
        log_dir = request.json['log_dir']
        save_log_dir = os.path.join(all_data['root_log_dir'], log_dir)
        if is_log_dir_has_step(save_log_dir):
            return jsonify(status='success', have_trends=True)
        else:
            return jsonify(status='success', have_trends=False, msg='There is no trend data for this log.')
    except Exception:
        print("Exception detected in have_trends()")
        return jsonify(status='fail', have_trends=False, msg='Error from the server.')

@chart_page.route('/chart/range', methods=['POST'])
def ranges():
    try:
        res = check_uuid(all_data['uuid'], request.json['uuid'])
        if res != None:
            return jsonify(res)
        keys = request.json['keys']
        log_dir = request.json['log_dir']
        ranges = request.json['ranges']
        handler = ChartStepLogHandler(save_log_dir=os.path.join(all_data['root_log_dir'], log_dir),
                                      uuid=all_data['uuid'], round_to=all_data['basic_settings']['round_to'],
                                      max_steps=100000,
                                      wait_seconds=10,
                                      exclude_columns=all_data['chart_settings']['chart_exclude_columns'],
                                      max_no_updates=all_data['chart_settings']['max_no_updates'])
        filepaths = []
        for key in keys:
            filepaths.append(os.path.join(all_data['root_log_dir'], log_dir, key+'.log'))
        updates = handler.read_single_update(filepaths, ranges)
        del handler

        refined_updates = {}
        for key in keys:
            logs = updates[key]
            refined_updates[key] = _refine_logs(logs, all_data['chart_settings']['max_points'],
                                                all_data['basic_settings']['round_to'])
        return jsonify(status='success', steps=refined_updates)

    except Exception as e:
        print(e)
        return jsonify(status='fail', msg='Some bug happens, contact developer.')




