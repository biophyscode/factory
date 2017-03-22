#!/usr/bin/env python

"""
Prepare or check that the environment is ready for the factory.
"""

__all__ = ['nuke','renew']

import os,sys,time,re,shutil
from config import read_config,write_config,is_terminal_command,bash,abspath
from makeface import fab

class FactoryEnv:

	"""
	Run things in a carefully-constructed environment.
	"""

	#---settings for different environments
	meta = {
		'virtualenv':{
			'reqs':['mill/requirements_virtualenv.txt'],
			'setup_kickstart':'setup_virtualenv',
			'setup_refresh':'setup_virtualenv_refresh',
			'loader_commands':{
				'env_activate':'source env/bin/activate',
				'env_deactivate':'deactivate'},
			'activate_script':'env/bin/activate_this.py',
			'welcome':'welcome_message'},
		#---need python2 vs 3
		'anaconda':{
			'reqs_conda':['mill/requirements_anaconda_conda.txt'],
			'reqs_pip':[],
			'setup_kickstart':'setup_anaconda',
			'setup_refresh':'setup_anaconda_refresh',
			'activate_script':'env/bin/pyvenv',
			'welcome':'welcome_message'}}
	#---! need a place to store env path !!! (see above; it's in the activate_script)	
	#---sandbox mimics the virtualenv and uses the same setup, with an extra flag not encoded here
	meta['virtualenv_sandbox'] = dict(meta['virtualenv'])
	meta['virtualenv_sandbox']['setup_kickstart'] = 'setup_virtualenv_sandbox'
	#---folder we always need at root
	required_folders = ['logs','connections']

	def __init__(self,):
		"""
		Create a factory environment from instructions in the config, and setup or refresh if necessary.
		"""
		#---create required folders for the factory
		for fn in self.required_folders:
			if not os.path.isdir(fn): os.mkdir(fn)
		#---get a copy of the configuration
		self.config = read_config()
		self.timestamp = self.config.get('setup_stamp',None)
		kind = self.config.get('species',None)
		if kind not in self.meta:
			raise Exception('environment type is %s, but it must be one of: %s'%(kind,self.meta.keys()))
		self.kind = kind
		for key in self.meta[kind]: self.__dict__[key] = self.meta[kind][key]
		#---make sure all requirements files are available no matter what 
		do_refresh = self.check_spotchange() if self.timestamp else True
		#---environment creation is divided into two parts: first run and refreshes
		start_time = time.time()
		if not self.timestamp: getattr(self,self.setup_kickstart)()
		if not self.timestamp or do_refresh: getattr(self,self.setup_refresh)()
		if do_refresh or not self.timestamp:
			print('[NOTE] setup took %.1f minutes'%((time.time()-start_time)/60.))
		#---! should we register every time this runs? or just when there is a refresh?
		self.register_finished()
		#---now that the environment is updated, we source it
		if sys.version_info<(3,0): execfile(self.activate_script,dict(__file__=self.activate_script))
		else: exec(open(self.activate_script).read())
		#---! RYAN DOES NOT TRUST ^^^ BECAUSE IT DOES NOT UPDATE BASH $VIRTUAL_ENV. check that this worked!
		#---! it would be nice to have a welcome message that confirms your environment is correct
		if hasattr(self,self.welcome): getattr(self,self.welcome)()

	def check_spotchange(self):
		"""
		Given a timestamp we see if any of the spots have changed. If they have, we run the refresh routine.
		"""
		reqs_keys = [i for i in self.__dict__ if re.match('^reqs',i)]
		#---loop over keys that start with "reqs" to check requirements files
		for req_type in reqs_keys:
			#---check spotchange only if timestamp is not None
			fns_changed = [fn for fn in self.__dict__[req_type] if 
				int(time.strftime('%Y%m%d%H%M%s',time.localtime(os.path.getmtime(fn))))>int(self.timestamp)]
		#---any requirement change requires a refresh
		#---! note that it might be useful to only run pip install on the ones that change?
		return any(fns_changed)

	def register_finished(self):
		"""
		Update the config.py to make note of the changes to the environment.
		"""
		#---! MOVE THIS TO THE self.meta
		#---record success and load/unload commands for the environment
		self.config['setup_stamp'] = time.strftime('%Y%m%d%H%M%s')
		### for key,val in self.loader_commands.items(): self.config[key] = val
		write_config(self.config)

	def setup_virtualenv_sandbox(self): 
		"""Wrapper for the sandboxed version of virtualenv setup which requires flag, is v. similar."""
		self.setup_virtualenv(sandbox=True)
 
	def setup_virtualenv(self,sandbox=False):
		"""
		Create a virtualenvironment.
		"""
		def virtualenv_fail(name,extra=None):
			"""
			When virtualenv requires a system package we tell users that anaconda may be an option.
			"""
			message = 'failed to create a virtual environment: missing %s. '%name
			if extra: message += extra
			raise Exception(message)
		if is_terminal_command('virtualenv'): virtualenv_fail('virtualenv')
		#---! automatically start redis? prevent dump.rdb?
		#---preliminary checks
		#---! default redis conf?
		if is_terminal_command('redis-cli'):
			virtualenv_fail('redis-cli',
				extra='if you have redis installed, '+
					'you can run "sudo /usr/sbin/redis-server --daemonize yes". '+
					'if your redis is local (via e.g. anacodna) you can omit "sudo"')
		#---you can sandbox or not
		venv_opts = "--no-site-packages " if sandbox else "--system-site-packages "
		#---note that virtualenv can re-run on the env folder without issue
		bash('virtualenv %senv'%venv_opts,log='logs/log-virtualenv')

	def setup_virtualenv_refresh(self):
		"""
		Refresh the virtualenvironment.
		"""
		for fn in self.reqs:
			print('[STATUS] installing packages via pip from %s'%fn)
			bash('source env/bin/activate && pip install -r %s'%fn,
				log='logs/log-virtualenv-pip-%s'%os.path.basename(fn))
		#---custom handling for required upgrades
		#---! would be useful to make this systematic
		required_upgrades = ['Sphinx>=1.4.4','numpydoc','sphinx-better-theme','beautifulsoup4']
		bash('pip install -U %s'%' '.join([
			"'%s'"%i for i in required_upgrades]),log='logs/log-virtualenv-pip')

	def welcome_message(self):
		print(fab('ENVIRONMENT','cyan_black'))
		bash('which python')

	def setup_anaconda(self):
		"""
		Set up anaconda.
		"""
		anaconda_location = self.config.get('anaconda_location',None)
		if not anaconda_location: 
			raise Exception('download anaconda and run `make set anaconda_location <path>`')
		install_fn = abspath(anaconda_location)
		if not os.path.isfile(install_fn): raise Exception('cannot find %s'%fn)
		bash('bash %s -b -p %s/env'%(install_fn,os.getcwd()))

	def setup_anaconda_refresh(self):
		"""
		Refresh the virtualenvironment.
		"""
		for fn in self.reqs_conda:
			print('[STATUS] installing packages via pip from %s'%fn)
			bash('source env/bin/activate && conda install -y --file %s'%fn,
				log='logs/log-anaconda-conda-%s'%os.path.basename(fn))
		
def nuke(sure=False):
	"""
	Start from scratch. Erases the environment and  resets the config. You must set the species after this.
	"""
	if sure or all(re.match('^(y|Y)',(input if sys.version_info>(3,0) else raw_input)
		('[QUESTION] %s (y/N)? '%msg))!=None for msg in ['okay to nuke everything','confirm']):
		#---reset procedure starts here
		write_config({
			'commands': ['mill/setup.py','mill/shipping.py','mill/factory.py'],
			'commands_aliases': [('set','set_config')]})
		#---we do not touch the connections, obviously, since you might nuke and reconnect
		#---deleting sensitive stuff here
		for fn in [i for i in ['data'] if os.path.isdir(i)]: shutil.rmtree(fn)
		for dn in ['env','logs','calc','data','pack','site']:
			if os.path.isdir(dn): shutil.rmtree(dn)

def renew(species=None,sure=False):
	"""
	These are test sets for the environment. Be careful -- it erases your current environment!
	"""
	if sure or all(re.match('^(y|Y)',(input if sys.version_info>(3,0) else raw_input)
		('[QUESTION] %s (y/N)? '%msg))!=None for msg in 
		['`renew` is a test set that deletes everything. okay?','confirm']):
		if not species: raise Exception('testset needs a species')
		if species=='virtualenv':
			bash('make nuke sure && make set species virtualenv && make test')
		elif species=='anaconda':
			bash(' && '.join([
				'make nuke sure',
				'make set species anaconda',
				'make set anaconda_location ~/libs/Anaconda3-4.2.0-Linux-x86_64.sh',
				'make test']))
		else: raise Exception('no testset for species %s'%species)
