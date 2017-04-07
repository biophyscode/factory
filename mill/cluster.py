#!/usr/bin/env python

"""
Orchestrate a poor man's cluster system.
Because Ryan and Joe intensely dislike other vegetable-named methods for doing this.
"""

import os,sys,time,glob
from config import read_config,write_config,is_terminal_command,bash,abspath
from makeface import abspath

class Cluster:

	"""
	Make a computation cluster.
	"""

	job_running = '*.running.pid'
	job_waiting = '*.waiting.pid'

	def __init__(self,dn=None):
		"""
		Register a jobs directory and validate it.
		"""
		if not dn: dn = 'logs/CLUSTER'
		self.dn = abspath(dn)
		self.config = read_config()
		if not os.path.isdir(self.dn): os.mkdir(self.dn)
		#---! validate cluster folder upon finding it
		else: print('[NOTE] found cluster folder at %s'%dn)
		#---! autodetect nprocs
		self.nprocs = int(self.config.get('nprocs',4))
		self.ppj = int(self.config.get('ppj',1))
		self.max_jobs = self.nprocs/self.ppj
		self.daemon()
		bash('which python')

	def submit(self):
		"""
		Add a new job.
		"""

	def start_job(self):
		"""
		get a job pid file
		start the job
		rename the pid file but only if the job actually 
		"""


	def check_and_submit(self):
		"""
		"""
		running = glob.glob(os.path.join(self.dn,self.job_running))
		waiting = sorted(glob.glob(os.path.join(self.dn,self.job_waiting)))
		free = self.max_jobs-len(running)
		if free<0: raise Exception('cluster is overbooked! something went really wrong')
		elif free==0: return
		elif free>0 and len(waiting)>0:
			print('free is %d'%free)
			print('waiting is %d'%len(waiting))
			self.start_job(waiting[0])


	def daemon(self):
		"""
		"""

		try:
			while True:
				self.check_and_submit()
				time.sleep(2)
		except KeyboardInterrupt:
			print('OKAY CHILL DUDE GOODBYE')

