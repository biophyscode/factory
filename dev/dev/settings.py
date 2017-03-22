
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = '$364*dzfjx(5_$(isggtb_d$j@ms0uc8_h+uyccg_ks=a&=%v!'
DEBUG = True
ALLOWED_HOSTS = ['localhost']
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'dev.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'dev.wsgi.application'
DATABASES = {
    'default': {
        'ENGINE':'django.db.backends.sqlite3',
        'NAME': BASE_DIR+"/../../data/dev/db.sqlite3",
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'

#---will be added from kickstart
INSTALLED_APPS = tuple(list(INSTALLED_APPS)+['simulator','calculator','djcelery'])

#---will be added from kickstart, celery worker and routing settings
import djcelery
from kombu import Exchange,Queue
djcelery.setup_loader()
BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERYD_CONCURRENCY = 1
CELERY_QUEUES = (
    Queue('queue_sim',Exchange('queue_sim'),routing_key='queue_sim'),
    Queue('queue_calc',Exchange('queue_calc'),routing_key='queue_calc'),
    )
CELERY_ROUTES = {
    'simulator.tasks.sherpa':{'queue':'queue_sim','routing_key':'queue_sim'},
    'calculator.tasks.sherpacalc':{'queue':'queue_calc','routing_key':'queue_calc'},
    }

#---PATHS
PROJECT_NAME = "ptdins"
DROPSPOT = "data/dev/sims"
AUTOMACS_UPSTREAM = "http://www.github.com/bradleyrp/automacs"
# AUTOMACS_UPSTREAM = "/home/ryb/factory/automacs"
PLOTSPOT = "data/dev/plot"
POSTSPOT = "data/dev/post"
ROOTSPOT = "/home/ryb/factory"
CALCSPOT = "calc/dev"
PLOTSPOT = os.path.expanduser(os.path.abspath(PLOTSPOT))+'/'
POSTSPOT = os.path.expanduser(os.path.abspath(POSTSPOT))+'/'
ROOTSPOT = os.path.expanduser(os.path.abspath(ROOTSPOT))+'/'
DROPSPOT = os.path.expanduser(os.path.abspath(DROPSPOT))+'/'
BACKRUN = 'celery_backrun'