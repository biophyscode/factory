from django.conf.urls import url
from django.conf.urls.static import static
from django.conf import settings
from . import views
import os

urlpatterns = [
	url(r'^$',views.index,name='index'),
	url(r'^ignore=(?P<ignore>[0-9]+)$',views.index,name='index_ignore',kwargs={'ignore':0}),
	url(r'^col(?P<collection_id>[0-9]+)grp(?P<group_id>[0-9]+)',views.index,name='bothIguess'),
	url(r'^grp(?P<group_id>[0-9]+)$',views.index,name=''),
	url(r'^grp(?P<group_id>[0-9]+)update$',views.index,name='index',kwargs={'update_group':True}),
	url(r'^col(?P<collection_id>[0-9]+)$',views.index,name=''),
	url(r'^col(?P<collection_id>[0-9]+)update$',views.index,name='index',kwargs={'update_collection':True}),
	url(r'^calc(?P<calculation_id>[0-9]+)$',views.index,name=''),
	url(r'^calc(?P<calculation_id>[0-9]+)update$',views.index,name='index',kwargs={'update_calculation':True}),
	url(r'^new_collection$',views.index,name='new_collection'),
	url(r'^new_group$',views.index,name='new_group'),
	url(r'^new_slice$',views.index,name='new_slice'),
	url(r'^slices$',views.slices_summary,name='slices'),
	url(r'^new_calculation$',views.index,name='new_calculation'),
	url(r'^compute$',views.compute,name='compute'),
	url(r'^rethumb$',views.refresh_thumbnails,name='refresh_thumbnails',kwargs={'remake':True}),
	url(r'^settings$',views.view_settings,name='view_settings'),
	url(r'^refresh_times$',views.refresh_times,name='refresh_times'),
	url(r'^sim(?P<id>[0-9]+)',views.detail_simulation,name='detail_simulation'),
	url(r'^logger',views.calculation_monitor,name='calculation_monitor'),
	url(r'^path=(?P<path>.+)$',views.view_code,name='view_code')
	]

urlpatterns += static('/static/calculator/',document_root='static/calculator/')
urlpatterns += static('/media/',document_root=settings.PLOTSPOT)
urlpatterns += static('/codes/',document_root=settings.ROOTSPOT)
urlpatterns += static('/omnidocs/',document_root=
	settings.ROOTSPOT+'/calc/project/omni/docs/build/_build/html/')
