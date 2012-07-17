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

