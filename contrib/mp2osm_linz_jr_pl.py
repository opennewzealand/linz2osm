#!/usr/bin/python
# mp2osm_linz_jr_pl.py
# 
# derived from 'mp2osm_ukraine.py'
# modified by simon@mungewell.org
# modified by Karl Newman (User:SiliconFiend) to preserve routing topology and parse RouteParam
# modified by Joe Richards (joe@penski.net) to include SUFI IDs and support most LINZ/NZOGPS feature types
# modified by Peter Lambrechtsen (plambrechtsen@gmail.com) to have a correctly formatted xml that will be imported by osmosis, and to handle larger MP files.
# license: GPL V2 or later
# if you make modifications, please email your version to the previous authors (as per the GPL)

import xml.etree.ElementTree as ET

attribution = 'LINZ & NZ Open GIS'
file_mp = open('input.mp')
outputfile = 'output.osm'
timestamp = '2009-01-09T20:03:54Z'

# flags and global variable
poi = False
polyline = False
polygon = False
xmlversion = '-1'
roadid = ''
rNodeToOsmId = {} # map routing node ids to OSM node ids

# debug/stats counters
poi_counter = 0
polyline_counter = 0
polygon_counter = 0

# writing to file
f = open(outputfile, 'w')
f.write('<osm generator="mp2osm_linz_jr_pl" version="0.6">\n')

#osm = ET.Element('osm', version='0.6', generator='mp2osm_linz_jr_nz' )
#osm.text = '\n  '
#osm.tail = '\n'
#source = '    <tag k="source" v="LINZ &amp; NZ Open GIS"/>'
source = ET.Element('tag', k='source',v=attribution)
source.tail = '\n    '
nodeid = -1
# Define the mapping from Garmin type codes to OSM tags
# Note that single items in parentheses need a trailing comma
poitagmap = {

     #JR: catCities
     (0x0100,0x100): {'place': 'city', 'linz:comment': 'size >10M'},        # added by JR.  np
     (0x0200,0x200): {'place': 'city', 'linz:comment': 'size 5-10M'},      # added by JR.  np
     (0x0300,0x300): {'place': 'city', 'linz:comment': 'size 2-5M'},       # added by JR.  np
     (0x0400,0x400): {'place': 'city', 'linz:comment': 'size 1-2M'},       # added by JR - pres
     (0x0500,0x500): {'place': 'city', 'linz:comment': 'size 0.5-1M'},     # added by JR - pres
     (0x0600,0x600): {'place': 'city', 'linz:comment': 'size 200-500K'},   # added by JR - pres
     (0x0700,0x700): {'place': 'city', 'linz:comment': 'size 100-200K'},   # added by JR - pres
     (0x0800,0x800): {'place': 'city', 'linz:comment': 'size 50-100K'},    # added by JR - pres
     (0x0900,0x900): {'place': 'city', 'linz:comment': 'size 20-50K'},     # added by JR - pres
     (0x0a00,0xa00): {'place': 'town', 'linz:comment': 'size 10-20K'},     # added by JR - pres
     (0x0b00,0xb00): {'place': 'town', 'linz:comment': 'size 5-10K'},       # added by JR - pres
     (0x0c00,0xc00): {'place': 'town', 'linz:comment': 'size 2-5K'},       # added by JR - pres
     (0x0d00,0xd00): {'place': 'town', 'linz:comment': 'size 1-2K'},       # added by JR - pres
     (0x0e00,0xe00): {'place': 'village', 'linz:comment': 'size 500-1K'},  # added by JR - pres
     (0x0f00,0xf00): {'place': 'village', 'linz:comment': 'size 200-500'}, # added by JR - pres
     (0x1000,): {'place': 'hamlet', 'linz:comment': 'size 100-200'},  # added by JR - pres
     (0x1100,): {'place': 'hamlet', 'linz:comment': 'size 100-200'},  # added by JR - pres

     (0x1200,): {'leisure': 'marina' },                               # added by JR - Raglan Wharf.  Spreadsheet suggests hamlet (0-100 size) but not in our dataset

     (0x1612, 0x1c00, 0x6400): {'highway': 'gate'},
     (0x160f,): {'man_made': 'beacon', 'mark_type': 'white'},         # added by JR - pres

     (0x1c01,): {'man_made': 'ship_wreck'},                           # added by JR - pres
     (0x1c09,): {'linz:comment': 'FIXMEFIXME  rock, awash, reef'},                   # added by JR - pres - TODO ammend

     (0x1e00,): {'place': 'region'},                                  # added by JR - pres, e.g. Southland    
     (0x2b00,): {'tourism': 'hotel'},
     (0x2b01,): {'tourism': 'motel'},
     (0x2b03,): {'tourism': 'caravan_site'},
     (0x2c06,): {'leisure': 'park'}, # added by JR
     (0x2c08,): {'leisure': 'park'}, # added by JR
     (0x2d05,): {'leisure': 'golf_course'}, # added by JR
     (0x2d06,): {'sport': 'skiing'}, # added by JR
     (0x2f04,): {'aeroway': 'aerodrome'}, # added by JR
     (0x2e02,): {'shop': 'supermarket'},
     (0x2f08,): {'amenity': 'bus_station'},
     (0x2f09,): {'waterway': 'boatyard'}, # added by JR
     (0x3002,): {'amenity': 'hospital'}, # added by JR
     (0x4400,): {'amenity': 'fuel'},
     (0x4700,): {'leisure': 'slipway'},
     (0x4800,): {'tourism': 'campsite'},
     (0x4900,): {'leisure': 'park'},
     (0x4a00,): {'tourism': 'picnic_site'},
     (0x4c00,): {'tourism': 'information'},
     (0x4d00,): {'amenity': 'parking'},
     (0x4e00,): {'amenity': 'toilets'},
     (0x5100,): {'amenity': 'telephone'},
     (0x5200,): {'tourism': 'viewpoint'},
     (0x5400,): {'sport': 'swimming'},
     (0x5500,): {'waterway': 'dam'}, # added by JR
     (0x5904,): {'aeroway': 'helipad'},
     (0x5905,): {'aeroway': 'aerodrome'},
     (0x5904,): {'aeroway': 'helipad'},
     (0x5a00,): {'distance_marker': 'yes'}, # Not approved
     (0x6401,): {'bridge': 'yes'}, # Apply to points?
     (0x6401,): {'building': 'yes'},
     (0x6402,): {'amenity': 'shelter', 'building': 'yes', 'tourism': 'alpine_hut'}, # added by JR -trekking huts, bivouacs, shelters, cabins
     (0x6403,): {'amenity': 'grave_yard'}, #added by JR
     (0x6505,): {'amenity': 'public_building', 'building': 'yes'},  # added by JR, only ex is Pumphouse
     (0x6406,): {'mountain_pass': 'yes', 'place': 'locality'}, # by JR: was highway=crossing, now mountain_pass=yes (for pass,col,saddle) TODO check
     (0x640c,): {'man_made': 'mineshaft'},
     (0x640a,): {'place': 'locality'}, # by JR - seems to apply to a lot of diff features, and is Garmin default for a POI
     (0x640d,): {'man_made': 'pumping_rig', 'type': 'oil'},
     (0x6411,): {'man_made': 'tower'},
     (0x6412,): {'highway': 'track', 'place': 'locality'}, # by JR - start of trek/walk- used to be 'trailhead' which is not even a proposed value
     (0x6413,): {'natural': 'cave_entrance'}, # by JR - used to be tunnel=yes but appears to caves - TODO check
     (0x6500, 0x650d): {'natural': 'water'},
     (0x6501,): {'natural': 'glacier'}, # added by JR - TODO tourism=attraction too?
     (0x6508,): {'waterway': 'waterfall'},
     (0x650c,): {'place': 'islet'},  # added by JR - v2
     (0x6511,): {'natural': 'spring'}, # added by JR - natural spring source
     (0x6513,): {'natural': 'wetland'}, # added by JR
     (0x6600,): {'place': 'locality', 'natural': 'hill', 'linz:comment': 'FIXME - hill?'}, # added by JR.. TODO check these, most seem to be in northland
     (0x6603,): {'landuse':'basin'}, # added by JR - TODO check since this is natural basin poi
     (0x6605,): {'natural': 'bench'},
     (0x6607,): {'natural': 'cliff'}, # added by JR - cliffs, bluffs etc
     (0x660c,): {'place': 'island'}, # added by JR - seems to be small islands as well as large
     (0x660a,): {'natural': 'wood'}, # added by JR - include bush and wild overgrowth
     (0x6611,): {'natural': 'mountain_range'}, # added by JR - TODO does not exist as tag
     (0x6613,): {'natural': 'ridge'}, # added by JR - TODO does not exist as tag

     (0x660d,): {'place': 'locality', 'natural': 'water'}, # added by JR - poi which are lake names
     (0x6616,): {'natural': 'peak'},
     (0x6617,): {'place': 'locality', 'natural': 'gully', 'linz:comment': 'FIXME: gorge/gully'}, # added by JR - gully/gorge does not exist, but giving it a placename might work
    }
polylinetagmap = {
     # TODO FIXME all these highway types, and links need to be checked
     (0x1,): {'highway': 'motorway'},   # added by JR
     (0x2,): {'highway': 'trunk'},
     (0x3,): {'highway': 'primary'},
     (0x4,): {'highway': 'secondary'},
     (0x5,): {'highway': 'tertiary'},
     (0x6,): {'highway': 'residential'},
     (0x7,): {'highway': 'service'}, # added by JR - TODO confirm in other places, example is Auckland airport's Cyril Kay Rd.. cf 0x7 as polygon which is diff.
     (0x8,): {'highway': 'primary_link'}, # added by JR - TODO FIXME what is a turning point (U-Turn etc) on a big road? this is actually on a tertiary road when i looked
     (0x9,): {'highway': 'secondary_link'}, # added by JR - TODO FIXME in the LINZ dataset is this actually used to connect secondary roads, or other types?
     (0xa,): {'highway': 'track', 'surface': 'unpaved'},
     (0xb,): {'highway': 'trunk_link'}, # added by JR
     (0xc,): {'junction': 'roundabout'}, # added by JR
     (0xd,): {'highway': 'cycleway'}, # added by JR
     (0x14,): {'railway': 'rail'}, # added by JR
     (0x16,): {'highway': 'footway'}, # added by JR
     (0x18,): {'waterway': 'stream'},
     (0x1b,): {'route': 'ferry'}, # added by JR

     # boundaries http://wiki.openstreetmap.org/wiki/Key:admin_level#10_admin_level_values_for_specific_countries
     (0x1c,): {'boundary': 'administrative', 'admin_level': '4'}, # added by JR, seems to be e.g. Otago/Canterbury, Auckland/Waikato TODO check this
     (0x1d,): {'boundary': 'administrative', 'admin_level': '6'}, # added by JR, seems to be e.g. Timaru district council, TODO check this

     (0x1e,): {'landuse': 'forest', 'leisure': 'nature_reserve'}, # added by JR
     (0x1f,): {'waterway': 'canal'},                              # added by JR, was 'river', but the only ones present are in Chch canals
     (0x29,): {'power': 'line'}
    }
polygontagmap = {
     (0x2,): {'landuse': 'residential'},     # added by JR - pres
     (0x20,): {'tourism': 'zoo', 'tourism': 'attraction'}, # added by JR - only Hamilton Zoo
     (0x5,): {'amenity': 'parking', 'area': 'yes'},
     (0x7,): {'landuse': 'aeroway'}, # added by JR - to describe outlines of runways and airport areas, cf. polyline
     (0x8,): {'landuse': 'retail', 'building': 'shops'}, # added by JR, cf. 0x8 polyline which is a ramp
     (0xd,): {'landuse': 'reservation', 'area': 'yes'}, # reservation is not even a proposed value TODO JR: this looks weird to me
     (0x13,): {'building': 'yes', 'area': 'yes'}, # added by JR - buildings, including hospitals or other random ones, esp present in Waikato
     (0x14,0x15): {'natural': 'wood', 'area': 'yes'}, # added by JR - v2
     (0x17,): {'leisure': 'park', 'area': 'yes'}, # added by JR - city park
     (0x18,): {'leisure': 'golf_course', 'area': 'yes'},
     (0x19,): {'leisure': 'sports_centre', 'area': 'yes', 'linz:todo': 'check type'}, # added by JR, TODO (check, sports_centre implies a building, but is at least rendered green). examples found in LINZ include sports parks, race courses, stadiums, cricket 'domains'..
     (0x1a,): {'landuse': 'cemetery', 'area': 'yes'}, # added by JR, TODO is ok, or should it be amenity=graveyard
     (0x28,): {'comment': 'JR:ocean'}, # added by JR, TODO work out what this is about, should we using coastlines
     (0x3c, 0x3e, 0x40, 0x41): {'natural': 'water', 'area': 'yes'}, # 0x3e added by JR
     (0x47, 0x48, 0x49): {'waterway': 'riverbank', 'area': 'yes'}, # 0x47 added by JR
     (0x4c,): {'waterway': 'intermittent', 'area': 'yes'},
     (0x50,): {'natural': 'wood', 'area': 'yes'}, # added by JR, seems to be for nature reserves too
     (0x51,): {'natural': 'wetland', 'area': 'yes'} # added by JR, was marsh
    }


def caps(words):
          return ' '.join([x.capitalize() for x in words.split()])

sufi=None
found=False
newElement=False
for line in file_mp:
    # print line
    # Marker for start of sections
    if line.startswith(';sufi'):
        if line == ';sufi-0' or line == ';sufi=0':
          sufi=None
        else:
          sufi=line.split('=')[1].strip();
     
    if line.startswith(('[POI]','[RGN10]','[RGN20]')):
        node = ET.Element('node', visible='true', id=str(nodeid), version=str(xmlversion), timestamp=str(timestamp))
        ET.Element('node', visible='true', id=str(nodeid), version=str(xmlversion), timestamp=str(timestamp))
        nodeid -= 1
        node.append(source)
        poi = True
        elementtagmap = poitagmap
        poi_counter += 1
        if sufi is not None:
            sufitag = ET.Element('tag', k='linz:sufi',v=sufi)
            sufitag.tail = '\n' 
            node.append(sufitag)
            sufi=None

    if line.startswith(('[POLYLINE]','[RGN40]')):
        node = ET.Element('way', visible='true', id=str(nodeid), version=str(xmlversion), timestamp=str(timestamp))
        nodeid -= 1
        node.append(source)
        polyline = True
        elementtagmap = polylinetagmap
        rnodes = {} # Track routing nodes for current polyline
        polyline_counter += 1
        if sufi is not None:
            sufitag = ET.Element('tag', k='linz:sufi',v=sufi)
            sufitag.tail = '\n' 
            node.append(sufitag)
            sufi=None

    if line.startswith(('[POLYGON]','[RGN80]')):
        node = ET.Element('way', visible='true', id=str(nodeid), version=str(xmlversion), timestamp=str(timestamp))
        nodeid -= 1
        node.append(source)
        polygon = True
        elementtagmap = polygontagmap
        polygon_counter += 1
        if sufi is not None:
            sufitag = ET.Element('tag', k='linz:sufi',v=sufi)
            sufitag.tail = '\n' 
            node.append(sufitag)
            sufi=None

    # parsing data
    if poi or polyline or polygon:
       
        if line.startswith('Label'):
            label = line.split('=')[1].strip()
            # Now strip out control codes such as ~[0x2f]
            codestart = label.find('~[')
            if codestart != -1:
                codeend = label.find(']',codestart)
                if codeend != -1:
                    label = label[0:codestart] + ' ' + label[codeend+1:]
            tag = ET.Element('tag', k='name',v=caps(label.strip())) # convert to right case. e.g. Arthur's Pass
            tag.tail = '\n    '
            node.append(tag)
        if line.startswith('Type'):
            typecode = line.split('=')[1].strip()
            tag = ET.Element('tag', k='linz:garmin_type',v=typecode)
            tag.tail = '\n    '
            node.append(tag)
            typecode = int(typecode, 16)
            for codes, taglist in elementtagmap.iteritems():
                if typecode in codes:
                    found=True
                    for key, value in taglist.iteritems():
                        tag = ET.Element('tag', k=key, v=value)
                        tag.tail = '\n    '
                        node.append(tag)
            if found==False :
                print 'ptang missing 0x%x poi:%s line:%s poly:%s sufi:%s' % (typecode, poi, polyline, polygon, sufi)
                found=False;
        if line.startswith('RoadID'):
            roadid = line.split('=')[1].strip()
            tag = ET.Element('tag', k='linz:RoadID',v=roadid)
            tag.tail = '\n    '
            node.append(tag)
        if line.startswith('RouteParam'):
            rparams = line.split('=')[1].split(',')
            # speedval has speeds in km/h corresponding to RouteParam speed value index
            speedval = [8, 20, 40, 56, 72, 93, 108, 128]
            speed = ET.Element('tag', k='maxspeed', v=str(speedval[int(rparams[0])]))
            speed.tail = '\n    '
            node.append(speed)
            rclass = ET.Element('tag', k='linz:garmin_road_class', v=str(rparams[1]))
            rclass.tail = '\n    '
            node.append(rclass)
            for att, attval in zip(('oneway', 'toll'), rparams[2:3]):
                if int(attval):
                    attrib = ET.Element('tag', k=att, v='true')
                    attrib.tail = '\n    '
                    node.append(attrib)
            # Note: taxi is not an approved access key
            vehicles = ['emergency', 'goods', 'motorcar', 'psv', 'taxi', 'foot', 'bicycle', 'hgv']
            for veh, res in zip(vehicles, rparams[4:]):
                vehtag = ET.Element('tag', k=veh, v=('yes', 'no')[int(res)])
                vehtag.tail = '\n    '
                node.append(vehtag)

        # Get nodes from all zoom levels (ie. Data0, Data1, etc)
        # TODO: Only grab the lowest-numbered data line (highest-resolution) and ignore the rest
        if line.startswith('Data'):
            if poi:
                coords = line.split('=')[1].strip()
                coords = coords.split(',')
                node.set('lat',str(float(coords[0][1:])))
                node.set('lon',str(float(coords[1][:-1])))
            if polyline or polygon:
                # Just grab the line and parse it later when the [END] element is encountered
                coords = line.split('=')[1].strip() + ','
                # TODO: parse out "holes" in a polygon by reading multiple Data0 lines and
                # constructing a multipolygon relation
        if line.startswith('Nod'):
            if polyline:
                # Store the point index and routing node id for later use
                nod = line.split('=')[1].strip().split(',', 2)
                rnodes[nod[0]] = nod[1]
        if line.startswith('[END]'):
            if polyline or polygon:
                # Have to write out nodes as they are parsed
                nodidx = 0
                nodIds = []
                reused = False
                while coords != '':
                    coords = coords.split(',', 2)
                    if str(nodidx) in rnodes:
                        if rnodes[str(nodidx)] in rNodeToOsmId:
                            curId = rNodeToOsmId[str(rnodes[str(nodidx)])]
                            reused = True
                        else:
                            curId = nodeid
                            nodeid -= 1
                            rNodeToOsmId[str(rnodes[str(nodidx)])] = curId
                    else:
                        curId = nodeid
                        nodeid -= 1
                    nodIds.append(curId)
                    # Don't write another node element if we reused an existing one
                    if not reused:
                        nodes = ET.Element('node', visible='true', version=str(xmlversion), timestamp=str(timestamp), id=str(curId), lat=str(float(coords[0][1:])), lon=str(float(coords[1][:-1])))
                        nodes.text = '\n    '
                        nodes.tail = '\n  '
#                        osm.append(nodes)
                        f.write(ET.tostring(nodes))

                    coords = coords[2]
                    reused = False
                    nodidx += 1
                nodidx = 0
                for ndid in nodIds:
                    nd = ET.Element('nd', ref=str(ndid))
                    nd.tail = '\n    '
                    node.append(nd)
            if polygon:
                nd = ET.Element('nd', ref=str(nodIds[0]))
                nd.tail = '\n    '
                node.append(nd)

            poi = False
            polyline = False
            polygon = False
            roadid = ''
            rnodes = {} # Clear out routing nodes to prepare for next entity

            node.text = '\n    '
            node.tail = '\n  '

            f.write(ET.tostring(node))
#            osm.append(node)
else:
	f.write('</osm>')

# dump some stats
print '======'
print 'Totals'
print '======'
print 'POI', poi_counter
print 'POLYLINE', polyline_counter
print 'POLYGON', polygon_counter
print 'Last nodeid', nodeid

