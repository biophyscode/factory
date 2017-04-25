#!/usr/bin/env python

"""
Testing and utility functions for the command-line.
The factory.py module exposes factory-specific commands while setup.py handles the environment.
"""

__all__ = ['test','set_config','unset','locate','testdocker','testcluster']

import os,glob,subprocess,json
import time,datetime
from setup import FactoryEnv
from config import bash,set_config,unset
from cluster import backrun,Cluster

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

def confirm_env():
	"""
	Make sure we are in the right conda environment.
	Obviously this will not work if you use the virtualenv.
	Factory setup adds activate_env pointer to the environment activator to config.py which is run
	every time you run a factory command. This is a helpful feature for one-off factory make commands because
	then the user doesn't have to worry about environments. It's annoying for development, so we source
	the environment ourselves, `make unset activate_env` and this check makes sure we don't make mistakes.
	"""
	hint = 'try `source env/bin/activate py2` or `make set activate_env="env/bin/activate py2"`'
	try: check = bash('conda info --json',catch=True)
	except: raise Exception('you are definitely in the wrong environment because I cannot find `conda`'+hint)
	conda_info = json.loads(check['stdout'])
	if not os.path.relpath(conda_info['default_prefix'],conda_info['conda_prefix'])=='envs/py2':
		raise Exception('you are not in the right environment! '+hint)

def testcluster():
	"""
	"""
	confirm_env()
	backrun(cmd='python -u mill/start.py stop-cluster.sh',
		log='cluster.log',stopper='clusterhalt.sh',killsig='INT')
	#---! wait for the cluster to get ready
	time.sleep(2)
	if False:
		#---submit a few jobs
		for j in range(10):
			#---write a job request
			stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S.%f')
			with open('cluster/%s.req'%stamp,'w') as fp: 
				script = '\n'.join(['echo "WAITING"','sleep 12','echo "DERPPP"'])
				fp.write(json.dumps({'bash':script}))
			time.sleep(0.05)
