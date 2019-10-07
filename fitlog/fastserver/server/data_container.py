

import threading
import time

class HandlerWatcher(threading.Thread):
    def __init__(self):
        super().__init__()
        self.all_handlers = all_handlers
        self._stop_flag = False
        self._quit = True
        self._start = False

    def run(self):
        self._quit = False
        self._start = True
        while not self._stop_flag:
            if len(self.all_handlers)>0:
                for _uuid in list(self.all_handlers.keys()):
                    handler = self.all_handlers[_uuid]
                    if handler.reader._quit:
                        handler.reader.stop()
                        handler = self.all_handlers.pop(_uuid)
                        del handler
            time.sleep(0.5)
        # 删除所有的handler
        for _uuid in list(self.all_handlers.keys()):
            handler = self.all_handlers.pop(_uuid)
            if handler.reader._quit:
                handler.reader.stop()
                del handler

        self._quit = True
    def stop(self):
        self._stop_flag = True
        count = 0
        while not self._quit:
            time.sleep(0.6)
            if count>3:
                raise RuntimeError("Some bug happens.")
            count += 1
# singleton
"""
all_data包含以下的key:
    settings: {} 一级dict，包含了所有的frontend_settings中的内容，value全部是bool值
    basic_settings: {} 一级dict包含了config中basic_settings中的setting.
    hidden_rows: {} 一级dict key为隐藏的row的id
    deleted_rows: {} 一级dict key为删除的row的id
    filter_condition: {} 一级dict，expanded的key以及它等于的value. value可以为str或者list[str], list[str]表示满足任意条件
        即可
    hidden_columns: {} 一级dict key为隐藏的column. 展平后的值
    exclude_columns: {} 一级dict，需要排除的column
    editable_columns: {} 一级dict，支持编辑的column名
    column_order: {} nested dict. 表示column的顺序的. 类似于{"meta":{"fit_id": xxx, ...}, "metric": {...}, "OrderKeys:["meta", "metric"]"}
    field_columns: {}, 一级dict，key是expanded后的且会显示在前端table的名称，比如hyper-lr, id
    column_dict: {}, 二级dict，第一级是展开的key, 比如hyper-lr; 第二级是{'title':, 'field':}等用于生成前端header的内容。
    chart_settings: {} 保存chart相关的设置，包含以下的内容
        chart_exclude_columns:{} 一级dict，需要排除的column名称
        max_points:int 前端每条线最多显示多少个点
        update_every: int, 隔多少秒update一次
        max_no_updates: int 多少次没有得到更新就认为已经停止了
    config: 读取的ConfigParser对象
    extra_data: {}, 第一层的key为前端增加的记录获取用户修改某条记录留下的修改记录; 第一层的value对应的是一个一级dict。
    root_log_dir: str, log文件夹的路径
    log_config_name: str, 
    log_reader: LogReader()对象
    port: int, port
    uuid: str, 这个server的uuid
    token: str,None 这个server的token，放访问路径上的
    data: {id1:{'id':id1, 'field1':xxx,}, id2:{}}, 所有的数据都在这个里面，这是一个一级dict. extra_data已经替换了里面的值
"""
all_data = {}
all_handlers = {}
handler_watcher = HandlerWatcher()