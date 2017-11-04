#!/usr/bin/env python

from django.conf import settings
from django.http import HttpResponse,HttpResponseRedirect
from django.core.urlresolvers import reverse
from tools import bash
from .models import Kickstart,Simulation

import json,datetime,shutil

"""
INTERACTIONS WITH AUTOMACS
"""

import os,sys,re

def prepare_simulation(sim):
	"""
	Prepare a simulation given an incomplete row.
	"""
	if os.path.isfile(settings.SIMSPOT+sim.path): 
		return HttpResponse('control failure: path exists: %s'%settings.SIMSPOT+sim.path)
	branch = ' -b %s '%settings.AUTOMACS_BRANCH if hasattr(settings,'AUTOMACS_BRANCH') else ''
	bash('git clone %s %s%s'%(settings.AUTOMACS,branch,sim.path),cwd=settings.SIMSPOT)
	#---always run make after clone otherwise config.py is absent. we have to catch or bash error.
	bash('make',cwd=settings.SIMSPOT+sim.path,catch=True)
	#---copy a user-supplied gromacs_config.py if one is available
	if settings.GROMACS_CONFIG:
		#---use the expected name for the local config
		shutil.copyfile(settings.GROMACS_CONFIG,os.path.join(settings.SIMSPOT,sim.path,'gromacs_config.py'))
	elif not os.path.isfile(os.path.expanduser('~/.automacs.py')):
		#---if no global config, then we write one. this only happens once
		#---users who wish to customize the runs should edit ~/.automacs.py OR set an explicit gromacs_config
		#---...key in the connect file which should point to a local copy of the .automacs.py
		bash('make gromacs_config home',cwd=settings.SIMSPOT+sim.path,catch=True)
	sim.save()

def make_setup(req,id_sim,id_kick):
	"""
	Run `make setup` in automacs to update and clone new modules.
	"""
	#---get the kickstarter name from the id
	kick = Kickstart.objects.get(id=id_kick)
	sim = Simulation.objects.get(id=id_sim)
	#---note that we run the setup command without checking the text. this assumes the Kickstart
	#---...table exactly matches the objects in the automacs amx.kickstarts module
	print('[STATUS] running `make setup %s`'%kick.name)
	#---! getting mysterious bash errors here?
	bash('make setup %s'%kick.name,cwd=settings.SIMSPOT+sim.path)
	#---update the kickstart flag in the simulation. this is irreversible; it prevents further kickstarting
	sim.kickstart = kick.name
	sim.status = 'kickstarted'
	sim.save()
	return HttpResponseRedirect(reverse('simulator:detail_simulation',kwargs={'id':id_sim}))

def make_prep(req,id_sim,expt_name):
	"""
	Run `make prep`. Automatically cleans so be careful!
	"""
	sim = Simulation.objects.get(id=id_sim)
	bash('make clean sure && make prep %s'%expt_name,cwd=settings.SIMSPOT+sim.path)
	#---update the experiment name in the simulation. this is irreversible
	sim.experiment = expt_name
	sim.status = 'selected_expt'
	sim.save()
	return HttpResponseRedirect(reverse('simulator:detail_simulation',kwargs={'id':id_sim}))

def make_run(expt,cwd):
	"""
	Prepare a run.
	"""
	#---! the target, expt.json, is hard-coded
	expt_fn = 'expt.json'
	#---read the expt.json since we only want to replace the settings
	with open(os.path.join(settings.SIMSPOT,cwd,expt_fn)) as fp: expt_raw = json.loads(fp.read())
	#---reconstruct the settings so that it can be read by yamlb later on
	new_settings = '\n'.join(['%s: %s'%(key,val) for key,val in expt.items()])
	expt_raw.update(settings_overrides=new_settings)
	with open(os.path.join(settings.SIMSPOT,cwd,expt_fn),'w') as fp: fp.write(json.dumps(expt_raw))
	#---prepare the JSON request to the cluster
	script = '\n'.join(['make run'])
	req_text = json.dumps({'bash':script,'cwd':settings.SIMSPOT+cwd,
		'stopper':os.path.join(settings.SIMSPOT,cwd,'stop-job.sh')})
	#---factory has to assign a job name because the cluster is ambivalent
	stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
	stamp_base = 'simulator.%s'%stamp
	submit_fn = '%s.req'%stamp_base
	#---write the cluster submission script to the cluster folder
	with open(os.path.join(settings.CLUSTER,submit_fn),'w') as fp: fp.write(req_text)
	#---! repeat for posterity
	with open(os.path.join(settings.CLUSTER,submit_fn+'.sub'),'w') as fp: fp.write(req_text)
	#---return the stamp only
	return stamp_base

def make_metarun(expt,cwd):
	"""
	Prepare a meta run.
	"""
	#---process all new settings into JSON files
	keys = sorted(expt.keys(),key=lambda x:int(re.match('^settings, step (.+)$',x).group(1)))
	for knum,key in enumerate(keys):
		expt_fn = 'expt_%d.json'%(knum+1)
		#---read the expt.json since we only want to replace the settings
		with open(os.path.join(settings.SIMSPOT,cwd,expt_fn)) as fp: expt_raw = json.loads(fp.read())
		#---reconstruct the settings so that it can be read by yamlb later on
		new_settings = '\n'.join(['%s: %s'%(key,val) for key,val in expt[key].items()])
		expt_raw.update(settings_overrides=new_settings)
		with open(os.path.join(settings.SIMSPOT,cwd,expt_fn),'w') as fp: fp.write(json.dumps(expt_raw))
	#---prepare the JSON request to the cluster
	script = '\n'.join(['make metarun'])
	req_text = json.dumps({'bash':script,'cwd':settings.SIMSPOT+cwd,
		'stopper':os.path.join(settings.SIMSPOT,cwd,'stop-job.sh')})
	#---factory has to assign a job name because the cluster is ambivalent
	stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
	stamp_base = 'simulator.%s'%stamp
	submit_fn = '%s.req'%stamp_base
	#---write the cluster submission script to the cluster folder
	with open(os.path.join(settings.CLUSTER,submit_fn),'w') as fp: fp.write(req_text)
	#---! repeat for posterity
	with open(os.path.join(settings.CLUSTER,submit_fn+'.sub'),'w') as fp: fp.write(req_text)
	#---return the stamp only
	return stamp_base
