from django import forms
from .models import *
from django.contrib import messages
from django.conf import settings
from django.forms import formset_factory
import re,subprocess
from django.db.models.fields import BLANK_CHOICE_DASH

#---! previously multiple_uploads.py

from django.forms import ValidationError

class MultiFileInput(forms.FileInput):

	def render(self,name,value,attrs={}):

		attrs['multiple'] = 'multiple'
		return super(MultiFileInput,self).render(name,None,attrs=attrs)

	def value_from_datadict(self,data,files,name):

		if hasattr(files,'getlist'): return files.getlist(name)
		else: return [files.get(name)]
 
class MultiFileField(forms.FileField):

	widget = MultiFileInput
	default_error_messages = {
		'min_num': u"Ensure at least %(min_num)s files are uploaded (received %(num_files)s).",
		'max_num': u"Ensure at most %(max_num)s files are uploaded (received %(num_files)s).",
		'file_size' : u"File: %(uploaded_file_name)s, exceeded maximum upload size."}

	def __init__(self,*args,**kwargs):
	
		self.min_num = kwargs.pop('min_num',0)
		self.max_num = kwargs.pop('max_num',None)
		self.maximum_file_size = kwargs.pop('maximum_file_size',None)
		super(MultiFileField, self).__init__(*args,**kwargs)

	def to_python(self, data):

		ret = []
		for item in data: ret.append(super(MultiFileField, self).to_python(item))
		return ret

	def validate(self, data):
	
		super(MultiFileField,self).validate(data)
		num_files = len(data)
		if len(data) and not data[0]: num_files = 0
		if num_files < self.min_num:
			raise ValidationError(self.error_messages['min_num'] % 
				{'min_num': self.min_num, 'num_files': num_files})
			return
		elif self.max_num and  num_files > self.max_num:
			raise ValidationError(self.error_messages['max_num'] % 
				{'max_num': self.max_num,'num_files': num_files})
		for uploaded_file in data:
			if uploaded_file.size > self.maximum_file_size:
				raise ValidationError(self.error_messages['file_size'] % 
				{ 'uploaded_file_name':uploaded_file.name})

#---! end multiple_uploads.py

#---some functions require absolute paths
def path_expander(x): return os.path.abspath(os.path.expanduser(x))

def get_program_choices():

	"""
	Collect a list of simulation protocols.
	"""

	#---add metaruns to program choices
	program_choices = ['protein','cgmd-bilayer','homology']
	try:
		print("TRYING TO GET BUNDLES")
		for pk,path in [[obj.pk,obj.path] for obj in Bundle.objects.all()]:
			kwargs = dict(shell=True,executable="/bin/bash",stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			path_full = os.path.expanduser(os.path.abspath(path))
			proc = subprocess.Popen("git -C %s ls-tree --full-tree -r HEAD"%path_full,**kwargs)
			ans = '\n'.join(proc.communicate())
			regex = '^[0-9]+\s*[^\s]+\s*[^\s]+\s*(metarun[^\s]+)'
			for m in [re.findall(regex,i)[0] for i in ans.split('\n') if re.match(regex,i)]:
				program_choices.append(obj.name+' > '+m)
			print("checking")
			print(path)
			print(path_full)
		print(program_choices)
		print("WIN!")
	except: pass
	return list(set(program_choices))

class build_simulation_form(forms.ModelForm):

	class Meta:  

		model = Simulation
		fields = ['name','program']
		program_choices = get_program_choices()
		widgets = {
			'program':forms.Select(choices=[(i,i) for i in program_choices],attrs={
				'title':'copy sources directly into step\nfolder (not step/source_name)',
				'size':len(program_choices)+1,'style':'resize:none;overflow:hidden;',
				})}

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

class form_simulation_tune(forms.Form):

	def __init__(self,*args,**kwargs):

		if 'initial' in kwargs: settings_info = kwargs['initial']['settings']
		else: settings_info = None
		kwargs.setdefault('label_suffix','')
		super(forms.Form,self).__init__(*args,**kwargs)
		if settings_info:
			for group_num,(named_settings,specs) in enumerate(settings_info):
				for key,val in specs:
					self.fields[named_settings+'|'+key] = forms.CharField(max_length=255,initial=val)
					self.fields[named_settings+'|'+key].label = key.lower()
					self.fields[named_settings+'|'+key].group = group_num
		source_choices = [[obj.id,obj.name] for obj in Source.objects.all()]
		self.fields['incoming_sources'] = forms.MultipleChoiceField(required=False,choices=source_choices)
		self.fields['incoming_sources'].label = 'sources'

class build_sources_form(forms.ModelForm):

	class Meta:  

		model = Source
		fields = ['name','fileset','elevate']
		widgets = {
			'elevate':forms.CheckboxInput(attrs={'title':
			'copy sources directly into step\nfolder (not step/source_name)'}),}
		
	fileset = MultiFileField(min_num=1,maximum_file_size=1024*1024*5)

	def __init__(self,*args,**kwargs):	
		
		kwargs.setdefault('label_suffix','')
		super(build_sources_form, self).__init__(*args, **kwargs)
		for field in self.fields: self.fields[field].label = field.lower()	

class build_bundles_form(forms.ModelForm):

	class Meta:  

		model = Bundle
		fields = ['name','path']
		
	def __init__(self,*args,**kwargs):	
		
		kwargs.setdefault('label_suffix', '')
		super(build_bundles_form, self).__init__(*args, **kwargs)
		for field in self.fields: self.fields[field].label = field.lower()
