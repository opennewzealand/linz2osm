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
        'NAME' : 'test_linz2osm',
    },
}

INSTALLED_APPS = (
    # 'django.contrib.auth',
    # 'django.contrib.contenttypes',
    # 'django.contrib.sessions',
    # 'django.contrib.messages',
    # 'django.contrib.admin',
    # 'django.contrib.admindocs',
    # 'django.contrib.staticfiles',
    # 'django.contrib.gis',
    
    'linz2osm.data_dict',
    'linz2osm.convert',
    'linz2osm.workslices',
    
    'south',
)
