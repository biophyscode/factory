from django.conf.urls import url
from django.conf.urls.static import static
from django.conf import settings
from .models import Simulation
from . import views
import os

urlpatterns = [
	url(r'^$',views.index,name='index'),
	url(r'^builder$',views.index,name='build_simulation'),
	url(r'^upload_sources$',views.upload_sources,name='upload_sources'),
	url(r'^upload_bundles$',views.upload_bundles,name='upload_bundles'),
	url(r'^sim(?P<id>[0-9]+)/?$',views.detail_simulation,name='detail_simulation'),
	url(r'^source(?P<id>[0-9]+)',views.detail_source,name='detail_source'),
	url(r'^sim(?P<id>[0-9]+)/logger$',views.simulation_logger,name='simulation_logger'),
	url(r'^sim(?P<id>[0-9]+)/queue_view$',views.queue_view,name='simulation_logger'),
	url(r'^queue_view',views.queue_view,name='simulation_logger'),
	url(r'^sim(?P<id>[0-9]+)/cancel$',views.simulation_cancel,name='simulation_cancel'),
	url(r'^sim(?P<id>[0-9]+)/terminate$',views.simulation_terminate,name='simulation_terminate'),
	url(r'^cancel_pending$',views.simulation_cancel_all,name='simulation_cancel_all'),
	]

urlpatterns += static('/static/simulator/',document_root='static/simulator/')
urlpatterns += static('/dropspot/',document_root=settings.DROPSPOT)
urlpatterns += static('/amxdocs/',document_root=settings.DROPSPOT+'/docs/amx/docs/build/_build/html/')
