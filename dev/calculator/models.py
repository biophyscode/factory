from django.db import models

class Collection(models.Model):

	"""
	Holds a list of simulations for batch computations.
	Corresponds to the "collections" section of a meta.yaml file in omnicalc.
	"""
	
	name = models.CharField(max_length=100,default='',unique=True)
	simulations = models.ManyToManyField('simulator.Simulation',blank=False)
	def __str__(self): return self.name

class Group(models.Model):

	"""
	Mirror the "group" object in omnicalc which holds a molecular dynamics selection string.
	"""
	
	name = models.CharField(max_length=100,default='',unique=True)
	selection = models.TextField(default='all')
	def __str__(self): return self.name

class Slice(models.Model):

	"""
	Mirror a trajectory slice in the database.
	"""
	
	name = models.CharField(max_length=100,default='',unique=False)
	simulation = models.ForeignKey('simulator.Simulation')
	start = models.IntegerField(blank=False,null=True)
	end = models.IntegerField(blank=False,null=True)
	skip = models.IntegerField(blank=False,null=True)
	groups = models.ManyToManyField(Group)
	def __str__(self): return self.simulation.name+'-'+self.name

class BackgroundCalc(models.Model):

	"""
	A calculation running in the background.
	"""

	class Meta:
		verbose_name = 'Background Calculation'
	def __str__(self): return 'PID '+str(self.pid)
	pid = models.IntegerField(default=-1)

class Calculation(models.Model):

	"""
	An omnicalc calculation managed by django.
	This populates the "extracalcs" dictionary in an omnicalc yaml file, which is later merged with calculations.
	"""

	name = models.CharField(max_length=100,default='',unique=True)
	#---! omnicalc must enforce uniqueness between calculations and "extracalcs" defined here
	name = models.CharField(max_length=100,default='',unique=False)
	uptype = models.CharField(max_length=30,choices=[(i,i) for i in ['simulation','post']],default='simulation')
	slice_name = models.CharField(max_length=50,
		#choices=[(i,i) for i in list(set([str(i.name) for i in Slice.objects.all()]))],
		blank=True,null=True)
	group = models.ForeignKey(Group)
	collections = models.ManyToManyField(Collection)
	def __str__(self): return self.name
