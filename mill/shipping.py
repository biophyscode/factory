#!/usr/bin/env python

__all__ = ['test','set_config','locate','testdocker']

import os,glob
from setup import FactoryEnv
from config import bash,set_config

def test():
	"""
	Source and test the environment.
	"""
	env = FactoryEnv()

def testdocker():
	"""
	Testing docker.
	"""
	dock = Pier()

def locate(keyword):
	"""
	Find a function.
	"""
	os.system('find ./ -name "*.py" | xargs egrep --color=always "(def|class) \w*%s\w*"'%keyword)
