from django.conf import settings

def global_settings(request):
	"""
	"""
	return {
		'NOTEBOOK_PORT':settings.NOTEBOOK_PORT,
		'NAME':settings.NAME}