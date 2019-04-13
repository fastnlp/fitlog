from fitlog.fastlog.writer import FileWriter, Event
from fitlog.fastlog.logger import Logger
from fitlog.fastlog.reader import LogReader
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

def rm_dir(dir_name):
    if not os.path.exists(dir_name):
        return
    for root, dn, fn in os.walk(dir_name, topdown=False):
        for d in dn:
            os.rmdir(os.path.join(root, d))
        for f in fn:
            os.remove(os.path.join(root, f))
    os.rmdir(dir_name)

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
    def write1(self):
        w = Logger(self.fn)
        w.add_rng_seed(val=12345)

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
        # test log writing
        self.write1()
        assert len(os.listdir(self.fn)) == 1
        self.write1()
        self.write1()
        assert len(os.listdir(self.fn)) == 3

    def test2(self):
        # test log reading
        N = 3
        for _ in range(N):
            self.write1()
        r = LogReader(self.fn)
        assert len(list(r.read_metas())) == N
        assert len(list(r.read_configs())) == N
        assert len(list(r.read_losses())) == N
        assert len(list(r.read_metrics())) == N
        assert len(list(r.read_scalars())) == N
        # print('\nmetas')
        # for i in r.read_metas():
        #     print(i)
        # print('\nconfigs')
        # for i in r.read_configs():
        #     print(i)
        # print('\nlosses')
        # for i in r.read_losses():
        #     print(i)
        # print('\nmetrics')
        # for i in r.read_metrics():
        #     print(i)
        # print('\nscalars')
        # for i in r.read_scalars():
        #     print(i)

    def teardown(self):
        rm_dir(self.fn)

    def setup(self):
        rm_dir(self.fn)
