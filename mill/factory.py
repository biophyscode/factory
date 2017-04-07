#!/usr/bin/env python

"""
"""

import os,sys,glob,re,shutil,subprocess
from config import bash,read_config
from makeface import abspath
from datapack import asciitree

__all__ = ['connect','template','connect','run','shutdown']

from setup import FactoryEnv

###---CONNECT PROCEDURE PORTED FROM original FACTORY

settings_additions = """
#---automatically added from kickstart
INSTALLED_APPS = tuple(list(INSTALLED_APPS)+['simulator','calculator'])
"""

get_omni_dataspots = """if os.path.isfile(CALCSPOT+'/paths.py'):
    omni_paths = {};execfile(CALCSPOT+'/paths.py',omni_paths)
    DATASPOTS = omni_paths['paths']['data_spots']
    del omni_paths
"""

urls_additions = """
#---automatically added
from django.conf.urls import include, url
from django.views.generic.base import RedirectView
urlpatterns += [
	url(r'^simulator/',include('simulator.urls',namespace='simulator')),
	url(r'^calculator/',include('calculator.urls',namespace='calculator')),
	url(r'^$',RedirectView.as_view(url='calculator/',permanent=False),name='index'),
	]
"""

#---permission settings for apache
media_segment = """
    Alias %s "%s"
    <Directory %s>
        Require all granted
    </Directory> 
"""

#---! note previously used "Options Indexes FollowSymLinks" for write directories
vhost_config = """
#---to serve FACTORY:
#---install apache2 and WSGI
#---copy this file to /etc/apache2/vhosts.d/
#---add "WSGIPythonPath /home/localshare/analysis/mplxr/env" to httpd.conf and substitue paths below
#---restart apache
<VirtualHost *:%d>
    ServerName %s
    ServerAlias factory
    DocumentRoot %s
%s
    WSGIScriptAlias / %s
    WSGIDaemonProcess factory python-path=%s:%s:%s
    WSGIProcessGroup factory
    <Directory %s>
    	Order allow,deny
    	Allow from all
    	Require all granted
    </Directory>
</VirtualHost>
"""

#---the development path must be within the factory
absolute_environment_path = abspath('env')

def find_and_replace(fn,*args):
	"""
	Mimic sed.
	"""
	#---replace some key lines
	with open(fn) as fp: text = fp.read()
	for f,t in args: text = re.sub(f,t,text,flags=re.M)
	with open(fn,'w') as fp: fp.write(text)

def package_django_module(projname):
	"""
	Packages and installs a django module.
	Note that this is necessary for the initial connection, even if you use the development code.
	"""
	dev_dn = os.path.join('dev',projname)
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

def prepare_vhosts(rootdir,connection_name,port=None,dev=True):

	"""
	Prepare virtualhost configuration for users to serve over apache2.
	"""

	site_packages = 'env/lib/python2.7/site-packages'
	#---we append the root directory to these media locations
	aliases = {
		'/static/calculator/':os.path.join(rootdir,'dev' if dev else site_packages,
			'calculator/static/calculator',''),
		'/static/simulator/':os.path.join(rootdir,'dev' if dev else site_packages,
			'simulator/static/simulator',''),}
	#---generic server settings
	serveset = {'port':88,'domain':'127.0.0.1',
		'document_root':os.path.join(rootdir,'site',connection_name,''),}
	alias_conf = ''
	for key,val in aliases.items(): 
		alias_conf += media_segment%(key,val,val)
	conf = vhost_config%(
		serveset['port'] if not port else port,
		serveset['domain'],
		serveset['document_root'],
		alias_conf,
		os.path.join(rootdir,'site',connection_name,connection_name,'wsgi.py'),
		os.path.join(rootdir,'site',connection_name,''),
		#---add dev early
		os.path.join(rootdir,'dev',''), 
		os.path.join(rootdir,site_packages),
		rootdir)
	return conf

def connect_single(connection_name,**specs):

	"""
	The big kahuna.
	"""

	import yaml

	#---always source the environment
	env = FactoryEnv()
	config = read_config()

	#---! for some reason py35 does not get sourced correctly but py27 does ??? see django-admin executable
	backrun = 'oldschool'

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

	#---PREPROCESS THE CONNECTION SETTINGS

	#---regex PROJECT_NAME to the connection names in the paths sub-dictionary	
	#---note that "PROJECT_NAME" is therefore protected and always refers to the top-level key in connect.yaml
	#---! note that you cannot use PROJECT_NAME in spots currently
	for key,val in specs.items():
		if type(val)==str: specs[key] = re.sub('PROJECT_NAME',connection_name,val)
		elif type(val)==list:
			for ii,i in enumerate(val): val[ii] = re.sub('PROJECT_NAME',connection_name,i)

	#---PREPARE DIRECTORIES

	#---make local directories if they are absent or do nothing if the user points to existing data
	root_data_dir = 'data/'+connection_name
	#---always make data/PROJECT_NAME for the default simulation_spot therein
	mkdir_or_report(root_data_dir)
	for key in ['post_data_spot','post_plot_spot','simulation_spot']: 
		mkdir_or_report(abspath(specs[key]))
	#---we always include a "sources" folder in the new simulation spot for storing input files
	mkdir_or_report(abspath(specs['simulation_spot']+'/sources/'))

	#---check if database exists and if so, don't make superuser
	make_superuser = not os.path.isfile(specs['database'])

	#---get automacs,omnicalc from a central place if it is empty
	automacs_upstream = specs.get('automacs',config.get('automacs',None))
	if not automacs_upstream: raise Exception('need automacs in config.py for factory or the connection')
	omnicalc_upstream = specs.get('omnicalc',config.get('omnicalc',None))
	if not omnicalc_upstream: raise Exception('need omnicalc in config.py for factory or the connection')

	#---interpret paths from connect.yaml for PROJECT_NAME/PROJECT_NAME/settings.py in the django project
	#---these paths are all relative to the rootspot, the top directory for the factory codes
	settings_paths = {
		'rootspot':os.path.join(os.getcwd(),''),
		'automacs_upstream':automacs_upstream,
		'project_name':connection_name,
		'plotspot':abspath(specs['post_plot_spot']),
		'postspot':abspath(specs['post_data_spot']),
		'dropspot':abspath(specs['simulation_spot']),
		'calcspot':specs['calc']}

	#---prepare additions to the settings.py and urls.py
	settings_append_fn = 'logs/setup-%s-settings-append.py'%connection_name
	urls_append_fn = 'logs/setup-%s-urls-append.py'%connection_name
	with open(settings_append_fn,'w') as fp:
		if 'development' in specs and specs['development']: 
			devpath = "import sys;sys.path.insert(0,os.getcwd()+'/dev/')" 
		else: devpath = ""
		for key,val in settings_paths.items():
			fp.write('%s = "%s"\n'%(key.upper(),val))
		fp.write(devpath+settings_additions)
		fp.write('\n#---run in the background the old-fashioned way\nBACKRUN = "%s"\n'%backrun)
		if 'omni_gromacs_config' in specs and specs['omni_gromacs_config']:
			fp.write('#---automacs/gromacs config file\nAMX_CONFIG = \"%s\"\n'%os.path.abspath(
				os.path.expanduser(specs['omni_gromacs_config'])))
		else: fp.write('#---automacs/gromacs config file\nAMX_CONFIG = None\n')
		for key in ['PLOTSPOT','POSTSPOT','ROOTSPOT']: 
			fp.write('%s = os.path.expanduser(os.path.abspath(%s))\n'%(key,key))
		#---must specify a database location
		if 'database' in specs: 
			fp.write("DATABASES['default']['NAME'] = \"%s\"\n"%os.path.abspath(specs['database']))
		if 'lockdown' in specs: fp.write(lockdown_extra%specs['lockdown'])
		fp.write(get_omni_dataspots)
		if specs.get('spots',None):
			#---append a lookup table for spots locations here
			path_lookups = dict([(key,re.sub('PROJECT_NAME',connection_name,
				abspath(os.path.join(val['route_to_data'],val['spot_directory']))))
				for key,val in specs['spots'].items()])
		else: path_lookups = {}
		fp.write('PATHFINDER = %s\n'%str(path_lookups))
		#---if port is in the specs we serve the development server on that port and celery on the next
		if 'port' in specs and backrun in ['celery','celery_backrun','old']: 
			fp.write('DEVPORT = %d\nCELERYPORT = %d\n'%(specs['port'],specs['port']+1))
		else: fp.write('DEVPORT = %d\nCELERYPORT = %d\n'%(8000,8001))
	with open(urls_append_fn,'w') as fp: fp.write(urls_additions)

	#---previous version of factory prepended a source command in front of every call
	#---django is accessed via packages imported in settings.py which is why we have to package them
	for app in ['simulator','calculator']: 
		if not os.path.isdir('pack/%s'%app): package_django_module(app)
	bash('django-admin startproject %s'%connection_name,
		log='logs/log-%s-startproject'%connection_name,cwd='site/')
	bash('cat %s >> site/%s/%s/settings.py'%(settings_append_fn,connection_name,connection_name))
	bash('cat %s >> site/%s/%s/urls.py'%(urls_append_fn,connection_name,connection_name))

	#---clone omnicalc if necessary
	omnicalc_previous = os.path.isdir('calc/%s'%connection_name)
	if not omnicalc_previous:
		bash('git clone %s calc/%s'%(omnicalc_upstream,connection_name),
			 log='logs/log-%s-git-omni'%connection_name)
		#---if this is fresh we run `make setup` because that provides a minimal config.py
		bash('make setup',cwd=specs['calc'])
	else: print('[NOTE] found calc/%s'%connection_name)

	if False:
		if not os.path.isdir('data/%s/sims/docs'%connection_name):
			bash('git clone %s data/%s/sims/docs'%(specs['automacs'],connection_name),
				log='logs/log-%s-git-amx'%connection_name)
		#bash('make docs',cwd='data/%s/sims/docs'%connection_name,
		#	log='logs/log-%s-automacs-docs'%connection_name)
		#---! no more config?
		#bash('make config defaults',cwd='calc/%s'%connection_name,
		#	log='logs/log-%s-omnicalc-config'%connection_name,env=True)
		for dn in ['calc/%s/calcs'%connection_name,'calc/%s/calcs/scripts'%connection_name]: 
			if not os.path.isdir(dn): os.mkdir(dn)
		#bash('make docs',cwd='calc/%s'%connection_name,log='logs/log-%s-omnicalc-docs'%connection_name)
		if backrun in ['celery','celery_backrun']:
			shutil.copy('deploy/celery_source.py','site/%s/%s/celery.py'%(connection_name,connection_name))
			#---BSD/OSX sed does not do in-place replacements
			bash('perl -pi -e s,multiplexer,%s,g site/%s/%s/celery.py'%
				(connection_name,connection_name,connection_name))	

	#---! what does this migration do?
	print('[NOTE] migrating ...')
	bash('python site/%s/manage.py migrate'%connection_name,
		log='logs/log-%s-migrate'%connection_name)
	print('[NOTE] migrating ... done')
	if make_superuser:
		print("[STATUS] making superuser")
		su_script = "from django.contrib.auth.models import User; "+\
			"User.objects.create_superuser('admin','','admin');print;quit();"
		p = subprocess.Popen('python ./site/%s/manage.py shell'%(connection_name),		
			stdin=subprocess.PIPE,stderr=subprocess.PIPE,stdout=open(os.devnull,'w'),
			shell=True,executable='/bin/bash')
		catch = p.communicate(input=su_script)[0]
	print("[STATUS] new project \"%s\" is stored at ./data/%s"%(connection_name,connection_name))
	print("[STATUS] replace with a symlink if you wish to store the data elsewhere")

	#---set up the calculations directory in omnicalc
	#---check if the repo pointer in the connection is a valid path
	#---! can this handle github paths? probably not. check and warn the user.
	new_calcs_repo = not (os.path.isdir(abspath(specs['repo'])) and (
		os.path.isdir(abspath(specs['repo'])+'/.git') or os.path.isfile(abspath(specs['repo'])+'/HEAD')))
	#---see if the repo is a URL. code 200 means it exists
	try:
		from urllib2 import urlopen
		url_return_code = urlopen(specs['repo']).code
	except: url_return_code = 0 
	if new_calcs_repo and url_return_code!=200: pass
	else: bash('make clone_calcs source="%s"'%specs['repo'],cwd=specs['calc'])

	#---configure omnicalc 
	#---note that make set commands can change the configuration without a problem
	bash('make set post_data_spot=%s'%settings_paths['postspot'],cwd=specs['calc'])
	bash('make set post_plot_spot=%s'%settings_paths['plotspot'],cwd=specs['calc'])
	#---! is the above comprehensive?
	#---! needs to interpret simulation_spot, add spots functionality

	if False:
		#---if the repo points nowhere we prepare a calcs folder for omnicalc (repo is required)
		new_calcs_repo = not (os.path.isdir(abspath(specs['repo'])) and (
			os.path.isdir(abspath(specs['repo'])+'/.git') or os.path.isfile(abspath(specs['repo'])+'/HEAD')))
		if new_calcs_repo:
			print("[STATUS] repo path %s does not exist so we are making a new one"%specs['repo'])
			mkdir_or_report(specs['calc']+'/calcs')
			bash('git init',cwd=specs['calc']+'/calcs',log='logs/log-%s-new-calcs-repo'%connection_name)
			#---! AUTO POPULATE WITH CALCULATIONS HERE
		#---if the repo is a viable git repo then we clone it
		else: 
			if not specs['repo']==specs['calc']+'/calcs':
				#---remove the "blank" calcs folders if they appear to be blank before cloning
				#---! note that it would be far better to simply require any user preserve their code with a git
				#if set([i for j in [fn 
				#	for root,dn,fn in os.walk('calc/%s/calcs'%connection_name)] 
				#	for i in j])==set(['.info','__init__.py']):
				shutil.rmtree(specs['calc']+'/calcs')
				try: bash('git clone '+specs['repo']+' '+specs['calc']+'/calcs',cwd='./',
					log='logs/log-%s-clone-calcs-repo'%connection_name)
				except:
					print('[WARNING] tried to clone %s into %s but it exists'%(
						specs['repo'],specs['calc']+'/calcs'))
		#---create directories if they are missing
		mkdir_or_report(specs['calc']+'/calcs/specs/')
		mkdir_or_report(specs['calc']+'/calcs/scripts/')
		mkdir_or_report(specs['calc']+'/calcs/codes/')
		subprocess.check_call('touch __init__.py',cwd=specs['calc']+'/calcs/scripts',
			shell=True,executable='/bin/bash')

	#---! NO. PRELOADS ARE CLUMSY
	if False:
		#---if startup then we load some common calculations (continued below)
		if specs['startup']: 
			bash('rsync -ariv deploy/preloads/ %s/calcs/'%specs['calc'],
				cwd='./',log='logs/log-%s-preloads'%connection_name)

	#---! add these calculations to the database (possibly for FACTORY)
	if 0: subprocess.check_call(
		'source env/bin/activate && python ./deploy/register_calculation.py %s %s %s'%
		(specs['site'],connection_name,specs['calc']),shell=True,executable='/bin/bash')

	if False:
		#---write the paths.yaml for the new omnicalc with the correct spots, paths, etc
		default_paths = {}
		default_paths['post_data_spot'] = settings_paths['postspot']
		default_paths['post_plot_spot'] = settings_paths['plotspot']
		default_paths['workspace_spot'] = abspath(specs['workspace_spot'])
		default_paths['timekeeper'] = specs.get('timekeeper',False)
		default_paths['spots'] = specs['spots']
		#---in case spots refers to a local directory we use full paths
		for spotname in specs['spots']:
			specs['spots'][spotname]['route_to_data'] = re.sub(
				'PROJECT_NAME',connection_name,os.path.abspath(specs['spots'][spotname]['route_to_data']))
		#---final substitutions so PROJECT_NAME can be used anywhere
		with open(os.path.join(specs['calc'],'paths.yaml'),'w') as fp: 
			fp.write(re.sub('PROJECT_NAME',connection_name,yaml.dump(default_paths)))
		
		#---previous omnicalc users may have a specific gromacs.py that they wish to use
		if 'omni_gromacs_config' in specs and specs['omni_gromacs_config']:
			gromacs_fn = os.path.abspath(os.path.expanduser(specs['omni_gromacs_config']))
			shutil.copyfile(gromacs_fn,specs['calc']+'/gromacs.py')

		#---refresh in case you added another spot
		print('[STATUS] running make in %s'%specs['calc'])
		if omnicalc_previous:
			subprocess.check_call('source env/bin/activate && make -s -C '+specs['calc']+' refresh',
				shell=True,executable='/bin/bash')
		#---assimilate old data if available
		subprocess.check_call('source env/bin/activate && make -s -C '+specs['calc']+' export_to_factory %s %s'%
			(connection_name,settings_paths['rootspot']+specs['site']),shell=True,executable='/bin/bash')
		print("[STATUS] got omnicalc errors? try git pull to stay current")

	#---prepare a vhost file
	conf = prepare_vhosts(os.getcwd(),connection_name,port=None if 'port' not in specs else specs['port'])
	with open('logs/vhost_%s.conf'%connection_name,'w') as fp: fp.write(conf)
	print("[STATUS] connected %s!"%connection_name)
	print("[STATUS] start with \"make run %s\""%connection_name)

	#---??? IS THIS IT ???

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
	#---read all connection files into one dictionary
	toc = read_connection(*connects)
	if name and name not in toc: raise Exception('cannot find projecte named "%s" in the connections'%name)
	#---which connections we want to make
	targets = [name] if name else toc.keys()
	#---loop over desired connections
	for project in targets: connect_single(project,**toc[project])

def run(name):
	"""
	Run a project.
	"""
	#---! some kinds of checks?
	bash('bash mill/run_project.sh %s'%name)

def shutdown(name):
	"""
	Shutdown a running server.
	"""
	#---! some kinds of checks? internalize this.
	bash('bash mill/shutdown.sh %s'%name)	
