from django import forms
from .models import *
from upload_multiple import *

import re
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

class build_simulation_form(forms.ModelForm):
	class Meta:  
		model = Simulation
		fields = ['name']
	def __init__(self,*args,**kwargs):
		"""
		Tell the user which fields are required.
		"""
		kwargs.setdefault('label_suffix', '')
		super(build_simulation_form, self).__init__(*args, **kwargs)
		for field in self.fields.values():
			field.error_messages = {'required':
				'field "{fieldname}" is required'.format(fieldname=field.label)}
		for field in self.fields: self.fields[field].label = field.lower()

class SimulationSettingsForm(forms.Form):
	"""
	Turn a settings block into a form.
	"""
	def __init__(self,*args,**kwargs):
		if 'initial' in kwargs: settings_blocks = kwargs['initial']['settings_blocks']
		kwargs.setdefault('label_suffix','')
		super(forms.Form,self).__init__(*args,**kwargs)
		if 'initial' in kwargs and settings_blocks:
			for group_num,(named_settings,specs) in enumerate(settings_blocks.items()):
				for key,val in specs['settings'].items():
					mods = dict(max_length=255,initial=val)
					if key in specs['multi']: mods.update(widget=forms.Textarea)
					self.fields[named_settings+'|'+key] = forms.CharField(**mods)
					self.fields[named_settings+'|'+key].label = re.sub('_',' ',key.lower())
					self.fields[named_settings+'|'+key].group = group_num

def validate_file_extension(value):
	if not re.match('^.+\.pdb$',value):
		raise ValidationError(_('%(value)s requires a file extension'),params={'value':value},)

class build_form_upload_coords(forms.ModelForm):
	class Meta:  
		model = Coordinates
		fields = ['name','files']
	files = MultiFileField(min_num=1,max_num=1,maximum_file_size=1024*1024*5)
	def __init__(self,*args,**kwargs):
		"""
		Tell the user which fields are required.
		"""
		kwargs.setdefault('label_suffix', '')
		super(build_form_upload_coords, self).__init__(*args, **kwargs)
		for field in self.fields.values():
			field.error_messages = {'required':
				'field "{fieldname}" is required'.format(fieldname=field.label)}
		for field in self.fields: self.fields[field].label = field.lower()
		self.fields['files'].label = ''
