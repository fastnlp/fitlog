


default_cfg = """
[frontend_settings]
# control some setting in the frontend page.
Ignore_null_value_when_filter=True
Wrap_display=True
Pagination=True
Hide_hidden_columns_when_reorder=False
# Will not try to upload your changes to the server
Offline=False
# whether save your changes
Save_settings=True
# Whether the rows are reorderable, when they are reorderable, they cannot be selected or copied
Reorderable_rows=False
# Where should fitlog revert codes to: ../<pj_name>-revert or ../<pj_name>-revert-<fit_id>
No_suffix_when_reset=True

[basic_settings]
# any data longer than this value will be partly replaced by '...'
str_max_length=20
# precision, the number of digits to keep
round_to=6
# Whether to ignore columns never changed
ignore_unchanged_columns=True

[data_settings]
# log dirs in this list are not displayed. Use ',' to separate columns
hidden_logs=
# log dirs in this list are ignore.
deleted_logs=

[column_settings]
# columns are not displayed, but can be chosen to display. Use ',' to separate columns
hidden_columns=
# columns are ignored, use ',' to separate columns
exclude_columns=
# editable columns, you have to be specific to the root
editable_columns=memo,meta-fig_msg,meta-git_msg
# recommend not to modify by hand, use the front page to change this
column_order=

[chart_settings]
# The maximum points one line can hold.
max_points=500
# columns are not displayed in the chart, not share with the one in the column_settings
chart_exclude_columns=
# the interval between update in the front page. in seconds. Don't set it too small.
update_every=3
# if that much no updates is detected, fitlog chart will regard this is a finished trend
max_no_updates=40
"""

from .log_config_parser import ConfigParser
import os
import json

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
    default_config = ConfigParser()
    default_config.read_string(default_cfg)
    for section in default_config.sections():
        if not config.has_section(section):
            raise KeyError("Section:`{}` is not in config.".format(section))
        for opt in default_config.options(section):
            if not config.has_option(section, opt):
                raise KeyError("Option:`{}` is not in Section:`{}` is not in config.".format(opt, section))


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


if __name__=='__main__':
    # config = configparser.ConfigParser(allow_no_value=True)
    # config.read_string(default_cfg)
    # print(config['display_settings'].getboolean('Ignore_null_value_when_filter'))
    os.mknod('../test/test.txt')


