#!/usr/bin/env python

"""
"""

import os,sys,glob,re,shutil,subprocess,textwrap,datetime
from config import bash,read_config
from makeface import abspath
from datapack import asciitree
from cluster import backrun

__all__ = ['connect','template','connect','run','shutdown']

from setup import FactoryEnv

str_types = [str,unicode] if sys.version_info<(3,0) else [str]

log_site = 'logs/site'
log_cluster = 'logs/cluster'
log_notebook = 'logs/notebook'

###---CONNECT PROCEDURE PORTED FROM original FACTORY

def find_and_replace(fn,*args):
	"""
	Mimic sed.
	"""
	#---replace some key lines
	with open(fn) as fp: text = fp.read()
	for f,t in args: text = re.sub(f,t,text,flags=re.M)
	with open(fn,'w') as fp: fp.write(text)

def package_django_module(source,projname):
	"""
	Packages and installs a django module.
	Note that this is necessary for the initial connection, even if you use the development code.
	"""
	dev_dn = os.path.join(source,projname)
	pack_dn = os.path.join('pack',projname)
	if not os.path.isdir(dev_dn): raise Exception('cannot find %s'%dev_dn)
	if os.path.isdir(pack_dn): raise Exception('%s already exists'%pack_dn)
	#---copy the generic python packager
	shutil.copytree('mill/packer',pack_dn)
	#---copy the development code into the same directory
	#---! make this pythonic
	bash('cp -a %s %s'%(dev_dn,os.path.join(pack_dn,'')))
	find_and_replace(os.path.join('pack',projname,'setup.py'),
		('^#---SETTINGS','packname,packages = \"%s\",[\"%s\"]'%(projname,projname)))
	find_and_replace(os.path.join('pack',projname,'MANIFEST.in'),
		('APPNAME',projname))
	#---prepare the package
	bash('python %s sdist'%os.path.join('pack',projname,'setup.py'))
	#---uninstall the package
	#try: bash('echo -e "y\n" | pip uninstall %s &> logs/log-pip-$projname'%projname)
	#except: pass
	#---install the package
	bash('pip install -U pack/%s/dist/%s-0.1.tar.gz'%(projname,projname),log='logs/log-pip-%s'%projname)

#---! note no calculator below
#---do not even think about changing this without MIRRORING the change in the development version
project_settings_addendum = """
#---django settings addendum
INSTALLED_APPS = tuple(list(INSTALLED_APPS)+['django_extensions','simulator','calculator'])
#---common static directory
STATICFILES_DIRS = [os.path.join(BASE_DIR,'static')]
TEMPLATES[0]['OPTIONS']['libraries'] = {'code_syntax':'calculator.templatetags.code_syntax'}
TEMPLATES[0]['OPTIONS']['context_processors'].append('calculator.context_processors.global_settings')
#---all customizations
from custom_settings import *
"""

#---project-level URLs really ties the room together
project_urls = """
from django.conf.urls import url,include
from django.contrib import admin
from django.views.generic.base import RedirectView
urlpatterns = [
	url(r'^$',RedirectView.as_view(url='simulator/',permanent=False),name='index'),
	url(r'^simulator/',include('simulator.urls',namespace='simulator')),
	url(r'^calculator/',include('calculator.urls',namespace='calculator')),
	url(r'^admin/', admin.site.urls),]
"""

def connect_single(connection_name,**specs):
	"""
	The big kahuna. Revamped recently.
	"""
	config = read_config()
	#---skip a connection if enabled is false
	if not specs.get('enable',True): return
	mkdir_or_report('data')
	mkdir_or_report('site')
	#---the site is equivalent to a django project
	#---the site draws on either prepackaged apps in the pack folder or the in-development versions in dev
	#---since the site has no additional data except taht specified in connect.yaml, we can always remake it
	if os.path.isdir('site/'+connection_name):
		print("[STATUS] removing the site for \"%s\" to remake it"%connection_name)
		shutil.rmtree('site/'+connection_name)
	#---regex PROJECT_NAME to the connection names in the paths sub-dictionary	
	#---note that "PROJECT_NAME" is therefore protected and always refers to the 
	#---...top-level key in connect.yaml
	#---! note that you cannot use PROJECT_NAME in spots currently
	for key,val in specs.items():
		if type(val)==str: specs[key] = re.sub('PROJECT_NAME',connection_name,val)
		elif type(val)==list:
			for ii,i in enumerate(val): val[ii] = re.sub('PROJECT_NAME',connection_name,i)
	#---paths defaults
	specs['plot_spot'] = specs.get('plot_spot',os.path.join('data',connection_name,'plot')) 
	specs['post_spot'] = specs.get('post_spot',os.path.join('data',connection_name,'post')) 
	specs['simulations_spot'] = specs.get('simulations_spot',os.path.join('data',connection_name,'sims'))
	specs['coords_spot'] = specs.get('coords_spot',os.path.join('data',connection_name,'coords'))

	#---cluster namer is set in a separate file
	cluster_namer = {}
	with open('mill/cluster_spec.py') as fp: exec(fp.read(),cluster_namer) 
	for key in [i for i in cluster_namer if i not in cluster_namer['keepsakes']]: del cluster_namer[key]

	###---DJANGO SETTINGS

	#---first define folders and (possibly) http git repos
	settings_custom = {
		'SIMSPOT':abspath(specs['simulations_spot']),
		#---! hard-coded. get it from config.py??
		'AUTOMACS':'http://github.com/bradleyrp/automacs',
		'PLOT':abspath(specs['plot_spot']),
		'POST':abspath(specs['post_spot']),
		'COORDS':abspath(specs['coords_spot']),
		#---omnicalc locations are fixed
		'CALC':abspath(os.path.join('calc',connection_name)),
		'FACTORY':os.getcwd(),
		#---! get this from config.py
		'CLUSTER':'cluster'}
	#---all paths are absolute unless they have a colon in them, in which case it is ssh or http
	#---we attach filesystem separators as well so that e.g. settings.SPOT can be added to relative paths
	settings_custom = dict([(key,os.path.join(os.path.abspath(val),'') if ':' not in val else val)
		for key,val in settings_custom.items()])
	settings_custom['CLUSTER_NAMER'] = cluster_namer
	#---if the user does not supply a gromacs_config.py the default happens
	#---option to specify gromacs config file for automacs
	if 'gromacs_config' in specs: 
		gromacs_config_fn = specs['gromacs_config']
		if not os.path.isfile(gromacs_config_fn):
			raise Exception('cannot find gromacs_config file at %s'%gromacs_config_fn)
		settings_custom['GROMACS_CONFIG'] = os.path.join(os.getcwd(),gromacs_config_fn)
	else: settings_custom['GROMACS_CONFIG'] = False
	#---additional custom settings which are not paths
	settings_custom['NOTEBOOK_PORT'] = 8888
	settings_custom['NAME'] = connection_name

	###---END DJANGO SETTINGS

	#---make local directories if they are absent or do nothing if the user points to existing data
	root_data_dir = 'data/'+connection_name
	#---always make data/PROJECT_NAME for the default simulation_spot therein
	mkdir_or_report(root_data_dir)
	for key in ['post_spot','plot_spot','simulations_spot']: 
		mkdir_or_report(abspath(specs[key]))
	#---we always include a "sources" folder in the new simulation spot for storing input files
	mkdir_or_report(abspath(specs.get('coords_spot',os.path.join('data',connection_name,'coords'))))

	#---check if database exists and if so, don't make superuser
	make_superuser = not os.path.isfile(specs['database'])

	#---get automacs,omnicalc from a central place if it is empty
	automacs_upstream = specs.get('automacs',config.get('automacs',None))
	msg = 'You can tell the factory where to get omnicalc/automacs by running e.g. '+\
		'`make set automacs=http://github.com/someone/automacs`.' 
	if not automacs_upstream: 
		raise Exception('need automacs in config.py for factory or the connection. '+msg)
	omnicalc_upstream = specs.get('omnicalc',config.get('omnicalc',None))
	if not omnicalc_upstream: 
		raise Exception('need omnicalc in config.py for factory or the connection. '+msg)

	#---note that previous version of factory prepended a source command in front of every call
	#---...however the factory handles this for us now
	#---django is accessed via packages imported in settings.py which is why we have to package them
	#---...this saves us from making N copies of the development code

	#---! YOU NEED TO MAKE THE DEVELOPMENT POSSIBLE SOMEHWERE HEREABOUTS

	#---! hard-coding the location of the sources
	django_source = 'interface'
	#---! switching to new development codes...calculator not available yet
	for app in ['simulator','calculator']: 
		if not os.path.isdir('pack/%s'%app): 
			package_django_module(source=django_source,projname=app)
	
	#---one new django project per connection
	bash('django-admin startproject %s'%connection_name,
		log='logs/log-%s-startproject'%connection_name,cwd='site/')
	#---link the static files to the development codes (could use copytree)
	os.symlink(os.path.join(os.getcwd(),django_source,'static'),
		os.path.join('site',connection_name,'static'))

	#---all settings are handled by appending to the django-generated default
	#---we also add changes to django-default paths
	with open(os.path.join('site',connection_name,connection_name,'settings.py'),'a') as fp:
		fp.write(project_settings_addendum)
		if specs.get('development',False):
			fp.write('#---use the development copy of the code\n'+
				'import sys;sys.path.insert(0,os.path.join(os.getcwd(),"%s"))'%django_source) 

	#---write custom settings
	#---some settings are literals
	custom_literals = ['CLUSTER_NAMER']
	with open(os.path.join('site',connection_name,connection_name,'custom_settings.py'),'w') as fp:
		#---! proper way to write python constants?
		fp.write('#---custom settings are auto-generated from mill.factory.connect_single\n')
		for key,val in settings_custom.items():
			#---! is there a pythonic way to write a dictionary to a script of immutables
			if ((type(val) in str_types and re.match('^(False|True)$',val)) or key in custom_literals
				or type(val)==bool):
				out = '%s = %s\n'%(key,val)
			else: out = '%s = "%s"\n'%(key,val)
			fp.write(out)
	#---write project-level URLs
	with open(os.path.join('site',connection_name,connection_name,'urls.py'),'w') as fp:
		fp.write(project_urls)

	#---clone omnicalc if necessary
	omnicalc_previous = os.path.isdir('calc/%s'%connection_name)
	if not omnicalc_previous:
		bash('git clone %s calc/%s'%(omnicalc_upstream,connection_name),
			 log='logs/log-%s-git-omni'%connection_name)
		#---if this is fresh we run `make setup` because that provides a minimal config.py
		bash('make setup',cwd=specs['calc'])
	else: print('[NOTE] found calc/%s'%connection_name)

	#---initial migration for all new projects to start the database
	#---...!!!!!!!!!!!!!!
	print('[NOTE] migrating ...')
	bash('python site/%s/manage.py makemigrations'%connection_name,
		log='logs/log-%s-migrate'%connection_name)
	bash('python site/%s/manage.py migrate --run-syncdb'%connection_name,
		log='logs/log-%s-migrate'%connection_name)
	print('[NOTE] migrating ... done')
	if make_superuser:
		print("[STATUS] making superuser")
		su_script = "from django.contrib.auth.models import User; "+\
			"User.objects.create_superuser('admin','','admin');print;quit();"
		p = subprocess.Popen('python ./site/%s/manage.py shell'%(connection_name),		
			stdin=subprocess.PIPE,stderr=subprocess.PIPE,stdout=open(os.devnull,'w'),
			shell=True,executable='/bin/bash')
		catch = p.communicate(input=su_script if sys.version_info<(3,0) else su_script.encode())[0]
	print("[STATUS] new project \"%s\" is stored at ./data/%s"%(connection_name,connection_name))
	print("[STATUS] replace with a symlink if you wish to store the data elsewhere")

	#---set up the calculations directory in omnicalc
	#---check if the repo pointer in the connection is a valid path
	new_calcs_repo = not (os.path.isdir(abspath(specs['repo'])) and (
		os.path.isdir(abspath(specs['repo'])+'/.git') or os.path.isfile(abspath(specs['repo'])+'/HEAD')))
	downstream_git_fn = os.path.join('calc',connection_name,'calcs','.git')
	#---if the repo key gives a web address and we already cloned it, then we do nothing and suggest a pull
	if ':' in specs['repo'] and os.path.isdir(downstream_git_fn):
		print('[NOTE] the calc repo (%s) appears to be remote and %s exists.'%(
			specs['calc'],downstream_git_fn)+'you should pull the code manually to update it')
	#---check that a calcs repo from the internet exists
	elif new_calcs_repo and re.match('^http',specs['repo']):
		#---see if the repo is a URL. code 200 means it exists
		if sys.version_info<(3,0): from urllib2 import urlopen
		else: from urllib.request import urlopen
		code = urlopen(specs['repo']).code
		if code!=200: raise Exception('repo appears to be http but it does not exist')
		else: bash('make clone_calcs source="%s"'%specs['repo'],cwd=specs['calc'])
	#---check that the repo has a colon in the path, implying a remote ssh connection is necessary
	elif new_calcs_repo and ':' in specs['repo']:
		print('[WARNING] assuming that the calcs repository is on a remote machine: %s'%specs['repo'])
		bash('make clone_calcs source="%s"'%specs['repo'],cwd=specs['calc'])
	#---if the calcs repo exists locally, we just clone it
	elif not new_calcs_repo and os.path.isdir(downstream_git_fn): 
		print('[NOTE] git appears to exist at %s already and connection does not specify '%
			os.path.join(abspath(specs['repo']),'.git')+
			'an upstream calcs repo so we are continuing without action')
	elif not new_calcs_repo and not os.path.isfile(downstream_git_fn): 
		bash('make clone_calcs source="%s"'%specs['repo'],cwd=specs['calc'])
	#---make a fresh calcs repo because the meta file points to nowhere
	else:
		os.mkdir(specs['repo'])
		bash('git init',cwd=specs['repo'])
		#---after making a blank repo we put a placeholder in the config
		bash('make set calculations_repo="no_upstream"',cwd=specs['calc'])
		msg = ('When connecting to project %s, the "repo" flag in your connection file points to nowhere. '
			'We made a blank git repository at %s. You should develop your calculations there, push that '
			'repo somewhere safe, and distribute it to all your friends, who can use the "repo" flag to '
			'point to it when they start their factories.')
		print('\n'.join(['[NOTE] %s'%i for i in textwrap.wrap(
			msg%(connection_name,specs['repo']),width=60)]))

	#---pass a list of meta_filters through (can be list of strings which are paths or globs)
	calc_meta_filters = specs.get('calc_meta_filters',None)
	if calc_meta_filters:
		for filt in calc_meta_filters:
			#---note that meta_filter is turned into a list in config.py in omnicalc
			bash('make set meta_filter="%s"'%filt,cwd=specs['calc'])

	#---configure omnicalc 
	#---note that make set commands can change the configuration without a problem
	bash('make set post_data_spot=%s'%settings_custom['POST'],cwd=specs['calc'])
	bash('make set post_plot_spot=%s'%settings_custom['PLOT'],cwd=specs['calc'])
	#---! needs to interpret simulation_spot, add spots functionality
	#---! previously ran register_calculation.py here -- may be worth recapping in this version?
	#---! prepare vhost file here when it's ready
	#---??? IS THIS IT ???

#---! later you need to add omnicalc functionality
if False: get_omni_dataspots = """if os.path.isfile(CALCSPOT+'/paths.py'):
    omni_paths = {};execfile(CALCSPOT+'/paths.py',omni_paths)
    DATASPOTS = omni_paths['paths']['data_spots']
    del omni_paths
"""

###---UTILITY FUNCTIONS

def template(template=None,name=None):
	"""
	List templates and possibly create one for the user.
	"""
	template_source = 'connection_templates.py'
	if sys.version_info<(3,0):
		templates = {}
		execfile(os.path.join(os.path.dirname(__file__),template_source),templates)
		for key in [i for i in templates if not re.match('^template_',i)]: templates.pop(key)
		asciitree({'templates':templates.keys()})
	else: raise Exception('dev')
	#---if the user requests a template, write it for them
	if not template and not name: print('[NOTE] rerun with e.g. '+
		'`make template <template_name> <connection_file>` to make a new connection. '+
		'you can omit the connection file name.')
	elif name and not template: raise Exception('you must supply a template_name')
	elif template not in templates: raise Exception('cannot find template "%s"'%template)
	elif not name and template: name = template+'.yaml'
	#---write the template
	if template:
		fn = os.path.join('connections',name)
		if not re.match('^.+\.yaml$',fn): fn = fn+'.yaml'
		with open(fn,'w') as fp:
			fp.write(templates[template])
		print('[NOTE] wrote a new template to %s'%fn)

def mkdir_or_report(dn):
	"""
	"""
	if os.path.isdir(dn): print("[STATUS] found %s"%(dn))
	else: 
		os.mkdir(dn)
		print("[STATUS] created %s"%dn)

def read_connection(*args):
	"""
	Parse a connection yaml file.
	"""
	import yaml
	toc = {}
	for arg in args:
		with open(arg) as fp: 
			contents = yaml.load(fp.read())
			for key,val in contents.items():
				if key in toc: 
					raise Exception('found key %s in the toc already. redundant copy in %s'%arg)
				toc.update(**{key:val})
	return toc

def connect(name=None):
	"""
	Connect or reconnect a particular project.
	"""
	#---get all available connections
	connects = glob.glob('connections/*.yaml')
	if not connects: raise Exception('no connections available. try `make template` for some examples.')
	#---read all connection files into one diction ary
	toc = read_connection(*connects)
	if name and name not in toc: raise Exception('cannot find projecte named "%s" in the connections'%name)
	#---which connections we want to make
	targets = [name] if name else toc.keys()
	#---loop over desired connections
	for project in targets: connect_single(project,**toc[project])

def check_port(port):
	"""
	"""
	import socket
	s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	try: s.bind(("127.0.0.1",port))
	except socket.error as e: raise Exception('port %d is not free: %s'%(port,str(e)))
	s.close()

def start_site(name,lock='pid.site.lock',log=log_site):
	"""
	"""
	#---start django
	site_dn = os.path.join('site',name)
	if not os.path.isdir(site_dn): 
		raise Exception('missing site/%s. did you forget to connect it?'%name)
	check_port(8000)
	#---for some reason you have to KILL not TERM the runserver
	#---! replace runserver with something more appropriate? a real server?
	backrun(cmd='python %s runserver'%os.path.join(os.getcwd(),site_dn,'manage.py'),
		log=log,stopper=lock,killsig='KILL',scripted=False)
	return lock,log

def start_cluster(lock='pid.cluster.lock',log=log_cluster):
	"""
	"""
	#---if you want to run multiple clusters, use a more nuanced check for stale clusters
	regex_stale = 'mill/cluster_start.py'
	#---pre-check that there are no running clusters
	ask = subprocess.Popen('ps xao comm,args',shell=True,
		stdout=subprocess.PIPE,stderr=subprocess.PIPE,executable='/bin/bash')
	stdout,stderr = ask.communicate()
	if re.search(regex_stale,stdout):
		raise Exception('there appears to be a stale cluster already running!')
	#---start the cluster. argument is the location of the kill switch for clean shutdown
	#---! eventually the cluster should move somewhere safe and the kill switches should be hidden
	#---! ...make shutdown should manage the clean shutdown
	backrun(cmd='python -u mill/cluster_start.py %s'%lock,
		log=log,stopper=lock,killsig='INT',scripted=False)
	return lock,log

def daemon_ender(fn,cleanup=True):
	"""
	Read a lock file and end the job with a particular message
	"""
	try: bash('bash %s'%fn)
	except Exception as e: 
		print('[WARNING] failed to shutdown lock file %s with exception:\n%s'%(fn,e))
	if cleanup: os.remove(fn)

def stop_locked(what,lock,log,cleanup=True):
	"""
	Save the logs and terminate the server.
	"""
	if what not in ['site','cluster','notebook']: raise Exception('can only stop site or cluster')
	#---terminate first in case there is a problem saving the log
	daemon_ender(lock,cleanup=cleanup)
	stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
	if not os.path.isdir('logs'): raise Exception('logs directory is missing')
	shutil.move(log,'logs/arch.%s.%s.log'%(what,stamp))

def start_notebook(name,lock='pid.notebook.lock',log=log_notebook):
	"""
	"""
	check_port(8888)
	if not os.path.isdir(os.path.join('site',name)):
		raise Exception('cannot find site for %s'%name)
	#---note that TERM safely closes the notbook server
	backrun(cmd='python site/%s/manage.py shell_plus --notebook --no-browser'%name,
		log=log,stopper=lock,killsig='TERM',scripted=False)
	return lock,log

def run(name):
	"""
	"""
	#---start the site first before starting the cluster
	lock_site,log_site = start_site(name)
	try: lock_cluster,log_cluster = start_cluster()
	except Exception as e:
		stop_locked('site',lock=lock_site,log=log_site)
		raise Exception('failed to start the cluster so we shut down the site. exception: %s'%str(e)) 
	start_notebook(name)
	#except: print('[WARNING] notebook failed!')

def shutdown():
	"""
	"""
	try: stop_locked('notebook',lock='pid.notebook.lock',log=log_notebook)
	except Exception as e: print('[WARNING] failed to stop notebook. exception: %s'%str(e))
	try: stop_locked('site',lock='pid.site.lock',log=log_site)
	except Exception as e: print('[WARNING] failed to stop site. exception: %s'%str(e))
	#---the cluster cleans up after itself so we do not run the cleanup
	try: stop_locked('cluster',lock='pid.cluster.lock',log=log_cluster,cleanup=False)
	except Exception as e: print('[WARNING] failed to stop cluster. exception: %s'%str(e))
