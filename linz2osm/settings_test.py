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
    'lds_sample': {
        '_description': "LINZ Data Service Sample Data",
        '_srid': 4326,
        '_version': "2012-01-01",
        'ENGINE' : 'django.contrib.gis.db.backends.postgis',
        'NAME' : 'lds_sample',
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    #'django.contrib.sessions',

    'linz2osm.lobby',
    'linz2osm.data_dict',
    'linz2osm.convert',
    'linz2osm.workslices',
    # 'linz2osm.workslices',
    # 'linz2osm.lobby',

    # 'djcelery',
    'south',
)

BROKER_URL = 'amqp://guest@localhost//'
# SOUTH_TESTS_MIGRATE = False
SKIP_SOUTH_TESTS = True
