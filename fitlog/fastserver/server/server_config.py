

# TODO可以修改为使用fastgit/normal下的内容，这样不用维持两份
default_cfg = """
[frontend_settings]
# 以下的几个设置主要是用于控制前端的显示
Ignore_null_value_when_filter=True
Wrap_display=True
Pagination=True
Hide_hidden_columns_when_reorder=False
# 前端的任何变动都不会尝试更新到服务器，即所有改动不会保存
Offline=False
# 是否保存本次前端页面的改动，以使得下次打开是与本次一致的页面
Save_settings=True
# row是否是可以通过拖拽交换的，如果可以交换则无法进行复制
Reorderable_rows=False
# 当选择revert代码时 revert到的路径: ../<pj_name>-revert 或 ../<pj_name>-revert-<fit_id>
No_suffix_when_reset=True
# 是否忽略掉filter_condition中的不存在对应key的log
Ignore_filter_condition_not_exist_log=True

[basic_settings]
# 如果有内容长度超过这个值，在前端就会被用...替代。
str_max_length=20
# float的值保留几位小数
round_to=6
# 是否在表格中忽略不改变的column
ignore_unchanged_columns=True

[data_settings]
# 在这里的log将不在前端显示出来，但是可以通过display点击出来。建议通过前端选择
hidden_logs=
# 在这里的log将在前端删除。建议通过前端选择
deleted_logs=
# 可以设置条件，只有满足以下条件的field才会被显示，请通过前端增加filter条件。
filter_condition=

[column_settings]
# 隐藏的column，建议通过前端选择
hidden_columns=
# 不需要显示的column，用逗号隔开，不要使用引号。需要将其从父节点一直写到它本身，比如排除meta中的fit_id, 写为meta-fit_id
exclude_columns=
# 允许编辑的column
editable_columns=memo,meta-fig_msg,meta-git_msg
# column的显示顺序，强烈推荐不要手动更改
column_order=

[chart_settings]
# 在走势图中，每个对象最多显示的点的数量，不要太大，否则前端可能会卡住
max_points=200
# 不需要在走势图中显示的column名称
chart_exclude_columns=
# 前端间隔秒多久尝试更新一次走势图，不要设置为太小。
update_every=4
# 如果前端超过max_no_updates次更新都没有获取到更新的数据，就停止刷新。如果evaluation的时间特别长，可能需要调大这个选项。
max_no_updates=40
"""

from .log_config_parser import ConfigParser
import os
import json
import glob

def read_server_config(config_path):
    """
    给定config的path，读取里面的config。如果config不存在，则按照默认的值创建
    :param config_path: str
    :return: dict, config的内容
    """
    config = ConfigParser(allow_no_value=True)
    if not os.path.exists(config_path):
        config_dir = os.path.dirname(config_path)
        if not os.path.isdir(config_dir):
            os.makedirs(config_dir)
        os.mknod(config_path)  # 不存在就创建空文件
        config.read_string(default_cfg)
        with open(config_path, 'w') as f:
            config.write(f)
    else:
        config.read(config_path)
        # check configparser, 必须拥有一样的section
        check_config(config)

    all_data = {}
    # 读取settings
    settings = {}
    get_dict_from_config(config, 'frontend_settings', settings, 'bool')
    settings = {key.capitalize():value for key, value in settings.items()}
    all_data['settings'] = settings

    # 读取display_settings
    basic_settings = {}
    get_dict_from_config(config, 'basic_settings', basic_settings)
    for key in ['str_max_length', 'round_to']:
        basic_settings[key] = int(basic_settings[key])
    for key in ['ignore_unchanged_columns']:
        basic_settings[key] = basic_settings[key]=='True'
    all_data['basic_settings'] = basic_settings


    # 读取data_settings
    hidden_logs = read_list_from_config(config, 'data_settings', 'hidden_logs', ',')
    all_data['hidden_rows'] = {log:1 for log in hidden_logs}
    deleted_rows = read_list_from_config(config, 'data_settings', 'deleted_logs', ',')
    all_data['deleted_rows'] = {log: 1 for log in deleted_rows}
    if len(config.get('data_settings', 'filter_condition'))!=0:
        all_data['filter_condition'] = json.loads(config.get('data_settings', 'filter_condition'))
    else:
        all_data['filter_condition'] = {}

    # 读取column_settings
    hidden_columns = read_list_from_config(config, 'column_settings', 'hidden_columns', ',')
    all_data['hidden_columns'] = {column:1 for column in hidden_columns}

    # 读取exclude columns
    exclude_columns = read_list_from_config(config, 'column_settings', 'exclude_columns', ',')
    all_data['exclude_columns'] = {column:1 for column in exclude_columns}

    # 读取editable_columns
    editable_columns = read_list_from_config(config, 'column_settings', 'editable_columns', ',')
    all_data['editable_columns'] = {column:1 for column in editable_columns}

    # 读取column_order
    column_order = config.get('column_settings', 'column_order')
    if column_order!='':
        column_order = json.loads(column_order)
    else:
        column_order = {}
    all_data['column_order'] = column_order

    # 保存config对象, 因为需要保留下注释
    all_data['config'] = config

    _dict = {}
    chart_exclude_columns = read_list_from_config(config, 'chart_settings', 'chart_exclude_columns', ',')
    _dict['chart_exclude_columns'] = {column:1 for column in chart_exclude_columns}
    _dict['max_points'] = config.getint('chart_settings', 'max_points')
    _dict['update_every'] = config.getint('chart_settings', 'update_every')
    _dict['max_no_updates'] = config.getint('chart_settings', 'max_no_updates')
    all_data['chart_settings'] = _dict

    return all_data

def save_config(all_data, config_path):
    config = all_data['config']
    if not os.path.exists(config_path):
        config_dir = os.path.dirname(config_path)
        if not os.path.isdir(config_dir):
            os.makedirs(config_dir)
        os.mknod(config_path)  # 不存在就创建空文件

    # frontend_settings
    settings = all_data['settings']
    settings = {key.replace(' ', '_'):value for key, value in settings.items()}
    save_dict_to_config(config, 'frontend_settings', settings)

    # basic_settings
    basic_settings = all_data['basic_settings']
    save_dict_to_config(config, 'basic_settings', basic_settings)

    # data settings
    hidden_logs = all_data['hidden_rows'].keys()
    config.set('data_settings', 'hidden_logs', ','.join(hidden_logs))
    deleted_logs = all_data['deleted_rows'].keys()
    config.set('data_settings', 'deleted_logs', ','.join(deleted_logs))
    if len(all_data['filter_condition'])!=0:
        filter_condition = json.dumps(all_data['filter_condition'])
    else:
        filter_condition = ''
    config.set('data_settings', 'filter_condition', filter_condition)

    # column_settings
    for option in ['hidden_columns', 'editable_columns']:
        save_list_to_config(config, 'column_settings', option, all_data[option])
    column_order = refine_column_order(all_data['column_order'])
    column_order = json.dumps(column_order)
    config.set('column_settings', 'column_order', column_order)

    with open(config_path, 'w', encoding='utf-8') as f:
        config.write(f)

def refine_column_order(column_order):
    # 重新生成column_order
    new_column_order = {}
    if 'OrderKeys' in column_order: # 还有下一级
        keys = column_order['OrderKeys']
        for key in keys:
            value = column_order[key]
            child = refine_column_order(value)
            if len(child)==0:
                new_column_order[key] = 'EndOfOrder'
            else:
                new_column_order[key] = child
    return new_column_order


def save_list_to_config(config, section, option, container, sep=','):
    if not config.has_section(section):
        config.add_section(section)
    if len(container)==0:
        str_ = ''
    else:
        str_ = sep.join(container.keys())
    config.set(section, option, str_)


def save_dict_to_config(config, section, container):
    if not config.has_section(section):
        config.add_section(section)
    for key, value in container.items():
        config.set(section, key, str(value))


def read_list_from_config(config, section, option, sep):
    str_ = config.get(section, option)
    items = []
    if str_!='':
        items = str_.split(sep)
        items = [item.strip() for item in items]
    return items

def check_config(config):
    # 检查config是否拥有所有的值，如果没有的话，使用默认值填写
    default_config = ConfigParser()
    default_config.read_string(default_cfg)
    for section in default_config.sections():
        if not config.has_section(section):
            # raise KeyError("Section:`{}` is not in config.".format(section))
            config.add_section(section)
            for option, value in default_config.items(section):
                config.set(section, option, value)
        for opt in default_config.options(section):
            if not config.has_option(section, opt):
                # raise KeyError("Option:`{}` is not in Section:`{}` is not in config.".format(opt, section))
                config.set(section, opt, default_config.get(section, opt))

def get_dict_from_config(config, section, container, dtype=None):
    if dtype == 'int':
        func = config.getint
    elif dtype == 'bool' or dtype=='boolean':
        func = config.getboolean
    else:
        func = config.get
    for option in config.options(section):
        container[option] = func(section, option)

def read_extra_data(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def save_extra_data(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f)


def _get_config_names(root_log_dir):
    """
    给定log的路径, 返回下面所有结尾为.cfg的文件

    :param str, root_log_dir:
    :return: list(dir)
    """
    configs = glob.glob(os.path.join(root_log_dir, '*.cfg'))
    configs = [os.path.basename(config) for config in configs]
    return configs


