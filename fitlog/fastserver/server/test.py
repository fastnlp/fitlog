
import numpy as np
from collections import OrderedDict


import random
import time

def strTimeProp(start, end, format, prop):
    """Get a time at a proportion of a range of two formatted times.

    start and end should be strings specifying times formated in the
    given format (strftime-style), giving an interval [start, end].
    prop specifies how a proportion of the interval to be taken after
    start.  The returned time will be in the specified format.
    """

    stime = time.mktime(time.strptime(start, format))
    etime = time.mktime(time.strptime(end, format))

    ptime = stime + prop * (etime - stime)

    return time.strftime(format, time.localtime(ptime))


def randomDate(start, end, prop):
    return strTimeProp(start, end, '%m/%d/%Y %I:%M %p', prop)


def generate_data(num_records=3):
    logs = []
    for i in range(num_records):
        res = OrderedDict()
        res['id'] = str(i) # id比如放在第一位

        # commid info
        c_res = OrderedDict()
        if np.random.randint(100)<90:
            c_res['fit_id'] = hex(np.random.randint(1e10))[2:10]
        c_res['git_id'] = hex(np.random.randint(1e10))[2:10]
        c_res['git_msg'] = chr(np.random.randint(65, 123))*np.random.randint(5, 100)
        c_res['time'] = randomDate("1/1/2008 1:30 PM", "1/1/2009 4:50 AM", random.random())
        res['meta'] = c_res

        # hyper param
        c_res = OrderedDict()
        c_res['lr'] = np.random.rand()
        if np.random.randn()<0.1:
            c_res['hidden_size'] = np.random.randint(100, 103)
            c_res['whatever'] = 2
            c_res['haha'] = np.random.randint(1, 103)
        res['hyper'] = np.random.rand()
        res['hyper'] = c_res

        # metric
        c_res = OrderedDict()
        c1_res = OrderedDict()
        c1_res['f1'] = np.random.random()
        c1_res['pre'] = np.random.random()
        c_res['F1SpanMetric'] = c1_res
        c1_res = OrderedDict()
        c1_res['f1'] = np.random.random()
        c1_res['pre1'] = np.random.random()
        c_res['F2SpanMetric'] = c1_res
        res['Metrics'] = c_res

        # # other
        if np.random.random()<0.5:
            c_res = OrderedDict()
            c_res['loss'] = np.random.rand()
            c2_res = OrderedDict()
            c3_res = OrderedDict()
            for i in range(2):
                c3_res['c3_1'] = np.random.choice(list('abcdef'))
                c3_res['c3_2'] = np.random.choice(list('abcdef'))
                c2_res['c2_{}'.format(i)] = c3_res
                c_res['c_{}'.format(i)] = c2_res
            res['others'] = c_res

        logs.append(res)
    return logs


if __name__ == '__main__':
    pass

