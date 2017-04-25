#!/usr/bin/env python

"""
All interactions with omnicalc are here.
"""

import os,sys,json,re,subprocess,datetime
import nbformat as nbf
from django.conf import settings

sys.path.insert(0,settings.CALC)
sys.path.insert(0,os.path.join(settings.CALC,'omni'))
omnicalc = __import__('omnicalc')

def get_workspace():
	"""
	Get a fresh copy of the workspace. Called by the calculator index function.
	"""
	#---! prefer to set the meta_filter somewhere in the factory?
	work = omnicalc.WorkSpace(cwd=settings.CALC)
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
	call = subprocess.Popen('jupyter notebook list'.split(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	stdout,stderr = call.communicate()
	token_regex = r'\n(?:http.*?\/\?token=)(.*?)\s.*?(\/.+)\s'
	#---we add trailing slashes to paths to match the settings.FACTORY convention (all paths get trails)
	jupyters = dict([(os.path.join(j,''),i) for i,j in re.findall(token_regex,stdout)])	
	if settings.FACTORY in jupyters: return jupyters[settings.FACTORY]
	else: return 'TOKEN_ERROR'

header_code = """
plotname = '%s'
#---factory header
exec(open('../omni/base/header_ipynb.py').read())
"""

def export_notebook(plotname):
	"""
	Requires omnicalc to supply the header
	"""
	cwd = settings.CALC
	target = 'calcs/plot-%s.py'%plotname
	dest = 'calcs/plot-%s.ipynb'%plotname
	regex_splitter = r'\n\#---cellblock\s*\n'
	regex_hashbang = r'^\#.*?\n(.+)$'
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
	for chunk in re.split(regex_splitter,re.match(regex_hashbang,text,flags=re.M+re.DOTALL).group(1)):
		nb['cells'].append(nbf.v4.new_code_cell(chunk.strip()))
	#---write the notebook
	with open(os.path.join(cwd,dest),'w') as fp: nbf.write(nb,fp)
