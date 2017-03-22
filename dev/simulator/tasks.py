from __future__ import absolute_import
from celery import shared_task
from .models import Simulation
import os,subprocess,re
from django.conf import settings
from .models import Simulation,Source
from celery.utils.log import get_task_logger
import time,re,json,glob,shutil,os
from billiard.exceptions import Terminated
from celery.signals import task_revoked

logger = get_task_logger(__name__)

def post_job_tasks(program,cwd):

	"""
	Method-specific cleanup tasks.
	"""

	if program=='homology':
		best_pointer = cwd+'/best_structure_path'
		if os.path.isfile(best_pointer):
			with open(best_pointer) as fp: bsp = fp.read()
			best = re.search('[\w0-9\.]+\.pdb',bsp).group()
			new_source = Source(name=best.rstrip('\.pdb'),elevate=False)
			new_source.save()
			os.mkdir(settings.DROPSPOT+'/sources/%s'%new_source.folder())
			shutil.copy(cwd+'/'+best,settings.DROPSPOT+'sources/%s'%new_source.folder())
	else: print "[WARNING] no post_job_tasks for method %s"%program

@shared_task(track_started=True,max_retries=0,bind=True,throws=(Terminated,))
def sherpa(self,command,**kwargs):

	"""
	Use subprocess and celery to execute a job in the background.
	"""

	cwd = kwargs['cwd']
	wait_fn = os.path.join(cwd,'waiting.log')
	if not os.path.isfile(wait_fn):
		print '[WARNING] sherpa tried to start a job with no "waiting.log" so exiting'
		return
	else: os.remove(wait_fn)
	job = subprocess.Popen(command,shell=True,cwd=cwd,preexec_fn=os.setsid)
	pid_log = os.path.join(cwd,'script-stop-job.sh')
	with open(pid_log,'w') as fp: fp.write('#!/bin/bash\npkill -TERM -g %d'%job.pid)
	os.chmod(pid_log,0744)
	job.communicate()
	if os.path.isfile(pid_log): os.remove(pid_log)
	#---! add the post_job_tasks again

@task_revoked.connect()
def job_revoked(*args,**kwargs):

	"""
	Kill the job when celery revokes it.
	"""

	request = kwargs['request']
	print '[STATUS] revoking request '+str(request)
	cwd = request.kwargs['cwd']
	pid_log = os.path.join(cwd,'PID.log')
	with open(pid_log) as fp: pid = int(re.search('([0-9]+)',fp.read()).group())
	print '[STATUS] killing PID %d and company'%pid
	#---kill the group related to the session leader
	os.system('pkill -TERM -g %d'%pid)
