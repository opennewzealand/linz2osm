#  LINZ-2-OSM
#  Copyright (C) Koordinates Ltd.
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Django settings for linz2osm project.

import djcelery
djcelery.setup_loader()

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE' : 'django.contrib.gis.db.backends.postgis',
        'NAME' : '',
        'USER' : '',
        'PASSWORD' : '',
    },
#    'linz_dataset': {
#        '_description': "Chathams V16",
#        '_srid': 3793,
#        'ENGINE' : 'django.contrib.gis.db.backends.postgis',
#        'NAME' : '',
#        'USER' : '',
#        'PASSWORD' : '',
#    },
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Pacific/Auckland'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directories for media, generated statics
# and shared static assets
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''
STATIC_ROOT = ''
LINZ2OSM_SCRIPT_ROOT = ''
STATICFILES_DIRS = (
    '/path/to/linz2osm/assets/',
)

# URLs that handles the media served from MEDIA_ROOT and STATIC_ROOT
# Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'
STATIC_URL = '/static/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '--fill-this-up-with-some-random-stuff--'

# List of callables that know how to import templates from various sources.
# TEMPLATE_LOADERS = (
#     # 'django.template.loaders.filesystem.load_template_source',
#     'django.template.loaders.app_directories.load_template_source',
# #     'django.template.loaders.eggs.load_template_source',
# )

MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'linz2osm.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'django.contrib.humanize',
    'django.contrib.sites',
    'django.contrib.comments',

    'linz2osm.linz2osm_comments',

    'linz2osm.lobby',
    'linz2osm.data_dict',
    'linz2osm.convert',
    'linz2osm.workslices',

    'djcelery',
    'south',
)

COMMENTS_APP = 'linz2osm.linz2osm_comments'

CACHE_BACKEND = 'db://django_cache'
BROKER_URL = 'amqp://guest@localhost//'
LINZ_DATA_SERVICE_API_KEY = 'ENTER API KEY'

LOGIN_URL = '/login/'

# Override anything here with a settings_site.py file
try:
    from settings_site import *
except ImportError, e:
    pass
