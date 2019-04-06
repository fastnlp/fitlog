# fastlog
轻量级的机器学习实验记录工具。内部开发中

## 使用方法

使用`Logger`记录实验信息
```python
from fastlog import Logger
w = Logger(log_dir='...') # 传入log保存目录

# 记录实验参数
cfg = {'lr': 3e-4,
       'hidden': 400,
       'weight_decay': 1e-5,
       'lr_decay': 0.95, }
w.add_config(cfg)

# 随着实验进行，记录不同的值
w.add_scalar('c1', 1, step=1)
w.add_scalar('v2', 2.2, step=2)
w.add_scalar('v3', 0.3, step=3)
w.add_loss('corss_loss', 10.3, step=4)
w.add_metric('f1', 2.3, step=5)
w.add_metric('acc', 4.3, step=6)
w.close()
```

使用`LogReader`读取实验信息
```python
from fastlog import LogReader
r = LogReader(log_dir='...') # 传入log保存目录

# 所有read_*方法都返回生成器
meta = r.read_metas() # 读取每个实验meta信息
configs = r.read_configs() # 读取每个实验的设置
# 读取实验中数据，loss，metrics等
losses = r.read_losses() #读取每个实验最小loss
metrics = r.read_metrics() #读取每个实验最小&最大metric
scalars = r.read_scalars() #读取每个实验最小&最大scalar
 
print(list(meta))
print(list(configs))
# ... etc

```