from __future__ import absolute_import
import os
from celery import Celery
from django.conf import settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE','dev.settings')
#---if you need the models use: import django;django.setup();from simulator.models import Simulation
#---! removed extraneous broker='django://' from below after system was working properly
app = Celery('dev',broker='redis://localhost:6379/0',backend='redis://localhost:6379/0')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
