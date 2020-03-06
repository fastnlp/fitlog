#!/usr/bin/env python
# coding=utf-8
from setuptools import setup, find_packages

with open('README.md', encoding='utf-8') as f:
    readme = f.read()

with open('LICENSE', encoding='utf-8') as f:
    license = f.read()

with open('requirements.txt', encoding='utf-8') as f:
    reqs = f.read()

setup(
    name='fitlog',
    version='0.3.1',
    description='fitlog: Log tool for Deep Learning, developed by Fudan FastNLP Team',
    long_description=readme,
    long_description_content_type='text/markdown',
    license='Apache license',
    python_requires='>=3.6',
    include_package_data=True,
    packages=find_packages(),
    install_requires=reqs.strip().split('\n'),
    entry_points={
        'console_scripts':[
            'fitlog = fitlog.__main__:main_cmd'
        ]
    }
)
