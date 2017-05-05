from django.conf import settings

def global_settings(request):
	"""
	"""
	return {
		'NOTEBOOK_PORT':settings.NOTEBOOK_PORT,
		'NOTEBOOK_IP':settings.NOTEBOOK_IP,
		'NAME':settings.NAME}