==============
环境变量
==============

在新版的 fitlog 中，用户可以在运行程序前使用环境变量 ``FITLOG_FLAG`` 影响 fitlog 的作用。
注意，该环境变量发生作用的时刻在于 fitlog 被 import 的瞬间，之后再改变环境变量不影响 fitlog 的作用。

环境变量 ``FITLOG_FLAG`` 有三种值: ``DEBUG`` , ``NO_COMMIT`` 和其它（包括为空）。

当 ``FITLOG_FLAG=DEBUG`` 时，程序中对 fitlog 的所有调用都不起作用。你也可以在代码中使用 ``fitlog.debug()`` 产生类似的效果。

当 ``FITLOG_FLAG=NO_COMMIT`` 时，程序中使用 fitlog 记录数据的调用正常，但 ``fitlog.commit()`` 失效。你可以在同时运行多个实验时，只进行一次自动 commit。

当 ``FITLOG_FLAG`` 为空或等于其它值时，不产生额外的效果。
