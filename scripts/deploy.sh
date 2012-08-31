#!/bin/sh

ssh otm@waipoua sudo -u linz2osm "whoami"
ssh otm@waipoua sudo -u linz2osm "bash -c 'cd /home/linz2osm/linz2osm/src ; git pull'"
ssh otm@waipoua sudo -u linz2osm "bash -c 'cd /home/linz2osm/linz2osm/src ; source ../bin/activate ; ./manage.py syncdb'"
ssh otm@waipoua sudo -u linz2osm "bash -c 'cd /home/linz2osm/linz2osm/src ; source ../bin/activate ; ./manage.py migrate'"
ssh otm@waipoua sudo -u linz2osm "bash -c 'cd /home/linz2osm/linz2osm/src ; source ../bin/activate ; ./manage.py collectstatic --clear --noinput'"
ssh otm@waipoua sudo supervisorctl restart all
