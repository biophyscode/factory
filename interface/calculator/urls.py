from django.conf.urls import url

from . import views

urlpatterns = [
	url(r'^$',views.index,name='index'),
	url(r'^get_code/(?P<name>.+)$',views.get_code,name='get_code'),
	url(r'^make_notebook/(?P<name>.+)$',views.make_notebook,name='make_notebook'),
]