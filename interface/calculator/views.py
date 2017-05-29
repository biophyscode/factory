from django.http import HttpResponse,HttpResponseRedirect
from django.shortcuts import render,get_object_or_404
from django.template import loader
from django.core.urlresolvers import reverse
from django.conf import settings
from django.http import JsonResponse
from .models import *

from interact import make_bootstrap_tree,get_notebook_token,export_notebook
from interact import FactoryWorkspace,PictureAlbum,FactoryBackrun
from tools import bash

import os,json,re,datetime,time,glob,pprint

#---shared global variables to prevent lags
shared_work = None
shared_album = None
shared_backrun = None
notebook_token = None

###---START WORKSPACE TILES

def make_tree_postdat(outgoing):
	"""Present post-processing data as a tree for the index."""
	global shared_work
	#---collect posts by basename, excluding the numbered part of the filenames
	try: posts = shared_work.work.postdat.posts()
	except:
		return HttpResponse(str(shared_work))
	base_names = sorted(set(map(lambda x:re.match('^(.*?)\.n',x).group(1),posts.keys())))
	short_names = sorted(set([v.specs['slice']['short_name'] for k,v in posts.items()]))
	posts_restruct = {}
	for sn in short_names:
		keys = [p for p,v in posts.items() if v.specs['slice']['short_name']==sn]
		base_names = sorted(set(map(lambda x:re.match('^(.*?)\.n',x).group(1),keys)))
		#---! note that we might also want to organize the postdata by short_name
		posts_restruct[sn] = dict([(b,
			dict([(k,posts[pname]) for k in 
			[pname for pname in posts.keys() if re.match('^%s'%b,pname)]
			])) for b in base_names])
	posts_tree = json.dumps(list(make_bootstrap_tree(posts_restruct,floor=2)))
	outgoing['trees']['posts'] = {'title':'postprocessing data',
		'name':'posts','name_tree':'posts_tree','data':posts_tree}

def make_tree_slices(outgoing):
	"""Make a slices tree."""
	global shared_work
	if shared_work.work.slices: slices_tree = json.dumps(
		list(make_bootstrap_tree(shared_work.work.slices,floor=3)))
	else: slices_tree = json.dumps({})
	outgoing['trees']['slices'] = {'title':'slices',
		'name':'slices','name_tree':'slices_tree','data':slices_tree}

def make_tree_calculations(outgoing):
	"""Expose workspace calculations as a tree."""
	global shared_work
	if shared_work.work.calcs:
		calcs_tree_raw = list(make_bootstrap_tree(shared_work.work.calcs,floor=1))
	else: calcs_tree_raw = []
	for cc,c in enumerate(calcs_tree_raw): calcs_tree_raw[cc]['href'] = 'get_code/%s'%c['text']
	calcs_tree = json.dumps(calcs_tree_raw)
	outgoing['trees']['calcs'] = {'title':'calculations',
		'name':'calcs','name_tree':'calcs_tree','data':calcs_tree}

def make_tree_plots(outgoing):
	"""Present plots as a tree."""
	global shared_work
	plots_tree_raw = list(make_bootstrap_tree(shared_work.work.plots,floor=1))
	for cc,c in enumerate(plots_tree_raw): 
		plots_tree_raw[cc]['href'] = 'get_code/plot-%s'%c['text']
	plots_tree = json.dumps(plots_tree_raw)
	outgoing['trees']['plots'] = {'title':'plots',
		'name':'plots','name_tree':'plots_tree','data':plots_tree}

def make_tree_tasks(outgoing):
	"""Present pending tasks as a tree."""
	global shared_work
	tasks_details = {}
	for name,task in shared_work.work.tasks:
		calc_name = task['post'].specs['calc']['calc_name']
		if calc_name not in tasks_details: tasks_details[calc_name] = {}
		sn = task['job'].sn
		tasks_details[calc_name][sn] = {
			'slice':task['job'].slice.__dict__,'calc':task['job'].calc.__dict__}
	tasks_tree_raw = list(make_bootstrap_tree(tasks_details,floor=3))
	for cc,c in enumerate(tasks_tree_raw):
		tasks_tree_raw[cc]['href'] = 'get_code/%s'%c['text']
	tasks_tree = json.dumps(tasks_tree_raw)
	outgoing['trees']['tasks'] = {'title':'pending calculations',
		'name':'tasks','name_tree':'tasks_tree','data':tasks_tree}

def make_tree_meta_files(outgoing):
	"""Make a list of meta files as a tree with links to edit the files."""
	global shared_work
	#---get meta files
	meta_files_rel = dict([(os.path.basename(k),os.path.relpath(k,os.path.join(os.getcwd(),settings.CALC))) 
		for k in shared_work.work.specs_files])
	meta_files_raw = list(make_bootstrap_tree(meta_files_rel,floor=1))
	calc_rel_dn = os.path.relpath(settings.CALC,os.getcwd())
	for cc,c in enumerate(meta_files_raw):
		meta_files_raw[cc]['href'] = 'http://%s:%s/%s?token=%s'%(
			settings.NOTEBOOK_IP,settings.NOTEBOOK_PORT,'/'.join([
			'edit',calc_rel_dn,meta_files_rel[c['text']]]),notebook_token)
	meta_files_tree = json.dumps(meta_files_raw)
	outgoing['trees']['meta_files'] = {'title':'meta files',
		'name':'meta_files','name_tree':'meta_files_tree','data':meta_files_tree}

def make_warn_missings(outgoing):
	"""Warn the user if items are missing from meta."""
	global shared_work
	#---! note that this should be modified so it is more elegant
	outgoing.update(missings=', '.join([i for i in 
		'slices calcs plots'.split() if not shared_work.work.__dict__[i]]))

###---END WORKSPACE TILES

def index(request,pictures=True,workspace=True):
	"""
	Simulator index shows: simulations, start button.
	"""
	#---HTML sends back the status of visible elements so their visibility state does not change
	#---! needs replaced
	workspace = request.GET.get('workspace',
		{True:'true',False:'false','true':'true','false':'false'}[workspace])
	pictures = request.GET.get('pictures',
		{True:'true',False:'false','true':'true','false':'false'}[pictures])
	#---after this point workspace and picture flags are text
	#---send out variables that tell the HTML whether different elements (e.g. pictures) are visible
	outgoing = {'trees':{},'workspace_visible':workspace,
		'pictures_visible':pictures,'show_workspace_toggles':workspace=='true'}
	#---! deprecated: global work,workspace_timestamp,notebook_token,logging_state,logging_text,plotdat
	global shared_work,shared_album,shared_backrun,notebook_token
	#---get the notebook token once and hold it in memory
	if not notebook_token: notebook_token = get_notebook_token()
	if not shared_backrun: shared_backrun = FactoryBackrun()
	outgoing.update(notebook_token=notebook_token)
	#---workspace view includes tiles that mirror the main items in the omnicalc workspace
	if workspace=='true':
		#---on the first visit we make the workspace
		if not shared_work: shared_work = FactoryWorkspace()
		#---BEGIN POPULATING "outgoing"
		outgoing['found_meta_changes'] = shared_work.meta_changed()
		outgoing['workspace_timestamp'] = shared_work.timestamp()
		make_tree_postdat(outgoing)
		make_tree_slices(outgoing)
		make_tree_calculations(outgoing)
		make_tree_plots(outgoing)
		#---! currently testing on actinlink
		try: make_tree_tasks(outgoing)
		except: pass
		make_warn_missings(outgoing)
		make_tree_meta_files(outgoing)
		#---END POPULATING "outgoing"
		#---! use update method above instead of passing around the outgoing ...
		#---dispatch logging data
		outgoing.update(**shared_backrun.dispatch_log())
	#---if pictures are included in this view we send the album
	if pictures=='true':
		#---prepare pictures
		if not shared_album: shared_album = PictureAlbum(backrunner=shared_backrun)
		outgoing.update(album=shared_album.album)
	return render(request,'calculator/index.html',outgoing)

def refresh(request):
	"""Refresh the workspace and redirect to the calculator."""
	shared_work.refresh()
	return view_redirector(request)

def get_code(request,name):
	"""Retrieve a calculation code."""
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
	Redirect to the ipython notebook make function.
	"""
	plotname = re.match('^plot-(.+)',name).group(1)
	#---extract the name by convention here
	export_notebook(plotname)
	#---naming convention on the redirect
	return HttpResponseRedirect(reverse('calculator:get_code',kwargs={'name':name}))

def view_redirector(request):
	"""
	Redirect to the index while retaining the workspace and pictures flags.
	This helps ensure that going to "workspace only" hides the pictures when you do other things.
	"""
	return HttpResponseRedirect(reverse('calculator:index',
		kwargs={'workspace':request.GET.get('workspace','true'),
		'pictures':request.GET.get('pictures','true')}))

def compute(request):
	"""Run a compute request and redirect."""
	global shared_backrun
	#---dev purposes only: in case you go right to compute
	if not shared_backrun: shared_backrun = FactoryBackrun()
	cmd = 'make compute'
	#---use the backrun instance to run make compute. note that this protects against simultaneous runs
	print('[STATUS] running `%s`'%cmd)
	shared_backrun.run(cmd=cmd,log='log-compute')
	return view_redirector(request)

def logging(request):
	"""Serve logging requests from AJAX to the console."""
	global shared_backrun
	logstate = shared_backrun.logstate()
	if logstate: return JsonResponse(logstate)
	else: HttpResponseRedirect(reverse('calculator:index'))

def logging_false(request):
	"""
	Report on a running simulation if one exists.
	Note that getting teh status of the simulation automatically provides the filename for the running
	job's log file. Hence we send the log file as a signal to monitor things, then send it back through
	the URL so that the sim_console function (me) needs only to pipe it back to the page. This is 
	way more elegant than using this function to request the file, since we already have it in the detail
	function.
	"""
	global logging_lock,logging_state,logging_text
	#---if the lock file exists and the logging_lock is set then we update the AJAX console
	if logging_state in 'running' and os.path.isfile(logging_lock):
		#---read the log and return
		with open(logging_fn) as fp: logging_text = fp.read()
		return JsonResponse({'line':logging_text,'running':True})
	elif logging_state in 'running' and not os.path.isfile(logging_lock):
		#---return the final json response and turn off the logging_lock so the AJAX calls stop
		logging_lock = False
		logging_state = 'completed'
		#---read the log and return
		with open(logging_fn) as fp: logging_text = fp.read()
		return JsonResponse({'line':logging_text,'running':False})
	elif logging_state in 'idle': 
		return HttpResponseRedirect(reverse('calculator:index'))
		return JsonResponse({'line':'computer is idle','running':True})
	else: return JsonResponse({'line':'logging_state %s'%logging_state,'running':True})

def clear_logging(request):
	"""Turn off logging and hide the console."""
	global shared_backrun
	shared_backrun.state = 'idle'
	return view_redirector(request)
