import json
import os
from contextlib import contextmanager


@contextmanager
def open_reader(log_dir):
    reader = LogReader(log_dir=log_dir)
    yield reader
    reader.close()


class LogReader():
    def __init__(self, log_dir='.'):
        self.log_dir = log_dir
        self._meta_path = os.path.join(log_dir,'meta.log')
        self._event_path = os.path.join(log_dir,'event.log')
        self._event_fp = open(self._event_path, 'r', encoding='utf-8')


    def read_metas(self):
        def ismeta(x):
            if 'name' in x and 'val' in x:
                n = x['name']
                return n[0] == '$' and n[-1] == '$'
            return False

        with open(self._meta_path, 'r', encoding='utf-8') as f:
            lines = filter(ismeta, (json.loads(l) for l in f))
            res = {l['name'][1:-1]: l['val'] for l in lines}
        return res

    def read_hypers(self):
        def ishyper(x):
            if 'name' in x and 'val' in x:
                n = x['name']
                return n[0] != '$' and n[-1] != '$'
            return False

        with open(self._meta_path, 'r', encoding='utf-8') as f:
            lines = filter(ishyper, (json.loads(l) for l in f))
            res = {l['name']: l['val'] for l in lines}
        return res

    def read_event(self):
        l = self._event_fp.readline()
        if not l:
            return None
        return json.loads(l)

    def read_events(self):
        return list(self.read_events_iter())

    def read_events_iter(self):
        while 1:
            e = self.read_event()
            if e is None:
                break
            yield e

    def close(self):
        self._event_fp.close()
        self._event_fp = None
