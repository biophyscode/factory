from __future__ import absolute_import
from celery import shared_task
import os,subprocess
from django.conf import settings
from .models import BackgroundCalc
import time

@shared_task(track_started=True)
def sherpacalc(job_row_id,autoreload=False,log='log',cwd='./'):

	"""
	Run the calculations in the background.
	REMEMBER THAT IF YOU CHANGE THIS FUNCTION YOU HAVE TO RESTART THE WORKER!!!
	"""

	print "[STATUS] running sherpacalc at with cwd=%s at %s"%(cwd,os.getcwd())
	job = subprocess.Popen('make compute log=%s autoreload'%log,cwd=cwd,
		shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	#---! should we gut the background jobs? and rework the queue viewer?
	this_job = BackgroundCalc.objects.get(pk=job_row_id)
	this_job.pid = job.pid
	this_job.save()
	job.communicate()
	#---! should we always plot?
	job = subprocess.Popen('make plot plotlog=%s'%log,cwd=cwd,
		shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	this_job.pid = job.pid
	this_job.save()
	job.communicate()
	#---wait before deleting to make sure logs get pushed out
	this_job.delete()
	return
