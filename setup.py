# -*- coding: utf-8 -*-
from setuptools import setup
from setuptools import find_packages


setup(
    name="PageAuto",
    version="0.0.1",
    description="An easy way to automate web app with selenium.",
    long_description=open("README.md", encoding="utf8").read(),
    author="Jo Tsai",
    author_email="joecai1990@gmail.com",
    url="https://github.com/JoTsaiCN/PageAuto",
    license="Apache license",
    packages=find_packages(exclude=("test",)),
    test_suite="test",
    install_requires=[
        'selenium',
        'PyYAML'
    ]
)
