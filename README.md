LINZ-2-OSM
==========

Running at:
http://linz2osm.openstreetmap.org.nz/

Requirements
------------

 * Python 2.7 (not tested with Python 3)
 * Django 1.4
 * PostgreSQL 8.3 or later + PostGIS 1.5 or later
 * Pydermonkey (see notes)
 * Pygments
 * Django South
 * RabbitMQ
 * Celery 3 or later and django-celery
 * GDAL 1.5 or later
 * BeautifulSoup (only if generating layers from LINZ data dictionary with dd_load)

Installing Pydermonkey
----------------------

Pydermonkey needs to build spidermonkey-1.8.1pre, and the URL is out of date. To install:

 * run `pip install --no-install pydermonkey`
 * go into the build/pydermonkey directory, and checkout spidermonkey-1.8.1pre to a `spidermonkey-1.8.1pre` directory:
   run `hg clone http://hg.toolness.com/spidermonkey/ -u 1.8.1pre spidermonkey-1.8.1pre`
 * run `python setup.py build_spidermonkey`
 * go back to the virtualenv root and run `pip install --no-download pydermonkey`
 
Install
-------

 * make a settings_site.py file and add overrides for things like:
   * `DATABASES`
   * `DEBUG`, `TEMPLATE_DEBUG`
   * `ADMINS`, `MANAGERS`
   * `MEDIA_ROOT`
   * `TEMPLATE_DIRS`
   * `SECRET_KEY`
   * non-default databases are used as datasets, add a _description and _srid
     field to define. 

 * run `manage.py syncdb` to build the DB tables. Creating a user is a 
   good idea.
 * run `manage.py migrate` to apply DB migrations.
 * run `manage.py createcachetable django_cache` to add a cache table.
 
 * run `manage.py loaddata v16_layers` to populate the layer models.
 * run `manage.py loaddata example_tags` to load some example tags for road_cl,
   and some defaults for all layers.
 * run `manage.py generate_datasets` to configure the app for the datasets and layers you've added
 * run `manage.py runserver`
 * from the linz2osm dir, run `../manage.py celery -A workslices worker
 * head to http://localhost:8000
 * have fun! :)

New Datasets
------------

To load some other IFF data, use the linz_topo scripts from nz-geodata-scripts
to populate a PostGIS DB. Then, add it as a database in the settings file,
(make sure it has _description and _srid defined) and it should just work.

 * http://code.google.com/p/nz-geodata-scripts/wiki/LinzTopo   

Support, Bugs, Ideas
--------------------

 * File an issue in Github at: 
   http://github.com/opennewzealand/linz2osm/issues
 * Ask on the NZOpenGIS mailing list:
   http://groups.google.co.nz/group/nzopengis

Special Thanks
--------------

LINZ-2-OSM is made possible with the generous support of these organisations:

 * Land Information New Zealand
   http://www.linz.govt.nz/
 * New Zealand Geospatial Office
   http://www.linz.govt.nz/geospatial-office
 * Digital NZ
   http://www.digitalnz.org/
 * The Ministry of Culture and Heritage
   http://www.mch.govt.nz/
 * Koordinates
   http://www.koordinates.com/

Legal
-----

Copyright (C) 2010-2012 Koordinates Ltd.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

More Legal
----------

djangosnippets:
http://djangosnippets.org/about/tos/

-----
jQuery:
Copyright 2012 jQuery Foundation and other contributors
Released under the MIT license
http://jquery.org/license

-----
Bootstrap:
Copyright 2012 Twitter, Inc.

Licensed under the Apache License, Version 2.0 (the "License"); you may not
use this work except in compliance with the License. You may obtain a copy
of the License in the LICENSE file, or at:

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.

http://twitter.github.com/bootstrap/index.html
