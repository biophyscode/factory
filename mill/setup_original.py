#!/usr/bin/env python

"""
Prepare or check that the environment is ready for the factory.
"""

__all__ = ['check_env']

import os,time
from config import read_config,write_config,is_terminal_command,bash

def check_env(force=False,f=False):
	"""
	Checks whether the current environment is ready or not.
	Every time you run a factory `make` command, we check the last-setup timestamp in config and compare it
	to setup-influencing files e.g. requirements.txt.
	"""
	config = read_config()
	setup_stamp = config.get('setup_stamp',None)
	if not setup_stamp or (force or f): setup()
	else: raise Exception('dev check the stamp times')

def setup():
	"""
	Run the factory setup procedure.
	This routes you to the right setup procedure.
	"""
	config = read_config()
	if config.get('docker',False): setup_docker()
	else: 
		species = config.get('species',None)
		species_opts = ['virtualenv','virtualenv_sandbox']
		if not species or species not in species_opts:
			raise Exception('config.py must have key "species" from %r'%species_opts)
		#---call the setup program
		if species in ['virtualenv','virtualenv_sandbox']: 
			setup_virtualenv(sandbox=species=='virtualenv_sandbox')
	#---! stamp needs checked
	
def setup_docker():
	"""
	"""
	print('setting up docker')

def virtualenv_fail(name,extra=None):
	"""
	When virtualenv requires a system package we tell users that anaconda may be an option.
	"""
	message = 'failed to create a virtual environment: missing %s. '%name
	if extra: message += extra
	raise Exception(message)

def setup_virtualenv(sandbox=False):
	"""
	MAIN SETUP ROUTINE
	"""
	config = read_config()
	if is_terminal_command('virtualenv'): virtualenv_fail('virtualenv')

	#---! automatically start redis? prevent dump.rdb?

	#---preliminary checks
	#---! default redis conf?
	if is_terminal_command('redis-cli'):
		virtualenv_fail('redis-cli',
			extra='if you have redis installed, '+
				'you can run "sudo /usr/sbin/redis-server --daemonize yes". '+
				'if your redis is local (via e.g. anacodna) you can omit "sudo"')

	venv_opts = "--no-site-packages " if sandbox else "--system-site-packages "
	#---note that virtualenv can re-run on the env folder without issue
	start_time = time.time()
	bash('virtualenv %senv'%venv_opts,log='logs/log-virtualenv')
	print('[STATUS] installing packages via pip...')
	bash('source env/bin/activate && pip install -r mill/requirements_virtualenv.txt',log='logs/log-virtualenv-pip')
	print('[NOTE] setup took %.1f minutes'%((time.time()-start_time)/60.))
	required_upgrades = ['Sphinx>=1.4.4','numpydoc','sphinx-better-theme','beautifulsoup4']
	bash('pip install -U %s'%' '.join(["'%s'"%i for i in required_upgrades]),log='logs/log-virtualenv-pip')
	#---record success
	config['setup_stamp'] = time.strftime('%Y%m%d%H%M%s')
	write_config(config)
