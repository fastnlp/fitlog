
from collections import defaultdict
from numbers import Number
from ...fastgit.committer import _colored_string

def flatten_dict(prefix, _dict, connector='-'):
    """
    给定一个dict, 将其展平，比如{"a":{"v": 1}} -> {"a-v":1}

    :param prefix:
    :param _dict:
    :param connector:
    :return:
    """
    new_dict = {}
    for key, value in _dict.items():
        if prefix != '':
            new_prefix = prefix + connector + str(key)
        else:
            new_prefix = str(key)
        if isinstance(value, dict):
            new_dict.update(flatten_dict(new_prefix, value, connector))
        else:
            new_dict[new_prefix] = value
    return new_dict

def stringify_dict_key(_dict):
    """
    保证_dict中所有key为str类型
    :param _dict:
    :return:
    """
    for key, value in _dict.copy().items():
        if isinstance(value, dict):
            value = stringify_dict_key(value)
        if not isinstance(key, str):
            del _dict[key]
            _dict[str(key)] = value
    return _dict

def replace_nan_inf(data):
    # data: List[dict]
    if isinstance(data, list):
        for d in data:
            _replace_nan_inf(d)
    elif isinstance(data, dict):
        _replace_nan_inf(data)
    else:
        raise TypeError("Unsupported type.")
    return data

def _replace_nan_inf(d):
    for k, value in d.items():
        if isinstance(value, dict):
            _replace_nan_inf(value)
        elif isinstance(value, list):
            for d in value:
                _replace_nan_inf(d)
        elif value==float('inf'):
            d[k] = "Infinity"
        elif value==float('-inf'):
            d[k] = "-Infinity"
        elif str(value)=='nan':
            d[k] = "NaN"

def check_uuid(gold_uuid, _uuid):
    if gold_uuid==_uuid:
        return None
    else:
        return {'status': 'fail',
                'msg': "The data are out-of-date, please refresh this page. Or, you can set this page as Offline to "
                       "stop sending updates to the server."}

class LogFilter:
    """

    """
    def __init__(self, filter_condition):
        self.filter_condition = filter_condition
        self._parse()

    def _filter_this_log_or_not(self, flat_log, ignore_not_exist):
        _filter = False
        for field_name, field_filters in self.filters.items():
            if field_name in flat_log:
                value = flat_log[field_name]
                _field_filter_flag = True # 默认删除
                for field_filter in field_filters:  # [[[operator, con], [operator, con]], [[]]], or的关系
                    _filter_flag = True  # 默认都满足
                    for field in field_filter: # and关系, 全部为满足才行
                        con, operator = field
                        if isinstance(value, bool):
                            if con.lower() == 'false':
                                con = False
                            else:
                                con = True
                        else:
                            con = type(value)(con)
                        con_expr = 'con' + operator + 'value'
                        __filter = False
                        try:
                            __filter = eval(con_expr)  # 满足条件说明为True
                        except Exception as e:
                            print(_colored_string(repr(e), 'red'))
                        _filter_flag = _filter_flag and __filter
                    _field_filter_flag = (not _filter_flag) and _field_filter_flag # 任何一个不删除就不删除了
                if _field_filter_flag and self.and_filters: # 一个不满足且是and关系
                    return True  # 删除掉
                elif not _field_filter_flag and not self.and_filters: # 一个满足且是or关系
                    return False
            elif ignore_not_exist:
                if self.and_filters:  # 因为是and的关系，所以只要一个条件不包含，则过滤掉
                    return True
            else:
                if not self.and_filters: # 因为是or的关系，只要有一个条件不存在，则包含进来
                    return False
        return _filter

    def _parse(self):
        # 将filter_condition分出and_conditions, or_conditions. 必须要满足所有and_conditions或满足一个or_conditions就放过
        if 'and_filters' in self.filter_condition:
            self.and_filters = bool(self.filter_condition['and_filters'])
        else:
            self.and_filters = True
        self.filters = defaultdict(list) # key是field_name, [[[con, operator], []], [], []], 不同list间为or关系，同一个list为and关系
        for field_name, conditions in self.filter_condition.items():
            if field_name=='and_filters':
                continue
            field_filters = []
            if isinstance(conditions, list):
                for condition in conditions:
                    field_filter = []
                    if isinstance(condition, Number):
                        field_filter.append([condition, '=='])
                    else:
                        if '&&' in condition:  # 如果使用了and符号
                            exprs = condition.split('&&')
                        else:
                            exprs = [condition]
                        for expr in exprs:
                            res = self._parse_condition(expr, field_name)
                            if res != None:
                                field_filter.append(res)
                    field_filters.append(field_filter)
            elif isinstance(conditions, Number):
                field_filters.append([[conditions, '==']])
            else:
                field_filter = []
                if '&&' in conditions:  # 如果使用了and符号
                    exprs = conditions.split('&&')
                else:
                    exprs = [conditions]
                for expr in exprs:
                    res = self._parse_condition(expr, field_name)
                    if res != None:
                        field_filter.append(res)
                field_filters.append(field_filter)
            self.filters[field_name] = field_filters

    def _parse_condition(self, expr, condition_key):
        # 给定一个expr计算它的表达式
        if isinstance(expr, str):
            expr = expr.strip()  # 删去空格
            if '<' in expr:
                index = expr.index('<')
                if 0<index<len(expr)-1:
                    print(_colored_string(f"Corrupted filter_condition in `{condition_key}`, '<' can only be in the beginning"
                                            "or in the end", 'red'))
                    return None
                else:
                    if index == 0:
                        con = expr[1:]
                        operator = '>'
                    else:
                        con = expr[:-1]
                        operator = '<'
            elif '>' in expr:
                index = expr.index('>')
                if 0<index<len(expr)-1:
                    print(_colored_string(f"Corrupted filter_condition in `{condition_key}`, '>' can only be in the beginning"
                                            " or in the end", 'red'))
                    return None
                else:
                    if index == 0:
                        con = expr[1:]
                        operator = '<'
                    else:
                        con = expr[:-1]
                        operator = '>'
            elif '!=' in expr:
                index = expr.index('!=')
                if 0<index<len(expr)-2:
                    print(_colored_string(f"Corrupted filter_condition in `{condition_key}`, '!=' can only be in the beginning"
                                            " or in the end", 'red'))
                    return None
                else:
                    if index==0:
                        con = expr[2:]
                    else:
                        con = expr[:-2]
                    operator = '!='
            elif '=' in expr:
                index = expr.index('=')
                if 0<index<len(expr)-1:
                    print(_colored_string(f"Corrupted filter_condition in `{condition_key}`, '=' can only be in the beginning"
                                            "or in the end", 'red'))
                    return None
                else:
                    if index == 0:
                        con = expr[1:]
                    else:
                        con = expr[:-1]
                    operator = '=='
            else:
                con = expr
                operator = ' in '
        elif isinstance(expr, Number):
            con = expr
            operator = '=='
        else:
            return None
        return [con, operator]

    def __str__(self):
        return str(self.filter_condition)

    def __repr__(self):
        return self.filter_condition.__repr__()