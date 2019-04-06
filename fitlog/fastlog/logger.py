from fitlog.fastlog.writer import FileWriter, Event
import os
from os import path
import datetime
import time as T
import random, numpy, torch
import argparse
import string
from fitlog import fastgit

#
# def set_rng_seeds(seed=None):
#     if seed is None:
#         seed = numpy.random.randint(0, 0x80000000)
#     else:
#         seed = int(seed)
#     random.seed(seed)
#     numpy.random.seed(seed)
#     torch.random.manual_seed(seed)
#     torch.cuda.manual_seed_all(seed)
#     # print('RNG_SEED {}'.format(seed))
#     return seed

class Logger():
    def __init__(self, log_dir='log_dir', code_dir='.'):
        self._start_time = None
        self._commit_id = None
        self._step_dict = {}

        self._code_dir = os.path.abspath(code_dir)
        self._root_dir = self._get_dirname(log_dir)
        self._loss_writer = FileWriter(fn=path.join(self._root_dir, 'loss.log'))
        self._metric_writer = FileWriter(fn=path.join(self._root_dir, 'metric.log'))
        self._scalar_writer = FileWriter(fn=path.join(self._root_dir, 'scalar.log'))
        self._meta_writer = FileWriter(fn=path.join(self._root_dir, 'meta.log'))

        self._log_all_meta()

    @staticmethod
    def _get_dirname(log_dir):
        length = 20
        os.makedirs(log_dir, exist_ok=True)
        dirs = set(os.listdir(log_dir))
        while 1:
            dn = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
            if dn not in dirs:
                break
        dn = os.path.join(log_dir, dn)
        os.makedirs(dn)
        return dn

    def _write_event(self, writer, name, value, step):
        if step is None:
            step = self.get_step(name)
        e = Event(time=self.delta_time(), step=step, name=name, val=value)
        writer.add_event(e)

    def add_scalar(self, name, value, step=None):
        self._write_event(self._scalar_writer, name, value, step)

    def add_loss(self, name, value, step=None):
        self._write_event(self._loss_writer, name, value, step)

    def add_metric(self, name, value, step=None):
        self._write_event(self._metric_writer, name, value, step)

    def add_scalars(self, step=None, **scalars):
        for name, val in scalars.items():
            self.add_scalar(name=name, value=val, step=step)

    def add_losses(self, step=None, **losses):
        for name, val in losses.items():
            self.add_loss(name=name, value=val, step=step)

    def add_metrics(self, step=None, **metrics):
        for name, val in metrics.items():
            self.add_metric(name=name, value=val, step=step)

    def add_config(self, cfg_dict):
        # support for args from command-line
        if isinstance(cfg_dict, argparse.Namespace):
            cfg_dict = cfg_dict.__dict__
        elif not isinstance(cfg_dict, dict):
            raise TypeError('cannot support config type: {}'.format(type(cfg_dict)))
        for name, val in cfg_dict.items():
            e = Event(name=name, val=val)
            self._meta_writer.add_event(e)

    def add_rng_seed(self, val, name=None):
        if name is None:
            name = '$rng-seed$all$'
        else:
            name = '$rng-seed${}$'.format(name)
        e = Event(name=name, val=val)
        self._meta_writer.add_event(e)

    def delta_time(self):
        return T.time() - self.start_time

    def get_step(self, name):
        if name in self._step_dict:
            step = self._step_dict[name]
            self._step_dict[name] += 1
        else:
            step = 0
            self._step_dict[name] = 1
        return step

    def _log_commit_id(self):
        id = None
        if fastgit:
            id = fastgit.get_commit_id(self._code_dir)
        e = Event(name='$fastgit.commit-id$', val=id)
        self._meta_writer.add_event(e)

    def close(self):
        self._loss_writer.close()
        self._metric_writer.close()
        self._scalar_writer.close()
        self._meta_writer.close()

    @property
    def start_time(self):
        return self._start_time

    def _log_start_time(self, time=None):
        if time is None:
            self._start_time = T.time()
        else:
            if not isinstance(time, (int, float)):
                raise TypeError('time must be int or float')
            self._start_time = time
        t = datetime.datetime.fromtimestamp(self._start_time)
        e = Event(name='$start-time$', val=t.strftime('%Y-%m-%d %H:%M:%S'))
        self._meta_writer.add_event(e)

    def _log_code_dir(self):
        e = Event(name='$code-dir$', val=self._code_dir)
        self._meta_writer.add_event(e)

    def _log_all_meta(self):
        """记录所有 meta 信息，现有：
            commit-id，库随机数种子，logger创建时间
        """
        self._log_commit_id()
        self._log_start_time()
        self._log_code_dir()
