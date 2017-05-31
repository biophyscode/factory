from django.http import HttpResponse,HttpResponseRedirect
from django.shortcuts import render,get_object_or_404
from django.template import loader
from django.core.urlresolvers import reverse
from django.conf import settings
from django.http import JsonResponse
from .forms import *
from .models import *
from interact import *
from tools import import_remote,yamlb
import os,json

#---! this is a useful tool. move it somewhere more prominent
#---dictionary lookups in templates e.g. "status_by_sim|get_item:sim.name"
from django.template.defaulttags import register
@register.filter
def get_item(dictionary,key): return dictionary.get(key)

#---fieldsets to organize the parts of a form
from django.forms.forms import BoundField
class FieldSet(object):
    def __init__(self,form,fields,legend='',cls=None,details=''):
        self.form = form
        self.legend = legend
        self.details = details
        self.fields = fields
        self.cls = cls
    def __iter__(self):
        for name in self.fields:
            field = self.form.fields[name]
            yield BoundField(self.form, field, name)

def index(request):
	"""
	Simulator index shows: simulations, start button.
	"""
	print(settings.GROMACS_CONFIG)
	sims = Simulation.objects.all().order_by('id')
	coords = Coordinates.objects.all().order_by('id')
	outgoing = dict(sims=sims,coords=coords)
	outgoing.update(root=settings.SIMSPOT)
	#---simulations by status
	statuses = job_status_infer()
	cluster_stat = dict([(stat_type,[{'name':name,'id':stat['id']} 
		for name,stat in statuses.items() if stat['stat']==stat_type])
		for stat_type in ['running','waiting','finished']])
	outgoing.update(cluster_stat=cluster_stat)
	statuses_by_sim = dict([(k,v['stat'] if v['stat'] else '???XXXX') for k,v in statuses.items()])
	outgoing.update(status_by_sim=statuses_by_sim)
	#---hide the cluster console unless some jobs are running
	if any(v=='running' for v in statuses_by_sim.values()): outgoing.update(cluster_running=True)

	if request.method == 'GET': 
		form = build_simulation_form()
		form_upload_coords = build_form_upload_coords()
		outgoing.update(form_sim_new=form,form_upload_coords=form_upload_coords)
		return render(request,'simulator/index.html',outgoing)
	#---if you end up here, it's because you are starting a simulation
	else:
		form = build_simulation_form(request.POST,request.FILES)
		#---note the following forms are empty because index POST handles simulatins
		form_upload_coords = build_form_upload_coords()
		outgoing.update(form_sim_new=form,form_upload_coords=form_upload_coords)
		#---index POST handles new simulations. other forms are routed to their respective functions
		if form.is_valid():
			sim = form.save(commit=False)
			sim.path = re.sub(' ','_',sim.name)
			sim.status = 'created'
			sim.save()
			prepare_simulation(sim)
			return HttpResponseRedirect(reverse('simulator:detail_simulation',kwargs={'id':sim.id}))
	return render(request,'simulator/index.html',outgoing)

def job_status_infer(sim=None):
	"""
	Look at the cluster to infer the job statuses.
	"""
	regex_submitted = '^submitted:(.+)$'
	#---if no stamp is supplied, we get them from simulation statuses
	if not sim: 
		sims = Simulation.objects.all().order_by('id')
		sims_submitted = [sim for sim in sims if re.match(regex_submitted,sim.status)]
		sims_stamps = dict([(sim.name,re.match(regex_submitted,sim.status).group(1)) 
			for sim in sims_submitted])
		sims_not_submitted = [sim for sim in sims if not re.match(regex_submitted,sim.status)]
	else: sims_submitted = [sim]
	#---infer the status of each job
	statuses = {}
	for sim in sims_submitted:
		if not re.match(regex_submitted,sim.status): continue
		job_status = 'idle'
		#---if the job is submitted we have to run this refresh block to infer its status
		#---! is inference the best option here, or should we track the jobs in the database?
		#---pop off the submission path
		submit_stamp = re.match('^submitted:(.+)$',sim.status).group(1)
		#---anticipate different names for the file depending on its job status
		for namer,form in settings.CLUSTER_NAMER.items():
			job_cluster_fn = os.path.join(settings.CLUSTER,re.sub('STAMP',submit_stamp,form))
			if os.path.isfile(job_cluster_fn):
				job_status = namer
				break
		statuses[sim.name] = {'stat':job_status,'stamp':submit_stamp,'fn':job_cluster_fn,'id':sim.id}
	for sim in sims_not_submitted:
		statuses[sim.name] = {'stat':'construction',
			'stamp':'no stamp yet','fn':'no job file yet','id':sim.id}
	return statuses

def detail_simulation(request,id):
	"""
	Detailed view of a simulation with tuneable parameters if the job is not yet submitted.
	"""
	sim = get_object_or_404(Simulation,pk=id)
	outgoing = dict(sim=sim)

	#---always show the config
	config = {}
	config = eval(open(os.path.join(settings.SIMSPOT,sim.path,'config.py')).read())
	outgoing.update(config=config)
	
	#---do we need to choose a kickstart?
	if sim.status=='created':
		#---load the kickstarts module from amx and update the Kickstart table
		mod = import_remote(os.path.join(settings.SIMSPOT,sim.path,'amx','kickstarts.py'))
		for key,val in mod['kickstarters'].items(): 
			Kickstart.objects.get_or_create(name=key,text=val.strip())
		kickstarts = Kickstart.objects.all().order_by('id')
		outgoing.update(kickstarts=kickstarts)

	#---get the preplist but only if we have kickstarted
	if sim.status=='kickstarted':
		preptext = bash('make prep_json',cwd=settings.SIMSPOT+sim.path,catch=True)
		expts = json.loads(re.search('^NOTE: (.*?)$',preptext['stdout'],flags=re.M).group(1))
		#---! currently only works for run
		for key in ['metarun','quick']: del expts[key]
		outgoing.update(expts=expts)

	#---after kickstart and prepping the experiment we are now ready to customize
	if sim.status=='selected_expt':
		#---options above instantiated by links and refreshes. below we use forms
		if request.method=='GET':
			outgoing.update(status='kickstarted with "%s" and prepared experiment "%s"'%
				(sim.kickstart,sim.experiment))
			with open(os.path.join(settings.SIMSPOT,sim.path,'expt.json')) as fp:
				expt = json.load(fp)
				outgoing.update(settings_raw=str(yamlb(expt['settings'])))
			#---block syntax from yamlb 
			regex_block_standard = r"^\s*([^\n]*?)\s*(?:\s*:\s*\|)\s*([^\n]*?)\n(\s+)(.*?)\n(?!\3)"
			if 'metarun' not in expt:
				#---a single settings block for a standard run
				settings_blocks = {'settings':{'settings':yamlb(expt['settings']),
					'multi':[i[0] for i in re.findall(regex_block_standard,expt['settings'],
					flags=re.M+re.DOTALL)]}}
				# !!! hello this is also a hack
				#settings_blocks['chooser?'] = {'settings':{'choosy':'incoming_sources'},'multi':[]}
			#---! metarun development goes here
			else: return HttpResponse('metarun is under development')
			form = SimulationSettingsForm(initial={'settings_blocks':settings_blocks})
			#---prepare fieldsets as a loop over the blocks of settings, one per run
			outgoing['fieldsets'] = [FieldSet(form,[settings_name+'|'+key 
				for key,val in settings_block['settings'].items()],legend=settings_name) 
				for settings_name,settings_block in settings_blocks.items()]
			#---! add a condition for whether we need a coordinate here? only some methods actually use it
			form_source = CoordinatesSelectorForm()
			outgoing['fieldsets'].append(FieldSet(form_source,['source'],
				legend="fetch coordinates"))
			outgoing['fieldsets'] = tuple(outgoing['fieldsets'])
		#---on submission we prepare the job
		else:
			form = SimulationSettingsForm(request.POST,request.FILES)
			form_source = CoordinatesSelectorForm(request.POST,request.FILES)
			#---note that the form validator applies here. Using "None" in the settings will cause some 
			#---...settings to be blank on the form and excepted on post. use "none" to get around this
			#---note that if the form is invalid the site will complain and keep you there
			if form.is_valid() and form_source.is_valid():
				#---unpack the form
				unpacked_form = [(i.split('|'),j) for i,j in form.data.items() if '|' in i]
				settings_blocks = dict([(k[0],{}) for k,v in unpacked_form])
				for (run_name,key),val in unpacked_form: settings_blocks[run_name][key] = val
				if len(settings_blocks)==1:
					#---note that a one-block run is a standard run (not a metarun)
					submit_fn = make_run(expt=settings_blocks['settings'],cwd=sim.path)
					sim.status = 'submitted:%s'%submit_fn
					sim.save()
				else: return HttpResponse('metarun is under development')
				#---process any incoming sources
				pks = form_source.cleaned_data['source']
				#---! implement input folders here at some point, perhaps using an alternate data structure
				if len(pks)>=1:
					if len(pks)>1:
						return HttpResponse('cannot parse incoming coordinates request: %s'%
							str(form_source.cleaned_data))
					obj = Coordinates.objects.get(pk=pks[0])
					#---copy the coordinate to the automacs simulation, where it is automatically picked up
					#---...from the root of the inputs folder (assume no other PDB file there)
					shutil.copyfile(os.path.join(settings.COORDS,obj.name),
						os.path.join(settings.SIMSPOT,sim.path,'inputs',obj.name))
				return HttpResponseRedirect(reverse('simulator:detail_simulation',kwargs={'id':sim.id}))

	#---submitted and running jobs
	if re.match('^submitted:.+$',sim.status):
		statuses = job_status_infer(sim=sim)
		outgoing.update(job_status=statuses[sim.name]['stat'])
		#---only show the ajax console if we are running
		if statuses[sim.name]['stat']=='running':
			outgoing.update(logging=os.path.basename(statuses[sim.name]['fn']))

	if False:
		#---submitted and running jobs
		if re.match('^submitted:.+$',sim.status):
			job_status = None
			#---if the job is submitted we have to run this refresh block to infer its status
			#---! is inference the best option here, or should we track the jobs in the database?
			#---pop off the submission path
			submit_stamp = re.match('^submitted:(.+)$',sim.status).group(1)
			#---anticipate different names for the file depending on its job status
			for namer,form in settings.CLUSTER_NAMER.items():
				if os.path.isfile(os.path.join(settings.CLUSTER,re.sub('STAMP',submit_stamp,form))):
					job_status = namer
					#---! best not to update the job status here because otherwise we cannot refresh
					break
			outgoing.update(job_status=job_status)

	#---outgoing request only shows the user things they can change
	return render(request,'simulator/detail.html',outgoing)

def upload_coordinates(request):
	"""
	Upload files to a new external source which can be added to future simulations.
	"""
	if request.method == 'GET': 
		form_coords = build_form_upload_coords()
	else:
		form_coords = build_form_upload_coords(request.POST,request.FILES)
		if form_coords.is_valid():
			coords = form_coords.save(commit=False)
			coords.name = re.sub(' ','_',coords.name)
			#---! do other stuff here if you want, before saving
			for filedat in request.FILES.getlist('files'):
				#---assume only one file and we save the name here
				coords.source_file_name = filedat.name
				with open(os.path.join(settings.COORDS,coords.name),'wb+') as fp:
					for chunk in filedat.chunks(): fp.write(chunk)
			coords.save()
			return HttpResponseRedirect('/')
	#---! this is kind of wasteful because index already does it ???
	outgoing = dict(sims=Simulation.objects.all().order_by('id'),\
		coords=Coordinates.objects.all().order_by('id'))
	outgoing.update(root=settings.SIMSPOT)
	form = build_simulation_form()
	outgoing.update(form_sim_new=form,form_upload_coords=form_coords)
	return render(request,'simulator/index.html',outgoing)

def cluster_view(request,debug=False):
	"""
	Report on a running simulation if one exists.
	"""
	#---! hacked six ways
	#---! NOTE THAT WE WANT ALL FILE MONITORING TO HAVE SOME KIND OF CHANGE-PUSH METHOD INSTEAD OF FREQUENT
	#---! ...CALLS TO DJANGO, WHICH SEEMS SILLY.
	try:
		with open('logs/cluster.%s'%settings.NAME) as fp: text = fp.read()
		return JsonResponse({'line':text,'running':True})
	except: return JsonResponse({'line':'idle','running':False})

def sim_console(request,log_fn):
	"""
	Report on a running simulation if one exists.
	Note that getting teh status of the simulation automatically provides the filename for the running
	job's log file. Hence we send the log file as a signal to monitor things, then send it back through
	the URL so that the sim_console function (me) needs only to pipe it back to the page. This is 
	way more elegant than using this function to request the file, since we already have it in the detail
	function.
	"""
	#---! hacked six ways
	try:
		with open(os.path.join(settings.CLUSTER,log_fn)) as fp: text = fp.read()
		return JsonResponse({'line':text,'running':True})
	except: return JsonResponse({'line':'idle','running':False})
