#  LINZ-2-OSM
#  Copyright (C) 2010-2012 Koordinates Ltd.
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

import urllib2

import BeautifulSoup

from django.core.management.base import BaseCommand

from linz2osm.data_dict.models import Layer

INDEX_URL = "http://apps.linz.govt.nz/topo-data-dictionary/index.aspx?page=index-obj-All"

class Command(BaseCommand):
    help = "Builds the Layer options"

    def handle(self, **options):
        html = urllib2.urlopen(INDEX_URL).read()
    
        # parse the HTML
        soup = BeautifulSoup.BeautifulSoup(html)
        # find <td class="bodytext"> element, which contains the data
        container = soup.find(id='contentwrapper')
    
        # find all the <tr> elements
        c = 0
        for row in container.findAll('tr'):
            cells = row.findAll('td')
            if not cells:
                # header row
                continue
            
            l_name = str(cells[0].a.string)
            l_entity = str(cells[1].string)
            print "%s:%s" % (l_name, l_entity)
            c += 1
            
            if l_entity.lower() == 'not available':
                l_entity = ''
            
            l, created = Layer.objects.get_or_create(name=l_name)
            l.entity = l_entity.capitalize()
            l.save()
            print "... created." if created else "... exists."
                
        print "%d layers processed" % c

