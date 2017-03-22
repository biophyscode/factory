from django.shortcuts import render,get_object_or_404
from django.conf import settings
from django.http import HttpResponseNotFound,HttpResponse,HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.http import JsonResponse
from simulator.models import *
from .forms import *
from .tasks import sherpacalc
from PIL import Image
import json,os,glob,re,time,subprocess
import yaml

def deep_hash_to_text(d,**kwargs):

	"""
	Turn nested dictionaries into a block of text.
	"""

	spacer = kwargs.get('spacer',' ')
	lines = kwargs.get('lines',[])
	indent = kwargs.get('indent',0)
	for key,value in d.iteritems():
		lines.append(spacer*indent+str(key))
		if isinstance(value,dict): deep_hash_to_text(value,indent=indent+1,lines=lines,spacer=spacer)
		else: lines.append(spacer*(indent+1)+str(value))
	return '\n'.join(lines)

def collect_images():

	"""
	Collect the names of all images in the plot directory and read their metadata.
	"""

	image_fns = [os.path.basename(fn) for fn in glob.glob(settings.PLOTSPOT+'/*.png')]
	print image_fns
	try:
		names_path_meta = [(
			re.sub('_',' ',re.findall('^fig\.([^\.]+)\.',fn)[0]),fn,
			eval(Image.open(settings.PLOTSPOT+'/'+fn).info['meta']) 
			if 'meta' in Image.open(settings.PLOTSPOT+'/'+fn).info else {}) for fn in image_fns
			if re.match('^fig\.([^\.]+)\.',fn)]
		image_fns_gif = [(os.path.basename(fn),os.path.basename(fn),{}) 
			for fn in glob.glob(settings.PLOTSPOT+'/*.gif')]
		return names_path_meta+image_fns_gif
	except: return []
	
def refresh_thumbnails(request,remake=False):

	"""
	Create or update thumbnails so the views load faster in case of enormous image files.
	This always makes the files that are missing.
	"""	

	root = settings.PLOTSPOT+'/'
	if not os.path.isdir(root+'/thumbs'): os.mkdir(root+'/thumbs')
	image_fns = collect_images()
	if image_fns == []: return HttpResponseRedirect(reverse('calculator:index'))
	for name,fn,meta in image_fns:
		thumbfile = os.path.dirname(root+fn)+'/thumbs/'+os.path.basename(root+fn)
		if not os.path.isfile(thumbfile) or remake:
			os.system('convert %s -thumbnail 500x500 %s'%(root+fn,thumbfile))
	#---wait for thumbs to refresh on disk if we remade them
	if remake: time.sleep(5)
	#---! need to refresh the page manually after refreshing the thumbnails for some reason
	#---! previously used ignore=time.time() to send a random number but not sure if this is necessary
	return HttpResponseRedirect(reverse('calculator:index_ignore',kwargs={'ignore':0}))
	
def index(request,collection_id=-1,group_id=-1,calculation_id=-1,
	update_group=False,update_collection=False,update_calculation=False,ignore=0):

	"""
	Show a set of calculations.
	"""

	if request.method == 'GET': 
		if group_id == -1: form_group = group_form(prefix='group_form')
		else: 
			group = Group.objects.get(pk=group_id)
			form_group = group_form(instance=group,prefix='group_form')	
			form_group.fields['name'].widget.attrs['readonly'] = True
		if collection_id == -1: form_collection = collection_form(prefix='collection_form')
		else: 
			collection = Collection.objects.get(pk=collection_id)
			form_collection = collection_form(instance=collection,prefix='collection_form')	
		if calculation_id == -1: form_calculation = calculation_form(prefix='calculation_form')
		else: 
			calculation = Calculation.objects.get(pk=calculation_id)
			form_calculation = calculation_form(instance=calculation,prefix='calculation_form')	
			form_calculation.fields['name'].widget.attrs['readonly'] = True
		form_slice = slice_form(prefix='slice_form')
	else:
		#---create a new collection
		if request.path == '/calculator/new_collection':
			form_slice = slice_form(prefix='slice_form')
			form_collection = collection_form(request.POST,request.FILES,prefix='collection_form')
			form_group = group_form(prefix='group_form')
			form_calculation = calculation_form(prefix='calculation_form')
			if form_collection.is_valid():
				#---crucial to note that you cannot do commit=False and save on the next line
				#---...when you have 
				new_collection = form_collection.save()
				return HttpResponseRedirect(reverse('calculator:index'))
		#---create a new group
		elif request.path == '/calculator/new_group':
			form_slice = slice_form(prefix='slice_form')
			form_collection = collection_form(prefix='collection_form')
			form_group = group_form(request.POST,request.FILES,prefix='group_form')
			form_calculation = calculation_form(prefix='calculation_form')
			if form_group.is_valid():
				new_group = form_group.save(commit=False)
				new_group.save()
				return HttpResponseRedirect(reverse('calculator:index'))
		#---create a new slice
		elif request.path == '/calculator/new_slice':
			form_slice = slice_form(request.POST,request.FILES,prefix='slice_form')
			form_collection = collection_form(prefix='collection_form')
			form_group = group_form(prefix='group_form')
			form_calculation = calculation_form(prefix='calculation_form')
			if form_slice.is_valid():
				slice_name = form_slice.cleaned_data['name']
				#---get the desired collections and make a new slice for each simulation in each collection
				if 'collections' in form_slice.cleaned_data:
					for collection_pk in form_slice.cleaned_data['collections']:
						for sim in Collection.objects.get(pk=collection_pk).simulations.all():
							#---make a new row in the slices table
							new_slice,created = Slice.objects.update_or_create(
								name=slice_name,
								simulation=sim,
								start=form_slice.cleaned_data['start'],
								end=form_slice.cleaned_data['end'],
								skip=form_slice.cleaned_data['skip'])
							for g in form_slice.cleaned_data['groups']: new_slice.groups.add(g)
							new_slice.save()
				return HttpResponseRedirect(reverse('calculator:index'))
		#---create a new calculation
		elif request.path == '/calculator/new_calculation':
			form_slice = slice_form(prefix='slice_form')
			form_collection = collection_form(prefix='collection_form')
			form_group = group_form(prefix='group_form')
			form_calculation = calculation_form(request.POST,request.FILES,prefix='calculation_form')
			if form_calculation.is_valid():
				new_calculation = form_calculation.save()
				return HttpResponseRedirect(reverse('calculator:index'))
		#---update a group
		elif update_group:
			group = Group.objects.get(pk=group_id)
			form_slice = slice_form(prefix='slice_form')
			form_collection = collection_form(prefix='collection_form')
			form_calculation = calculation_form(prefix='calculation_form')
			form_group = group_form(data=request.POST,instance=group,prefix='group_form')
			if form_group.is_valid():
				#---! note that we tried commit=False and later new_group.save() and it didn't update 
				new_group = form_group.save()
				return HttpResponseRedirect(reverse('calculator:index'))
		#---update a collection
		elif update_collection:
			collection = Collection.objects.get(pk=collection_id)
			form_slice = slice_form(prefix='slice_form')
			form_collection = collection_form(data=request.POST,instance=collection,prefix='collection_form')
			form_group = group_form(prefix='group_form')
			form_calculation = calculation_form(prefix='calculation_form')
			if form_collection.is_valid():
				new_collection = form_collection.save()
				return HttpResponseRedirect(reverse('calculator:index'))
		#---update a calculation
		elif update_calculation:
			calculation = Calculation.objects.get(pk=calculation_id)
			form_slice = slice_form(prefix='slice_form')
			form_collection = collection_form(prefix='collection_form')
			form_group = group_form(prefix='group_form')
			form_calculation = calculation_form(data=request.POST,instance=calculation,
				prefix='calculation_form')
			if form_calculation.is_valid():
				new_calculation = form_calculation.save()
				return HttpResponseRedirect(reverse('calculator:index'))
		else: raise Exception('unclear incoming path to the index.html page')
	refresh_thumbnails(request)
	image_fns = collect_images()
	#---collect codes
	code_fns = []
	for root,dns,fns in os.walk(os.path.join(settings.ROOTSPOT,settings.CALCSPOT,'calcs','')): 
		for fn in fns:
			if re.match('^.+[^_]\.py$',fn):
				code_fns.append((fn,os.path.join(root,fn)))
	outgoing = {
		'image_fns':image_fns,
		'simulations':Simulation.objects.all().order_by('id'),
		'collections':Collection.objects.all().order_by('id'),
		'collection_form':form_collection,
		'groups':Group.objects.all().order_by('id'),
		'calculations':Calculation.objects.all().order_by('id'),
		'group_form':form_group,
		'selected_group':-1 if group_id==-1 else Group.objects.get(pk=group_id),
		'selected_collection':-1 if collection_id==-1 else Collection.objects.get(pk=collection_id),
		'selected_calculation':-1 if calculation_id==-1 else Calculation.objects.get(pk=calculation_id),
		'slice_form':form_slice,
		'running_calculations':BackgroundCalc.objects.all().order_by('id'),
		'calculation_form':form_calculation,
		'slice_form_doc':form_slice.__doc__,
		'code_fns':code_fns,
		'CELERYPORT':settings.CELERYPORT,
		}
	modifier = ['','_original'][0]
	rendered = render_to_string('calculator/index%s.html'%modifier,outgoing)
	return render(request,'calculator/index%s.html'%modifier,outgoing)

def refresh_times(request):

	"""
	Check on the duration of a simulation.
	"""
	
	proc = subprocess.Popen('make refresh',cwd=settings.CALCSPOT,
		shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	proc.communicate()
	for sim in Simulation.objects.all():
		sn = sim.code	
		miniscript = ';'.join([
			"python -c \"execfile('./omni/base/header.py')",
			"print '>>>'+str(work.get_timeseries('%s'))\"",
			])
		proc = subprocess.Popen(miniscript%sn,cwd=settings.CALCSPOT,
			shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		catch = proc.communicate()
		try: 
			regex = '^>>>(.+)$'
			selected, = [re.findall(regex,i)[0] for i in ('\n'.join(catch)).split('\n') if re.match(regex,i)]
			timeseq = eval(selected)
			startstop = min([i[-1][0] for i in timeseq]),max([i[-1][1] for i in timeseq])
			sim.time_sequence = '-'.join(['%.f'%(i/1.0) for i in startstop])
			sim.save()
		except Exception as e: print "[ERROR] exception: %s"%e
	return HttpResponseRedirect(reverse('calculator:index'))

def view_settings(request):

	"""
	Show the settings for a particular instance of calculator.
	THIS APPEARS TO BE A DEAD END CONSIDER DELETING
	"""
	
	#---! hardcoded
	#projname = settings.PROJECT_NAME
	projname = 'ptdins'
	mplxr_basedir = '/home/localshare/analysis/mplxr/'

	with open(mplxr_basedir+'/calc/'+projname+'/gromacs.py') as fp: gromacs_settings = fp.read()
	with open(mplxr_basedir+'/calc/'+projname+'/paths.py') as fp: paths = fp.read()
	return render(request,'calculator/view_settings.html',
		{'gromacs_settings':gromacs_settings,'paths':paths,'rootdir':projname})
		
def detail_simulation(request,id):

	"""
	Detailed view of a simulation with tuneable parameters if the job is not yet submitted.
	URGENT NOTE: sim.dropspot IS DEPRECATED and was replaced with settings.DROPSPOT
	"""

	sim = get_object_or_404(Simulation,pk=id)
	outgoing = {'sim':sim}
	if request.method == 'GET': 
		form = group_form()
		outgoing['group_form'] = form
	else:
		#---write meta file with a new collection
		form = group_form(request.POST,request.FILES)
		if form.is_valid():
			new_collection = form.save(commit=False)
			new_collection.save()
			return HttpResponseRedirect(reverse('calculator:index'))
	return render(request,'calculator/detail.html',outgoing)

def detail_group(request,id):

	"""
	DEPRECATED?
	"""

	group = get_object_or_404(Group,pk=id)
	outgoing = {'group':group}
	if request.method == 'GET': 
		form_group = group_form(instance=group)
		outgoing['group_form'] = form_group
	else:
		form_group = group_form(data=request.POST,instance=group)
		outgoing['group_form'] = form_group
		if form_group.is_valid():
			#---! note that we tried commit=False and later new_group.save() and it didn't update 
			new_group = form_group.save()
			outgoing['collections'] = new_group.collection.all().order_by('id')
			return render(request,'calculator/detail_group.html',outgoing)
	outgoing['collections'] = group.collection.all().order_by('id')
	outgoing['show_collection'] = True
	return render(request,'calculator/detail_group.html',outgoing)

def compute(*args,**kwargs):

	"""
	Write the yaml file and run make compute.
	"""

	print "[STATUS] starting OMNICALC compute "
	#---prepare an a dictionary representing meta.yaml
	outgoing = {'slices':{},'collections':{}}
	for sl in Slice.objects.all():
		if sl.simulation.code not in outgoing['slices']: outgoing['slices'][sl.simulation.code] ={}
		if 'slices' not in outgoing['slices'][sl.simulation.code]: 
			outgoing['slices'][sl.simulation.code]['slices'] = {}
		outgoing['slices'][sl.simulation.code]['slices'][sl.name] = {
			'pbc':'mol','groups':[str(g.name) for g in sl.groups.all()],
			'start':int(sl.start),'end':int(sl.end),'skip':int(sl.skip),
			}
		if 'groups' not in outgoing['slices'][sl.simulation.code]: 
			outgoing['slices'][sl.simulation.code]['groups'] = {}			
		for grp in sl.groups.all():
			outgoing['slices'][sl.simulation.code]['groups'][grp.name] = grp.selection
	outgoing['meta'] = {}
	for sim in Simulation.objects.all():
		outgoing['meta'][sim.code] = {'name':sim.name}

	#---write collections
	for collect in Collection.objects.all():
		outgoing['collections'][collect.name] = [sim.code for sim in collect.simulations.all()]
	with open(settings.CALCSPOT+'/calcs/specs/meta.factory.slices.yaml','w') as fp:
		fp.write(yaml.safe_dump(outgoing))
	#---write calculations to a separate yaml file
	calcspecs = {'calculations':{},'plots':{}}
	for calc in Calculation.objects.all():
		calcspecs['calculations'][calc.name] = {
			'slice_name':calc.slice_name,
			'group':calc.group.name,
			'collections':[str(c.name) for c in calc.collections.all()],
			'uptype':calc.uptype,
			}
		calcspecs['plots'][calc.name] = {
			'slices':calc.slice_name,
			'calculation':[calc.name],
			'group':calc.group.name,
			'collections':[str(c.name) for c in calc.collections.all()],
			'uptype':calc.uptype,
			}

	with open(settings.CALCSPOT+'/calcs/specs/meta.factory.calculations.yaml','w') as fp:
		fp.write(yaml.safe_dump(calcspecs))			
	#---! consider adding make compute dry
	this_job = BackgroundCalc()
	this_job.save()
	sherpacalc.delay(this_job.id,autoreload=True,log='log',cwd=settings.CALCSPOT)

	return HttpResponseRedirect(reverse('calculator:index'))

def calculation_monitor(request):

	"""
	Report on a running calculation if one exists.
	"""

	monitor_div = '<div class="tile-col" style="height:200px;">'+\
		'<h3>running calculation</h3>%s</div>'
	#---only read if jobs are running otherwise ajax will remember the last text
	if any(BackgroundCalc.objects.all()):
		with open(settings.CALCSPOT+'/log') as fp: lines = fp.readlines()
		return JsonResponse({'line':'\n'.join([l.lstrip().rstrip() for l in lines]),'running':True})
	else: return JsonResponse({'line':'','running':False})

def view_code(request,path):

	"""
	Render a code to HTML.
	"""

	print "[STATUS] rendering code: %s"%path
	with open(path) as fp: code = fp.read()
	return render(request,'calculator/codeview.html',{'code':code,'path':path})

def slices_summary(request):

	"""
	Print a summary list of all slices.
	"""

	summary_text = '\n'.join([
		'slice name: %s simulation: %s times: %d-%d ps by %d ps'%(
			('"'+i.name+'"').ljust(20,'.'),
			('"'+i.simulation.name+'"').ljust(20,'.'),
			i.start,i.end,i.skip)
		for i in Slice.objects.all()])
	return render(request,'calculator/slices_summary.html',{'summary_text':summary_text})