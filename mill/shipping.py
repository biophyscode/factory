#!/usr/bin/env python

__all__ = ['test','set_config','locate','testdocker']

import os,glob,subprocess
from setup import FactoryEnv
from config import bash,set_config
from cluster import Cluster

def test():
	"""
	Source and test the environment.
	"""
	from makeface import fab
	from distutils.spawn import find_executable
	print(fab('ENVIRONMENT:','cyan_black')+' %s'%find_executable('python'))

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
