from django.db import models
from django.core.files.storage import Storage
from django.conf import settings
import shutil,os,re,subprocess

class SourceQuerySet(models.QuerySet):
	
	"""
	Must accompany the custom delete in the model for bulk deletion.
	"""

	def delete(self,*args,**kwargs):
		for obj in self: obj.delete()
		super(SourceQuerySet,self).delete(*args,**kwargs)

class Source(models.Model):

	"""
	A generic input file for a simulation.
	"""
	
	objects = SourceQuerySet.as_manager()
	name = models.CharField(max_length=100,default='',unique=True)
	elevate = models.BooleanField(default=False)
	def __str__(self): return self.name

	def folder(self):

		"""
		Remove spaces from folder names.
		"""

		return re.sub(' ','_',self.name)

	def delete(self):

		"""
		Remove the simulation directory via the admin page.
		"""

		print '[STATUS] deleting source %s'%self.name
		if not os.path.isdir(settings.DROPSPOT+'/sources/'+self.folder()):
			print '[WARNING] that source cannot be found or deleted'
		else: shutil.rmtree(settings.DROPSPOT+'/sources/'+self.folder())
		print '[STATUS] done'
		super(Source,self).delete()

class SimulationQuerySet(models.QuerySet):
	
	"""
	Must accompany the custom delete in the model for bulk deletion.
	"""

	def delete(self,*args,**kwargs):
		for obj in self: obj.delete()
		super(SimulationQuerySet,self).delete(*args,**kwargs)


class Bundle(models.Model):

	"""
	A pointer to a git repository that contains a pre-made simulation procedure.
	The repo will be cloned into inputs before running the simulation.
	"""
	
	name = models.CharField(max_length=100,default='',unique=True)
	path = models.CharField(max_length=200,unique=False,blank=False)
	def __str__(self): return self.name

	class Meta:
		verbose_name = 'AUTOMACS bundle'

class Simulation(models.Model):

	"""
	A simulation executed by automacs.
	"""

	objects = SimulationQuerySet.as_manager()

	class Meta:
		verbose_name = 'AUTOMACS simulation'

	name = models.CharField(max_length=100,unique=True)
	#---we constrain this in forms.py
	program = models.CharField(max_length=100,blank=False)
	started = models.BooleanField(default=False)
	details = models.TextField(default='',blank=True)
	code = models.CharField(max_length=200,unique=True,blank=True)
	sources = models.ManyToManyField(Source,blank=True)
	time_sequence = models.CharField(max_length=100,default='',blank=True)
	def __str__(self): return self.name

	def delete(self):

		"""
		Remove the simulation directory via the admin page.
		"""

		print '[STATUS] deleting simulation %s'%self.name
		#---removed exception if the code is blank and now allow deletion even if no folder
		if re.match('^\s*$',self.code) or not os.path.isdir(settings.DROPSPOT+self.code):
			print '[WARNING] that simulation cannot be found or deleted (code="%s")'%self.code
		else: shutil.rmtree(settings.DROPSPOT+'/'+self.code)
		print '[STATUS] done'
		super(Simulation,self).delete()
