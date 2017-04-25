from django.http import HttpResponse,HttpResponseRedirect
from django.shortcuts import render,get_object_or_404
from django.template import loader
from django.core.urlresolvers import reverse
from django.conf import settings
from django.http import JsonResponse
from .models import *
from interact import get_workspace,make_bootstrap_tree,get_notebook_token,export_notebook
from tools import bash

import os,json,re

#---get the notebook token once per run
#---! hence notebook restarts are not allowed or you would have to run that jupyter command to get a new one
notebook_token = None

def index(request):
	"""
	Simulator index shows: simulations, start button.
	"""
	outgoing = {}
	#---get the notebook token once and hold it in memory
	#---! IS THIS DJANGOTHONIC???
	global notebook_token
	if not notebook_token: notebook_token = get_notebook_token()
	outgoing.update(notebook_token=notebook_token)
	#---every index refresh gets the workspace again
	#---! we should try to use AJAX for minor updates?
	work = get_workspace()
	#---! DEV
	if hasattr(work,'postdat'):
		posts_tree = json.dumps(list(make_bootstrap_tree(work.postdat.posts(),floor=2)))
	if work.slices: slices_tree = json.dumps(list(make_bootstrap_tree(work.slices,floor=3)))
	#---get calculations and attach links
	if work.calcs:
		calcs_tree_raw = list(make_bootstrap_tree(work.calcs,floor=2))
		for cc,c in enumerate(calcs_tree_raw): calcs_tree_raw[cc]['href'] = 'get_code/%s'%c['text']
		calcs_tree = json.dumps(calcs_tree_raw)
		outgoing.update(posts_tree=posts_tree,slices_tree=slices_tree,calcs_tree=calcs_tree)
	#---get plots and attach links
	if work.plots:
		plots_tree_raw = list(make_bootstrap_tree(work.plots,floor=2))
		for cc,c in enumerate(plots_tree_raw): plots_tree_raw[cc]['href'] = 'get_code/plot-%s'%c['text']
		plots_tree = json.dumps(plots_tree_raw)
		outgoing.update(plots_tree=plots_tree)
	outgoing.update(missings=', '.join([i for i in 'slices calcs plots'.split() if not work.__dict__[i]]))
	return render(request,'calculator/index.html',outgoing)

def get_code(request,name):
	"""
	"""
	global notebook_token
	if not notebook_token: notebook_token = get_notebook_token()
	outgoing = dict(plotname=name,notebook_token=notebook_token)
	#---retrieve the raw code
	path = os.path.join(settings.CALC,'calcs','%s.py'%name)
	with open(path) as fp: raw_code = fp.read()
	outgoing.update(raw_code=raw_code,path=os.path.basename(path))
	#---detect an ipynb versions
	if re.match('^plot-(.+)',name):
		note_fn = os.path.relpath(os.path.join(settings.CALC,'calcs','%s.ipynb'%name),settings.FACTORY)
		if os.path.isfile(note_fn): outgoing.update(calc_notebook=os.path.basename(note_fn))
		else: outgoing.update(calc_notebook_make='MAKE')
	return render(request,'calculator/codeview.html',outgoing)

def make_notebook(request,name):
	"""
	"""
	plotname = re.match('^plot-(.+)',name).group(1)
	#---extract the name by convention here
	export_notebook(plotname)
	#---naming convention on the redirect
	return HttpResponseRedirect(reverse('calculator:get_code',kwargs={'name':name}))