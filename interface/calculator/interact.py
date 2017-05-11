#!/usr/bin/env python

"""
All interactions with omnicalc are here.
"""

import os,sys,json,re,subprocess,datetime,glob,pprint
import nbformat as nbf
from django.conf import settings

import sys
#---remote imports
sys.path.insert(0,os.path.join(settings.FACTORY,'mill'))
sys.path.insert(0,os.path.join(settings.CALC,'omni'))
from cluster import backrun
from base.store import picturedat
omnicalc = __import__('omnicalc')

def get_workspace():
	"""
	Get a fresh copy of the workspace. Called by the calculator index function.
	"""
	#---! prefer to set the meta_filter somewhere in the factory?
	work = omnicalc.WorkSpace(cwd=settings.CALC,do_slices=False,checkup=True)
	return work

def make_bootstrap_tree(spec,floor=None,level=None):
	"""
	Convert a nested dictionary to dictionary for JSON for bootstrap tree visualization.
	"""
	#---top level gets a number
	if not level: level = 0
	if level and floor and level>=floor: 
		yield({"text":re.sub("'",'\\"',str(spec))})
	else:
		for key,val in spec.items():
			if type(val)==dict: 
				yield({"text":key,"nodes":list(
					make_bootstrap_tree(val,level=level+1,floor=floor))})
			else: 
				#---! general way to handle non-dictionary items
				#---! note the try block is for printing postdat objects
				try: yield {"text":key,"nodes":[{"text":re.sub("'",'\\"',str(val.__dict__))}]}
				except: yield {"text":key,"nodes":[{"text":re.sub("'",'\\"',str(val))}]}

def get_notebook_token():
	"""
	See if there is a notebook server running for the factory.
	"""
	#---check the notebook log file to get the token
	with open('logs/notebook.%s'%settings.NAME) as fp: text = fp.read()
	token_regex = r'http:(?:.*?)\:(\d+)(?:\/\?token=)(.*?)\s.*?(?:\/.+)\s'
	jupyters_by_port = dict(re.findall(token_regex,text,re.M+re.DOTALL))
	if len(jupyters_by_port)!=1: 
		print(text)
		raise Exception('error figuring out jupyter token: %s'%jupyters_by_port)
	else: return jupyters_by_port.values()[0]

def export_notebook(plotname):
	"""
	Requires omnicalc to supply the header
	"""
	header_code = '\n'.join(["plotname = '%s'","#---factory header",
		"exec(open('../omni/base/header_ipynb.py').read())"])
	cwd = settings.CALC
	target = 'calcs/plot-%s.py'%plotname
	dest = 'calcs/plot-%s.ipynb'%plotname
	regex_splitter = r'(\n\#-*block:.*?\n)'
	regex_hashbang = r'^\#.*?\n(.+)$'
	#---all tabs are converted to spaces because Jupyter
	tab_width = 4
	#---make a new notebook
	nb = nbf.v4.new_notebook()
	#---read the target plotting script
	with open(os.path.join(cwd,target)) as fp: text = fp.read()
	#---write a title
	stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
	header_text = ("# %s\n"%plotname+"\n*an OMNICALC plot script*\n\nGenerated on `%s`. "+
		"Visit the [notebook server](/tree/calc/%s/calcs/) for other calculations.")%(stamp,settings.NAME)
	nb['cells'].append(nbf.v4.new_markdown_cell(header_text))
	#---write the header cell
	nb['cells'].append(nbf.v4.new_code_cell(header_code.strip()%plotname))
	#---write the remaining blocks with double-newlines demiting the cells
	text_no_hashbang = re.match(regex_hashbang,text,flags=re.M+re.DOTALL).group(1)
	#---split keeps the delimiters and we associate them with the trailing chunks
	chunks = re.split(regex_splitter,text_no_hashbang)
	chunks = [chunks[0]]+[chunks[i]+chunks[i+1] for i in range(1,len(chunks),2)]
	for chunk in chunks:
		nb['cells'].append(nbf.v4.new_code_cell(re.sub('\t',' '*tab_width,chunk.strip())))
	#---write the notebook
	with open(os.path.join(cwd,dest),'w') as fp: nbf.write(nb,fp)

class FactoryBackrun:

	"""
	Run a computation in the background and keep track of the logs.
	"""

	def __init__(self):
		#---several hard-coded parameters for this background-runner
		self.lock_fn = 'pid.%s.compute.lock'%settings.NAME
		self.lock_fn_abs = os.path.join(settings.FACTORY,settings.CALC,self.lock_fn)
		self.cwd = settings.CALC
		self.state = 'idle'
		self.log_fn = None

	def run(self,cmd,log):
		"""
		Generic computation which uses the logging functionality.
		Used for `make compute` and the thumbnailer.
		"""
		self.avail()
		self.log_fn = log
		backrun(cmd='%s kill_switch="%s"'%(cmd,self.lock_fn_abs),log=self.log_fn,stopper=self.lock_fn_abs,
			cwd=self.cwd,killsig='KILL',scripted=False,kill_switch_coda='rm %s'%self.lock_fn_abs)
		self.log_fn_abs = os.path.join(self.cwd,self.log_fn)
		self.state = 'running'

	def avail(self):
		"""Make sure we are not running."""
		if self.state!='idle':
			raise Exception(
				'cannot complete run request because we are running.'+
				' go back, hit "reset calculation" and try again.')

	def dispatch_log(self):
		"""
		Populate a view with variables that descripte the logging state.
		"""
		outgoing = dict()
		outgoing['show_console'] = self.state in ['running','completed']
		if outgoing['show_console']:
			self.read_log()
			outgoing['log_text'] = self.last_log_text
			outgoing['log_status'] = self.state
		return outgoing

	def read_log(self):
		"""Read the log file."""
		with open(self.log_fn_abs) as fp: self.last_log_text = fp.read()

	def logstate(self):
		"""
		Describe the logging status for the logging function that interacts with the console.
		Note that the lock file exists when the job is running.
		The backrun function clears the lock file at the end of the run.
		"""
		#---idle returns nothing and tells the logger to redirect to index and close the AJAX calls
		if self.state == 'idle': return None
		#---if we are running we get the text of the log file
		elif self.state == 'running': 
			self.read_log()
			#---if the lock file is missing, we change our state to completed 
			if not os.path.isfile(self.lock_fn_abs): self.state = 'completed'
		#---return the log text
		return {'line':self.last_log_text,'running':self.state in ['running','completed'],
			'calculator_status':self.state}

class PictureAlbum:

	"""
	Manage the factory view of the plots.
	"""

	def __init__(self,backrunner):

		"""Prepare an album of plots. This includes thumbnails."""
		#---check for a thumbnails directory
		thumbnails_subdn = 'thumbnails-factory'
		thumbnails_dn = os.path.join(settings.PLOT,thumbnails_subdn)
		if not os.path.isdir(thumbnails_dn): os.mkdir(thumbnails_dn)
		#---catalog top-level categories
		picture_files = glob.glob(os.path.join(settings.PLOT,'*.png'))
		cats,picture_files_filter = [],[]
		for fn in picture_files:
			try: 
				cats.append(re.match('^fig\.(.*?)\.',os.path.basename(fn)).group(1))
				picture_files_filter.append(fn)
			except: print('[WARNING] wonky picture %s'%fn)
		cats = list(set(cats))

		#---reconstruct the plot_details every time
		plots_details = {}
		#---! other plot formats?
		#---scan for all PNG files
		for fn in picture_files_filter:
			base_fn = os.path.basename(fn)
			details = {'fn':base_fn}
			#---check for thumbnails
			thumbnail_fn = os.path.join(thumbnails_dn,base_fn)
			details['thumb'] = os.path.isfile(thumbnail_fn)
			#---construct a minimal descriptor of the plot from the name only
			try: shortname = re.sub('[._]','-',re.match('^fig\.(.*)\.png$',base_fn).group(1))
			except: shortname = re.match('^(.*?)\.png$',base_fn).group(1)
			details['shortname'] = shortname
			try:
				meta_text = picturedat(base_fn,directory=settings.PLOT)
				details['meta'] = pprint.pformat(meta_text,width=80) if meta_text else None
			except: details['meta'] = None
			#---a unique key for HTML elements
			details['ukey'] = re.sub('\.','_',base_fn)
			#---category for showing many pictures at once
			#---! note repetitive with the catalog of top-level categories above
			details['cat'] = re.match('^fig\.(.*?)\.',os.path.basename(base_fn)).group(1)
			plots_details[base_fn] = details

		#---package the data into the global album which gets shipped out to the view
		self.album = dict(files=dict([(k,plots_details[k]) for k in plots_details.keys()[:]]),
			thumbnail_dn_base=thumbnails_subdn,thumbnail_dn_abs=thumbnails_dn,cats=sorted(cats))

		#---make thumbnails if necessary
		if any([v['thumb']==False for k,v in plots_details.items()]): self.thumbnail_maker(backrunner)

	def thumbnail_maker(self,backrunner):
		"""
		Construct a script to make thumbnails.
		"""
		global album
		cwd = settings.CALC
		lines = ['#!/bin/bash']
		thumbnails_dn = self.album['thumbnail_dn_abs']
		for ii,(name,item) in enumerate(self.album['files'].items()):
			if not item['thumb']:
				source_fn = os.path.join(settings.PLOT,name)
				thumbnail_fn = os.path.join(thumbnails_dn,name)
				lines.append('echo "[STATUS] converting %s"'%os.path.basename(thumbnail_fn))
				lines.append('convert %s -thumbnail 500x500 %s'%(source_fn,thumbnail_fn))
				#---! should we update here assuming that it is made correctly?
				self.album['files'][name]['thumb'] = thumbnail_fn 
		lines.append('echo "[STATUS] THUMBNAILS COMPLETE you may need to wait for them or refresh"')
		with open(os.path.join(settings.CALC,'script-make-thumbnails.sh'),'w') as fp:
			fp.write('\n'.join(lines))
		global logging_fn
		logging_fn = os.path.join(settings.FACTORY,settings.CALC,'log-thumbnails')
		backrunner.run(cmd='bash script-make-thumbnails.sh',log='log-thumbnails')

class FactoryWorkspace:

	"""
	Wrap an omnicalc workspace for the factory.
	"""

	def __init__(self):
		"""Hold a copy of the workspace."""
		self.refresh()

	def refresh(self):
		"""Get another copy of the workspace. This reimports all data but does not run a calculation."""
		self.work = omnicalc.WorkSpace(cwd=settings.CALC,do_slices=False,checkup=True)
		self.time = datetime.datetime.now()

	def meta_changed(self):
		"""Check meta files for changes so you can tell the user a refresh may be in order."""
		mtimes = [os.path.getmtime(i) for i in self.work.specs_files]
		found_meta_changes = any([self.time<datetime.datetime.fromtimestamp(os.path.getmtime(i)) 
			for i in self.work.specs_files])
		return found_meta_changes

	def timestamp(self):
		"""Return the timestamp of the latest refresh."""
		return self.time.strftime('%Y.%m.%d %H:%M.%S')
