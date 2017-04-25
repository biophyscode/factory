from __future__ import unicode_literals

from django.db import models

import re
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

class Simulation(models.Model):
	"""
	A simulation executed by automacs.
	"""
	class Meta:
		verbose_name = 'AMX simulation'
	name = models.CharField(max_length=100,unique=True)
	path = models.CharField(max_length=100,unique=True)
	experiment = models.CharField(max_length=100,blank=True)
	kickstart = models.CharField(max_length=100,blank=True)
	status = models.CharField(max_length=100,blank=True)
	def __str__(self): return self.name

class Kickstart(models.Model):
	"""
	A text block of commands that "kickstarts" an automacs simulation.
	"""
	class Meta:
		verbose_name = 'AMX kickstarter'
	name = models.CharField(max_length=100,unique=True)
	text = models.TextField(unique=True)
	def __str__(self): return self.name

def validate_file_extension(value):
	if not re.match('^.+\.pdb$',value):
		raise ValidationError(_('%(value)s requires a file extension'),params={'value':value},)

class Coordinates(models.Model):
	"""
	A starting structure for a simulation.
	"""
	class Meta:
		verbose_name = 'AMX coordinates'
	name = models.CharField(max_length=100,unique=True,validators=[validate_file_extension])
	source_file_name = models.CharField(max_length=100)
