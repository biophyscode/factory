#!/usr/bin/env python

"""
Orchestrate a poor man's cluster system.
Because Ryan and Joe intensely dislike other (ahem ... vegetable-named) methods for doing this.
"""

import os,sys,time,glob,subprocess,re,json,tempfile,signal,textwrap,datetime
from config import read_config,write_config,is_terminal_command,bash,abspath
from makeface import abspath
from datapack import asciitree

def backrun(**specs):
	"""
	Run a script in the background with a new group ID and a script which will kill the job and children.
	"""
	cwd = specs.get('cwd','./')
	sudo = specs.get('sudo',False)
	if 'log' in specs: log_fn = specs['log']
	elif 'name' in specs: log_fn = 'log-backrun-%s'%specs['name']
	else: raise Exception('need argument: name or log')
	if 'stopper' in specs: stopper_fn = specs['stopper']
	elif 'name' in specs: stopper_fn = 'script-stop-%s'%specs['name']
	else: raise Exception('need argument: name or stopper')
	#---sometimes we want the stopper to be executable but othertimes we want to avoid this
	#---...since we might name the stopper like a pid file and we don't want users to get confused
	scripted = specs.get('scripted',True)
	instructs = ['cmd','bin','bash']
	if sum([i in specs for i in instructs])!=1: raise Exception('backrun requires one of: %s'%instructs)
	if 'cleanup' in specs and 'bash' not in specs: 
		raise Exception('cleanup only compatible with explicit bash scripts')
	#---run a command
	elif 'cmd' in specs:
		cmd_full = "%snohup %s > %s 2>&1 &"%(specs.get('pre',''),specs['cmd'],log_fn)
	#---run a script
	elif 'bin' in specs:
		#---! should we ensure the script is executable? security problems?
		cmd_full = "%snohup ./%s > %s 2>&1 &"%(specs.get('pre',''),specs['script'],log_fn)
	#---write a script and run it
	elif 'bash' in specs:
		fp = tempfile.NamedTemporaryFile(delete=False)
		fp.write(specs['bash'])
		if 'cleanup' in specs: fp.write('\n'+specs['cleanup'])
		fp.close()
		cmd_full = "%snohup bash %s > %s 2>&1 &"%(specs.get('pre',''),fp.name,log_fn)
	print('[BACKRUN] running from "%s": `%s`'%(cwd,cmd_full))
	if 'bash' in specs: print('[BACKRUN] running the following script:\n'+
		'\n'.join(['[BACKRUN] | %s'%i for i in specs['bash'].splitlines()]))
	job = subprocess.Popen(cmd_full,shell=True,cwd=cwd,preexec_fn=os.setsid,executable='/bin/bash')
	#---! weird problems: if job.returncode!=0: raise Exception('backrun failure on `%s`:'%cmd_full)
	#---! check for port failure?
	ask = subprocess.Popen('ps xao pid,ppid,pgid',shell=True,
		stdout=subprocess.PIPE,stderr=subprocess.PIPE,executable='/bin/bash')
	stdout,stderr = ask.communicate()
	#---! DEPRECATED
	if False:
		#import pdb;pdb.set_trace()
		#---get the pgid for this job pid
		try: ids = re.search('^(%d)\s+(\d+)\s+(\d+).*?\n'%job.pid,stdout.decode(),flags=re.M).groups()
		except: 
			print('[BACKRUN] pid=%d'%(job.pid))
			raise Exception('job is missing from `ps` so it probably failed. see %s'%log_fn)
		pgid = int(ids[2])
	print('[BACKRUN] pgid=%d kill_switch=%s'%(job.pid,stopper_fn))
	term_command = '%spkill -%s -g %d'%('sudo ' if sudo else '',specs.get('killsig','TERM'),job.pid)
	if specs.get('double_kill',False): term_command = term_command+'\n'+term_command
	kill_switch = os.path.join(cwd,stopper_fn)
	kill_switch_coda = specs.get('kill_switch_coda',None)
	with open(kill_switch,'w') as fp: 
		fp.write(term_command+'\n')
		#---! the following sudo on cleanup only works for a one-line command
		if kill_switch_coda: fp.write('\n# cleanup\n%s%s\n'%('sudo ' if sudo else '',kill_switch_coda))
	if scripted: os.chmod(kill_switch,0o744)
	job.communicate()
	
class Cluster:

	"""
	Make a computation cluster.
	"""

	"""
	General design questions regarding the cluster:
		current status
			right now the cluster is a daemon that watches for new job requests by file pattern
			it only receives jobs, runs backrun, and changes their names
			otherwise it does no tracking of any kind
		the role of the factory
			since  the cluster is so elusive, and only works on filenames, the  factory looks at the names
			looking at the names infers the cluster status
			it might be useful to use a proper message passing interface
			celery was super-annoying however
			zmq might be a useful option: http://zguide.zeromq.org/
			for now though, it would be better to just get it working before committing to something huge
			currently, we set sim.status to submitted:STAMP and then check the disk for the status of the 
				job based on the naming of that STAMP
		immediate plan
			+ to proceed we want a list of running jobs on the index page
			+ and we also want the running log to be piped to the simulation
			+ and we also want to keep a list of kill switches when we shutdown the cluster
			we have to decide whether to get the cluster status from the simulations or from the disk
			proposal
				keep the current scheme whereby we store submitted:STAMP as the status
				the cluster queue list should be all jobs with this status
				collect those jobs then figure out their status by the files on disk
				running jobs should be piped in via ajax
	see also
		running stuff in the background via management commands
			http://stackoverflow.com/questions/15728081/looping-background-process-with-django
				https://docs.djangoproject.com/en/dev/howto/custom-management-commands/
	"""

	#---file naming conventions from the root directory
	spec_fn = 'mill/cluster_spec.py'

	def say(self,text):
		"""
		Say something.
		"""
		stamp = datetime.datetime.now().strftime('%Y.%m.%d.%H:%M.%S')
		print('[CLUSTER] [%s] %s'%(stamp,text))

	def __init__(self,spot=None,kill_switch=None):
		"""
		Register a jobs directory and validate it.
		"""
		#---retrieve naming conventions
		self.naming = {}
		with open(self.spec_fn) as fp: exec(fp.read(),self.naming)
		#---unpack the globs. see clsuter_spec.py
		self.job_running = re.sub('STAMP','*',self.naming['running'])
		self.job_waiting = re.sub('STAMP','*',self.naming['waiting'])
		if not spot: raise Exception('you must supply a cluster spot')
		self.spot = abspath(spot)
		self.kill_switch = kill_switch
		self.say('running from %s'%self.spot)
		self.config = read_config()
		if not os.path.isdir(self.spot): os.mkdir(self.spot)
		#---! validate cluster folder upon finding it
		else: self.say('found cluster folder at %s'%self.spot)
		#---! autodetect nprocs
		self.njobs = int(self.config.get('njobs',1))
		self.say('cluster can run %d concurrent jobs'%self.njobs)
		self.say('cluster receives jobs written to files named %s'%self.job_waiting)
		self.say('cluster logs running jobs to %s'%self.job_running)
		self.state = {'running':[],'queue':[]}
		self.daemon()

	def start_job(self,path):
		"""
		get a job pid file
		start the job
		rename the pid file but only if the job actually starts
		"""
		dn,fn = os.path.split(path)
		fn_base = re.sub('\.req$','',fn)
		#---read the request
		with open(path) as fp: specs = json.load(fp)
		#---request is deleted immediately after reading
		os.remove(path)
		if 'bash' not in specs: raise Exception('cluster can only receive explicit bash jobs')
		#---simple cleanup operation moves the file to remove it from the queue
		specs.update(cleanup='mv %s %s\nrm %s'%(
			os.path.join(os.getcwd(),'cluster/run-%s'%fn_base),
			os.path.join(os.getcwd(),'cluster/fin-%s'%fn_base),
			os.path.join(os.getcwd(),'stop-%s'%fn_base)))
		#---run the script with backrun, which runs it through nohup
		#---use absolute paths to write the log file in case specs carries a cwd
		if 'stopper' not in specs: specs.update(stopper='stop-%s'%fn_base)
		self.say('running backrun with specs: %s'%specs)
		backrun(log=os.path.join(os.getcwd(),'cluster/run-%s'%fn_base),**specs)

	def restate(self,verbose=False):
		"""
		Refresh the state.
		"""
		#---check the disk to observe the state
		running = glob.glob(os.path.join(self.spot,self.job_running))
		waiting = sorted(glob.glob(os.path.join(self.spot,self.job_waiting)))
		if sorted(running)!=sorted(self.state['running']) or sorted(waiting)!=sorted(self.state['queue']):
			#---update the state
			self.state['running'] = sorted(running)
			self.state['queue'] = sorted(waiting)
			self.say(' status: '+str(self.state))
		free = self.njobs - len(running)
		#---run a job if ready
		if free<0: raise Exception('a serious error has occured: the cluster is overbooked')
		elif free==0: return
		elif free>0 and len(waiting)>0:
			self.say('received job request: %s'%waiting[0])
			self.start_job(waiting[0])

	def shutdown_handler(self,signal,frame):
		"""
		"""
		self.say('shutting down')
		if self.kill_switch: 
			if not os.path.isfile(self.kill_switch):
				self.say('cannot find supposed kill switch at %s'%self.kill_switch)
			else:
				self.say('removing kill switch at %s'%self.kill_switch)
				os.remove(self.kill_switch)
		#---move the cluster.log which serves as a lock file
		stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
		os.system('mv cluster.log logs/arch.cluster.%s.log'%stamp)
		os.system('mv cluster logs/arch.cluster.%s'%stamp)
		self.say('shutdown complete')
		sys.exit(0)

	def daemon(self):
		"""
		The main daemon loop for the cluster. Periodically checks and submits jobs.
		"""
		#---before starting the daemon we register the shutdown handler with signal
		signal.signal(signal.SIGINT,self.shutdown_handler)
		self.say('the daemon is running')
		while True:
			self.restate()
			time.sleep(2)
