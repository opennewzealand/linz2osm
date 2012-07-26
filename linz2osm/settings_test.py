# Inherit from the settings.py defaults
try:
    from settings import *
except ImportError, e:
    pass

# Django test settings for linz2osm project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE' : 'django.contrib.gis.db.backends.postgis',
        'NAME' : 'linz2osm_test',
    },
}

INSTALLED_APPS = (
    'linz2osm.data_dict',
    'linz2osm.convert',
    # 'linz2osm.workslices',
    # 'linz2osm.lobby',
    
    # 'djcelery',
    'south',
)

BROKER_URL = 'amqp://guest@localhost//'
