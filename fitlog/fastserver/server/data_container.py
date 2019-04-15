

import threading
import time
import os

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
                        log_dir = self.all_handlers.pop(_uuid)._save_log_dir
                        del handler
                        print("Delete reader for {}:{}.".format(os.path.basename(log_dir), _uuid))
            time.sleep(0.5)
        # 删除所有的handler
        for _uuid in list(self.all_handlers.keys()):
            handler = self.all_handlers[_uuid]
            if handler.reader._quit:
                handler.reader.stop()
                del handler

        self._quit = True
    def stop(self):
        self._stop_flag = True
        count = 0
        while not self._quit:
            time.sleep(0.6)
            if count>2:
                raise RuntimeError("Some bug happens.")
            count += 1
# singleton
all_data = {}
all_handlers = {}
handler_watcher = HandlerWatcher()