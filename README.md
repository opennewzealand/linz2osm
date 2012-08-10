LINZ-2-OSM
==========

Requirements
------------

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
