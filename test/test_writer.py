from src.fastlog.writer import FileWriter, Event
from fastlog import Logger
from fastlog import LogReader
import os
import json

events = [
    Event(step=1, time=None, name='loss', val=10.2),
    Event(step=2, time=12, name='loss', val=20.5),
    Event(step=3, time=None, name='loss', val=13.2),
    Event(step=4, time=13, name='loss', val=4.2),
    Event(step=5, time=20, name=None, val=50.2),
    Event(step=6, time=100, name='loss', val=6.2),
    Event(step=7, time=101, name='loss', val=None),
    Event(step=8, time=102, name='loss', val=8.2),
]


class TestWriter():
    fn = 'test_writer.log'
    def test1(self):
        w = FileWriter(self.fn)
        try:
            w.add_str('='*10)
            for e in events:
                w.add_event(e)
            w.add_str('='*10)
        finally:
            w.close()

        with open(self.fn, 'r', encoding='utf-8') as f:
            true_lines = ['='*10] + [e.to_json() for e in events] + ['='*10]
            test_lines = f.readlines()
            for l1, l2 in zip(true_lines, test_lines):
                assert l1 + '\n' == l2

    def teardown(self):
        os.remove(self.fn)


class TestLogger():
    fn = 'test_logger'
    meta_fn = fn + '/meta.log'
    event_fn = fn + '/event.log'
    def write1(self):
        w = Logger(self.fn)

        cfg = {'lr': 3e-4,
               'hidden': 400,
               'weight_decay': 1e-5,
               'lr_decay': 0.95, }
        w.add_config(cfg)

        w.add_scalar('c1', 1, step=1)
        w.add_scalar('v2', 2.2, step=2)
        w.add_scalar('v3', 0.3, step=3)
        w.add_loss('corss_loss', 10.3, step=4)
        w.add_metric('f1', 2.3, step=5)
        w.add_metric('acc', 4.3, step=6)
        w.close()

    def test1(self):
        self.write1()
        with open(self.event_fn, 'r') as f:
            text = ''.join(f.readlines())
        true_text = """{"name": "c1", "val": 1, "time": 0, "step": 1}
{"name": "v2", "val": 2.2, "time": 0, "step": 2}
{"name": "v3", "val": 0.3, "time": 0, "step": 3}
{"name": "loss", "val": {"corss_loss": 10.3}, "time": 0, "step": 4}
{"name": "metric", "val": {"f1": 2.3}, "time": 0, "step": 5}
{"name": "metric", "val": {"acc": 4.3}, "time": 0, "step": 6}
"""
        assert text == true_text
        meta_log = {}
        with open(self.meta_fn, 'r') as f:
            for l in f:
                log = json.loads(l)
                assert 'name' in log
                assert 'val' in log
                meta_log[log['name']] = log['val']
        meta_true = {
            '$commit-id$': None,
            '$rng-seed$': None,
            '$start-time$': None,
            'lr': 0.0003,
            'hidden': 400,
            'weight_decay': 1e-05,
            'lr_decay': 0.95,
        }
        assert len(meta_log) == len(meta_true)
        for n, v in meta_true.items():
            assert n in meta_log
            if v is not None:
                assert v == meta_log[n]

    def test2(self):
        self.write1()
        r = LogReader(self.fn)
        meta = r.read_metas()
        hyper = r.read_hypers()
        events = r.read_events()
        print(meta)
        print(hyper)
        print(events[0:2])
        assert 'commit-id' in meta \
                and 'rng-seed' in meta \
                and 'start-time' in meta
        cfg = {'lr': 3e-4,
               'hidden': 400,
               'weight_decay': 1e-5,
               'lr_decay': 0.95, }
        assert cfg == hyper
        assert len(events) == 6

    def teardown(self):
        os.remove(self.event_fn)
        os.remove(self.meta_fn)
        os.rmdir(self.fn)
