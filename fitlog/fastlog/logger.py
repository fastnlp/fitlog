from src.fastlog.writer import FileWriter, Event
import os
from os import path
import datetime
import time as T
import random, numpy, torch
import argparse
try:
    from src import fastgit
except ImportError:
    import warnings
    warnings.warn('fastgit is missing, cannot log code', ImportWarning)
    fastgit = None


def set_rng_seeds(seed=None):
    if seed is None:
        seed = numpy.random.randint(0, 0x80000000)
    else:
        seed = int(seed)
    random.seed(seed)
    numpy.random.seed(seed)
    torch.random.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    # print('RNG_SEED {}'.format(seed))
    return seed

class Logger():
    def __init__(self, log_dir='log_dir'):
        self._start_time = None
        self._commit_id = None
        self._rng_seed = None
        # TODO gather all logs' dir
        self._root_dir = log_dir
        self._step_dict = {}
        os.makedirs(log_dir, exist_ok=True)
        self._event_writer = FileWriter(fn=path.join(self._root_dir, 'event.log'))
        self._meta_writer = FileWriter(fn=path.join(self._root_dir, 'meta.log'))
        self._log_all_meta()


    def add_scalar(self, name, value, step=None):
        if step is None:
            step = self.get_step(name)
        e = Event(time=self.delta_time(), step=step, name=name, val=value)
        self._event_writer.add_event(e)

    def add_loss(self, name, value, step=None):
        self.add_scalar_dict(name='loss', scalar_dict={name: value}, step=step)

    def add_metric(self, name, value, step=None):
        self.add_scalar_dict(name='metric', scalar_dict={name: value}, step=step)

    def add_scalar_dict(self, name, scalar_dict, step=None):
        if step is None:
            step = self.get_step(name)
        e = Event(time=self.delta_time(), step=step, name=name, val=scalar_dict)
        self._event_writer.add_event(e)

    def add_scalars(self, scalars, step=None):
        for name, val in scalars.items():
            self.add_scalar(name=name, value=val, step=step)

    def add_config(self, cfg_dict):
        # support for args from command-line
        if isinstance(cfg_dict, argparse.Namespace):
            cfg_dict = cfg_dict.__dict__
        elif not isinstance(cfg_dict, dict):
            raise TypeError('cannot support config type: {}'.format(type(cfg_dict)))
        for name, val in cfg_dict.items():
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
            fastgit.commit()
            id = fastgit.get_commit_id()
        e = Event(name='$commit-id$', val=id)
        self._meta_writer.add_event(e)

    def close(self):
        self._event_writer.close()
        self._meta_writer.close()

    @property
    def start_time(self):
        return self._start_time

    @property
    def rng_seed(self):
        return self._rng_seed

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

    def _log_rng_seeds(self, seed=None):
        # TODO add more seed if need
        seed = set_rng_seeds(seed)
        self._rng_seed = seed
        e = Event(name='$rng-seed$', val=seed)
        self._meta_writer.add_event(e)

    def _log_code_dir(self):
        # TODO maybe we need this
        pass

    def _log_all_meta(self):
        """记录所有 meta 信息，现有：
            commit-id，库随机数种子，logger创建时间
        """
        self._log_commit_id()
        self._log_rng_seeds()
        self._log_start_time()
        self._log_code_dir()
