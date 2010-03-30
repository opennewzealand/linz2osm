LINZ-2-OSM
==========


Requirements
------------

 * Django 1.2-beta
 * PostgreSQL + PostGIS
 * Pydermonkey
 
 Optionally:
 * BeautifulSoup (to populate layers from LINZ's data dictionary)
 * linz_topo scripts to convert IFF data to a PostGIS DB, from: 
   http://code.google.com/p/nz-geodata-scripts/wiki/LinzTopo
   
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
 
 * run `manage.py loaddata v16_layers` to populate the layer models.
 * run `manage.py loaddata example_tags` to load some example tags for road_cl,
   and some defaults for all layers.
   
 * run `manage.py runserver` and head to http://localhost:8000
 * have fun! :)
 

Support, Bugs, Ideas
--------------------

 * File an issue in Github at: 
   http://github.com/rcoup/linz2osm/issues
 * Ask on the NZOpenGIS mailing list:
   http://groups.google.co.nz/group/nzopengis

