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
	#---deprecated in favor of checking the log because public causes problems
	if False:
		call = subprocess.Popen('jupyter notebook list'.split(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		stdout,stderr = call.communicate()
		token_regex = r'\n(?:http.*?\/\?token=)(.*?)\s.*?(\/.+)\s'
		#---we add trailing slashes to paths to match the settings.FACTORY convention (all paths get trails)
		jupyters = dict([(os.path.join(j,''),i) for i,j in re.findall(token_regex,stdout)])	
		if settings.FACTORY in jupyters: return jupyters[settings.FACTORY]
		else: return 'TOKEN_ERROR'
	#---check the notebook log file to get the token
	with open('logs/notebook.%s'%settings.NAME) as fp: text = fp.read()
	token_regex = r'http:(?:.*?)\:(\d+)(?:\/\?token=)(.*?)\s.*?(?:\/.+)\s'
	jupyters_by_port = dict(re.findall(token_regex,text,re.M+re.DOTALL))
	if len(jupyters_by_port)!=1: 
		print(text)
		raise Exception('error figuring out jupyter token: %s'%jupyters_by_port)
	else: return jupyters_by_port.values()[0]

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
