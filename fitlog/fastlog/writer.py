import json
import threading
import queue


class Event():
    def __init__(self, name=None, val=None, time=None, step=None):
        self.name = name
        self.val = val
        self.time = time
        self.step = step

    @property
    def time(self):
        return self._time
    @time.setter
    def time(self, t):
        if t is None:
            self._time = None
        elif isinstance(t, (int, float)):
            self._time = int(t)
        else:
            raise TypeError('time must be int or float or None')
    @property
    def step(self):
        return self._step
    @step.setter
    def step(self, s):
        if s is None:
            self._step = None
        elif isinstance(s, int):
            self._step = s
        else:
            raise TypeError('step must be int or None')

    def to_json(self):
        data = {
            'name':self.name,
            'val':self.val,
        }
        if self.time is not None:
            data['time'] = self.time
        if self.step is not None:
            data['step'] = self.step
        return json.dumps(data)

class FileWriter():
    def __init__(self, fn:str):
        self._fn = fn
        self._q = queue.Queue(maxsize=100)
        self._thread = FileWriterThread(self._fn, self._q)
        self._thread.daemon = True
        self._thread.start()

    def add_event(self, e:Event):
        self._q.put(e.to_json(), timeout=60)

    def add_str(self, s:str):
        self._q.put(s, timeout=60)

    def close(self):
        self._q.put(None, timeout=60)
        self._thread.join(timeout=60)


class FileWriterThread(threading.Thread):
    def __init__(self, fn, q:queue.Queue):
        super(FileWriterThread, self).__init__()
        self._fn = fn
        self._q = q
        self._fp = None

    def run(self):
        self._fp = open(self._fn, 'w', encoding='utf-8')
        try:
            while 1:
                msg = self._q.get()
                if msg is None:
                    break
                self._fp.write(msg+'\n')
        finally:
            self._fp.close()
