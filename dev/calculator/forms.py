from django import forms
from .models import *
from django.contrib import messages
from django.conf import settings
from django.forms import formset_factory
from simulator.models import *
import glob,re

class collection_form(forms.ModelForm):

	class Meta:  

		model = Collection
		fields = ['name','simulations']

	def __init__(self,*args,**kwargs):

		kwargs.setdefault('label_suffix','')
		super(collection_form,self).__init__(*args,**kwargs)
		for field in self.fields.values():
			field.error_messages = {'required':
				'field "{fieldname}" is required'.format(fieldname=field.label)}
		#---! unclear if this is necessary
		# simulations = [[obj.id,obj.name] for obj in Simulation.objects.all()]
		# self.fields['simulations'] = forms.MultipleChoiceField(required=True,choices=simulations)
		for field in self.fields: self.fields[field].label = field.lower()

class group_form(forms.ModelForm):

	class Meta:  

		model = Group
		#---note that we omit simulation below so the user has to add simulations on the group detail page
		fields = ['name','selection']
		widgets = {'selection':forms.Textarea(
			attrs={'cols':30,'rows':4,'placeholder':'conventional atom or molecule selection string'})}

	def __init__(self,*args,**kwargs):

		kwargs.setdefault('label_suffix','')
		super(group_form,self).__init__(*args,**kwargs)
		for field in self.fields.values():
			field.error_messages = {'required':
				'field "{fieldname}" is required'.format(fieldname=field.label)}
		for field in self.fields: self.fields[field].label = field.lower()
		self.fields['selection'].initial = ''

		
class slice_form(forms.ModelForm):

	"""
	Trajectory slice applies to a collection of simulations and requires times (start,end,skip) 
	in picoseconds, and at least one group which provides an MDAnalysis-style selection command. 
	Adding slices and then running "compute" will generate the trajectory slices on disk.
	"""

	class Meta:  

		model = Slice
		fields = ['name','start','end','skip','groups']
		widgets = {
			'start':forms.TextInput(attrs={'placeholder':'1000 ps'}),
			'end':forms.TextInput(attrs={'placeholder':'101000 ps'}),
			'skip':forms.TextInput(attrs={'placeholder':'20 ps'}),
			}

	def __init__(self,*args,**kwargs):

		kwargs.setdefault('label_suffix','')
		super(slice_form,self).__init__(*args,**kwargs)
		for field in self.fields.values():
			field.error_messages = {'required':
				'field "{fieldname}" is required'.format(fieldname=field.label)}
		collections = [[obj.id,obj.name] for obj in Collection.objects.all()]
		self.fields['collections'] = forms.MultipleChoiceField(required=True,choices=collections)
		for field in self.fields: self.fields[field].label = field.lower()

class calculation_form(forms.ModelForm):

	class Meta:  

		model = Calculation
		fields = ['name','slice_name','group','collections']
		initial_fields = ['name','slice_name','group','collections']

	def __init__(self,*args,**kwargs):

		kwargs.setdefault('label_suffix','')
		super(calculation_form,self).__init__(*args,**kwargs)
		for field in self.fields.values():
			field.error_messages = {'required':
				'field "{fieldname}" is required'.format(fieldname=field.label)}
		collections = [[obj.id,obj.name] for obj in Collection.objects.all()]
		self.fields['collections'] = forms.MultipleChoiceField(required=True,choices=collections)

		#---detect calculation names from scripts in the calcs folder
		regex_valid_calculation = '^(?!(?:plot|pipeline)-)(.+)\.py$'
		fns = [os.path.basename(fn) for fn in glob.glob(settings.CALCSPOT+'/calcs/*.py')]
		valid_calcnames = [(i,i) for i in [re.findall(regex_valid_calculation,fn)[0] 
			for fn in fns if re.match(regex_valid_calculation,fn)]]
		self.fields['name'] = forms.ChoiceField(required=True,choices=valid_calcnames)

		#---get valid slices names (note this is the only user-facing slice name list)
		#---dummy object ids for the slice_name choice
		slice_names = [(i,i) for i in list(set([obj.name for obj in Slice.objects.all()]))]
		if slice_names != []:
			self.fields['slice_name'] = forms.ChoiceField(required=True,choices=slice_names)
		for field in self.fields: 
			self.fields[field].label = re.sub('_',' ',field.lower())

	def clean(self):
	
		cleaned_data = super(calculation_form, self).clean()
		collections = cleaned_data.get("collections")
		#---! hackish handling unicode below
		slice_name = cleaned_data['slice_name']
		for collection_id in collections:
			collection = Collection.objects.all().get(pk=collection_id)
			okay = False
			group = cleaned_data.get('group')
			error_message = ''
			for sim in collection.simulations.all():
				if not Slice.objects.all().filter(name=slice_name,groups=group).exists():
					error_message += 'cannot find slice "%s" and group "%s" for some simulation in "%s"'%(
						slice_name,group,collection.name)
					break
			if error_message != '': self.add_error('group',error_message)
