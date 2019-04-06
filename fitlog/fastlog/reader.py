import json
import os
from contextlib import contextmanager


@contextmanager
def open_reader(log_dir):
    reader = LogReader(log_dir=log_dir)
    yield reader
    reader.close()


class LogObjReader():
    def __init__(self, log_dir='.'):
        self.log_dir = log_dir
        self._meta_path = os.path.join(log_dir,'meta.log')
        self._loss_fp = open(os.path.join(log_dir,'loss.log'), 'r', encoding='utf-8')
        self._metric_fp = open(os.path.join(log_dir,'metric.log'), 'r', encoding='utf-8')
        self._scalar_fp = open(os.path.join(log_dir,'scalar.log'), 'r', encoding='utf-8')

    def read_metas(self):
        def ismeta(x):
            if 'name' in x and 'val' in x:
                n = x['name']
                return n[0] == '$' and n[-1] == '$'
            return False

        with open(self._meta_path, 'r', encoding='utf-8') as f:
            lines = filter(ismeta, (json.loads(l) for l in f))
            res = {}
            rngs = {}
            c_rng = 'rng-seed'
            for l in lines:
                n, v = l['name'][1:-1], l['val']
                if n.startswith(c_rng):
                    n = n[len(c_rng)+1:]
                    rngs[n] = v
                else:
                    res[n] = v
            res['rng-seed'] = rngs
        return res

    def read_configs(self):
        def ishyper(x):
            if 'name' in x and 'val' in x:
                n = x['name']
                return n[0] != '$' and n[-1] != '$'
            return False

        with open(self._meta_path, 'r', encoding='utf-8') as f:
            lines = filter(ishyper, (json.loads(l) for l in f))
            res = {l['name']: l['val'] for l in lines}
        return res

    @staticmethod
    def read_event(fp):
        l = fp.readline()
        if not l:
            return None
        return json.loads(l)

    @staticmethod
    def read_events(fp):
        while 1:
            e = LogObjReader.read_event(fp)
            if e is None:
                break
            yield e

    def read_losses(self):
        return self.read_events(self._loss_fp)

    def read_metrics(self):
        return self.read_events(self._metric_fp)

    def read_scalars(self):
        return self.read_events(self._scalar_fp)

    def close(self):
        self._loss_fp.close()
        self._metric_fp.close()
        self._scalar_fp.close()


class LogReader():
    # TODO support metric dict, e.g. (f1, pre, rec)

    def __init__(self, log_dir):
        self.log_dir = log_dir
        self._logs = os.listdir(log_dir)
        log_paths = [os.path.join(log_dir, dn) for dn in self.logs]
        self._readers = [LogObjReader(log_dir=dn) for dn in log_paths]

    @property
    def logs(self):
        return self._logs

    @property
    def readers(self):
        return self._readers

    def close(self):
        for r in self._readers:
            r.close()

    def read_metas(self):
        for r in self._readers:
            yield r.read_metas()

    def read_configs(self):
        for r in self._readers:
            yield r.read_configs()

    @staticmethod
    def get_minmax(events):
        res_min, res_max = {}, {}
        for e in events:
            n = e['name']
            if n not in res_min:
                res_min[n] = e
                res_max[n] = e
                continue
            if e['val'] > res_max[n]['val']:
                res_max[n] = e
            if e['val'] < res_min[n]['val']:
                res_min[n] = e
        return res_min, res_max

    def read_losses(self):
        for r in self._readers:
            val, _ = self.get_minmax(r.read_losses())
            yield val

    def read_metrics(self):
        for r in self._readers:
            min_v, max_v = self.get_minmax(r.read_metrics())
            yield min_v, max_v

    def read_scalars(self):
        for r in self._readers:
            min_v, max_v = self.get_minmax(r.read_scalars())
            yield min_v, max_v
