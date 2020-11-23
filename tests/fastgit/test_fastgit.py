import unittest
import os
import shutil
from fitlog.fastgit import committer


class TextExample(unittest.TestCase):
    def setUp(self):  # 定义一个setup，放一些准备的工作，或者准备一些测试数据。
        os.mkdir('testArea')

    def test_init(self):
        ret = committer.init_project('testArea/test_pj', git=False)
        self.assertEqual(ret, 0)

    def tearDown(self):  # 定义一个tearDown，在测试完的时候我要对测试有一个销毁的过程
        shutil.rmtree('testArea', ignore_errors=True)

    # 基本参考 https://docs.python.org/zh-cn/3/library/unittest.html
    # mock 提供了更多的可能性 https://docs.python.org/zh-cn/3/library/unittest.mock.html

