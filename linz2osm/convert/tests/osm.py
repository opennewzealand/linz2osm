import unittest
from xml.etree import ElementTree
import math
import sys
import random
random.seed(0)

from django.contrib.gis import geos

from linz2osm.convert import osm

class TestWriter(unittest.TestCase):
    def test_id(self):
        w = osm.OSMWriter()
        
        id0 = w.next_id
        self.assertEqual(type(id0), str)
        self.assert_(int(id0) < 0, "Expected ID <0, got %s" % id0)
        id1 = w.next_id
        self.assert_(int(id1) < 0, "Expected ID <0, got %s" % id0)
        self.assertNotEqual(int(id1), int(id0))

    def test_id_hash(self):
        w = osm.OSMWriter()
        self.assertEqual(int(w.next_id), -1)
        
        w = osm.OSMWriter('bob')
        id = int(w.next_id)
        self.assert_(id < 0, "Expected ID <0, got %s" % id)
        self.assertNotEqual(id, -1)

        w = osm.OSMWriter(777)
        id = int(w.next_id)
        self.assert_(id < 0, "Expected ID <0, got %s" % id)
        self.assertNotEqual(id, -1)

        w = osm.OSMWriter(u'unicode: \xe4\xf6\xfc')
        id = int(w.next_id)
        self.assert_(id < 0, "Expected ID <0, got %s" % id)
        self.assertNotEqual(id, -1)

        w = osm.OSMWriter((7, u'unicode: \xe4\xf6\xfc'))
        id = int(w.next_id)
        self.assert_(id < 0, "Expected ID <0, got %s" % id)
        self.assertNotEqual(id, -1)
    
    def test_node(self):
        w = osm.OSMWriter()
        
        id = w.build_node(geos.Point(123, 456), [])
        print w.xml()

        n = w.tree.find('/create/node')
        self.assert_(n is not None, "Couldn't find <node>")
        self.assertEqual(n.get('id'), id[0])
        
        self.assertEqual(len(w.tree.findall('//node')), 1)
        
        self.assert_(int(n.get('id')) < 0, "ID < 0")
        self.assertEqual(float(n.get('lon')), 123)
        self.assertEqual(float(n.get('lat')), 456)
        self.assertEqual(len(n.getchildren()), 0)

        id = w.build_node(geos.Point(234, 567), [])
        self.assertEqual(len(w.tree.findall('//node')), 2)

    def test_repeated_nodes(self):
        """ Nodes should be repeated """
        w = osm.OSMWriter()
        ids = [
            w.build_node(geos.Point(123, 456), [], map=False),
            w.build_node(geos.Point(123, 456), [], map=False),
        ]
        self.assertEqual(len(w.tree.findall('//node')), 2)

        w = osm.OSMWriter()
        ids = [
            w.build_geom(geos.Point(123, 456), []),
            w.build_geom(geos.Point(123, 456), []),
        ]
        self.assertEqual(len(w.tree.findall('//node')), 2)

        w = osm.OSMWriter()
        ids = w.build_geom(geos.MultiPoint(geos.Point(123, 456), geos.Point(123,456)), {})
        self.assertEqual(len(w.tree.findall('//node')), 1)

        w = osm.OSMWriter()
        ids = w.build_geom(geos.MultiPoint(geos.Point(123, 456), geos.Point(12,34)), {})
        ids = w.build_geom(geos.Point(123, 456), {})
        self.assertEqual(len(w.tree.findall('//node')), 3)

        w = osm.OSMWriter()
        ids = w.build_geom(geos.Point(123, 456), {})
        ids = w.build_geom(geos.MultiPoint(geos.Point(123, 456), geos.Point(12,34)), {})
        self.assertEqual(len(w.tree.findall('//node')), 3)

        w = osm.OSMWriter()
        ids = w.build_geom(geos.Point(123, 456), {'tag':'val'})
        ids = w.build_geom(geos.MultiPoint(geos.Point(123, 456), geos.Point(12,34)), {'tag':'val'})
        self.assertEqual(len(w.tree.findall('//node')), 3)

        w = osm.OSMWriter()
        ids = w.build_geom(geos.MultiPoint(geos.Point(123, 456), geos.Point(12,34)), {'tag':'val'})
        ids = w.build_geom(geos.Point(123, 456), {'tag':'val'})
        self.assertEqual(len(w.tree.findall('//node')), 3)
    
    def test_tags_single(self):
        w = osm.OSMWriter()
        parent = ElementTree.Element('parent')
        
        w.build_tags(parent, {'t1': 'v1'})
        self.assertEqual(len(parent.getchildren()), 1)
        tn = parent.getchildren()[0]
        self.assertEqual(tn.tag, 'tag')
        self.assertEqual(tn.get('k'), 't1')
        self.assertEqual(tn.get('v'), 'v1')
    
    def test_tags_empty(self):
        # should be able to call with empty dicts
        w = osm.OSMWriter()
        parent = ElementTree.Element('parent')

        w.build_tags(parent, {})
        w.build_tags(parent, None)
        
    def test_tags_multiple(self):
        w = osm.OSMWriter()
        parent = ElementTree.Element('parent')
        w.build_tags(parent, {'t0': 'v0', 't1': 'v1'})
        self.assertEqual(len(parent.getchildren()), 2)
        for i,tn in enumerate(parent.getchildren()):
            self.assertEqual(tn.tag, 'tag')
            self.assertEqual(tn.get('k'), 't%d' % i)
            self.assertEqual(tn.get('v'), 'v%d' % i)
        
    def test_tags_unicode(self):
        w = osm.OSMWriter()
        parent = ElementTree.Element('parent')
        w.build_tags(parent, {u'unicode_tag: \xe4\xf6\xfc': u'unicode_value: \xe4\xf6\xfc'})
        tn = parent.getchildren()[0]
        self.assertEqual(tn.get('k'), u'unicode_tag: \xe4\xf6\xfc')
        self.assertEqual(tn.get('v'), u'unicode_value: \xe4\xf6\xfc')
    
    def test_tags_nonstring(self):
        w = osm.OSMWriter()
        parent = ElementTree.Element('parent')
        w.build_tags(parent, {'t1': 7})
        tn = parent.getchildren()[0]
        self.assertEqual(tn.get('v'), '7')

    def test_tags_long(self):
        w = osm.OSMWriter()
        parent = ElementTree.Element('parent')
        self.assertRaises(osm.Error, w.build_tags, parent, {'*' * 256: 'v'})
        self.assertRaises(osm.Error, w.build_tags, parent, {'t': '*' * 256})

    def test_way_simple(self):
        w = osm.OSMWriter()

        l = ((1,1), (2,2), (3,3),)

        id = w.build_way(l, {})
        print w.xml()
        
        n = w.tree.find('/create/way')
        self.assert_(n is not None, "Couldn't find <way>")
        
        self.assertEqual(len(w.tree.findall('//way')), 1)

        nodes = w.tree.findall('/create/node') 
        self.assertEqual(len(nodes), 3)
        node_map = dict([(nn.get('id'), nn) for nn in nodes])
        
        self.assert_(int(n.get('id')) < 0, "ID < 0")
        self.assertEqual(n.get('id'), id[0])
        self.assertEqual(len(n.getchildren()), 3)
        for i in range(3):
            nc = n.getchildren()[i]
            self.assertEqual(nc.tag, 'nd')
            node_ref = nc.get('ref')
            self.assert_(node_ref)
            node_el = node_map.get(node_ref)
            self.assert_(node_el is not None)
            self.assertEqual(float(node_el.get('lon')), l[i][0])
            self.assertEqual(float(node_el.get('lat')), l[i][1])
    
    def test_way_multiple(self):
        w = osm.OSMWriter()

        l = (
            ((1,1), (2,2), (3,3),),
            ((4,4), (5,5), (6,6),),
        )

        ids = (
            w.build_way(l[0], {}),
            w.build_way(l[1], {}),
        )
        print w.xml()
        
        ways = w.tree.findall('/create/way')
        self.assertEqual(len(w.tree.findall('//way')), 2)

        nodes = w.tree.findall('/create/node') 
        self.assertEqual(len(nodes), 6)
        node_map = dict([(nn.get('id'), nn) for nn in nodes])
        
        for j,wn in enumerate(ways):
            self.assertEqual(len(wn.getchildren()), 3)
            for i in range(3):
                nc = wn.getchildren()[i]
                self.assertEqual(nc.tag, 'nd')
                node_ref = nc.get('ref')
                self.assert_(node_ref)
                node_el = node_map.get(node_ref)
                self.assert_(node_el is not None)
                self.assertEqual(float(node_el.get('lon')), l[j][i][0])
                self.assertEqual(float(node_el.get('lat')), l[j][i][1])
    
    def test_ways_repeated_nodes(self):
        w = osm.OSMWriter()

        rc = []
        for i in range(6):
            r = random.random()
            rc.append((r*100.0, r*10.0))

        data = (
            ( (rc[0], rc[1], rc[2],), None),
            ( (rc[1], rc[2], rc[3],), {}),
            ( (rc[1], rc[3],), {}),
            ( (rc[4], rc[1], rc[5],), {'t':'v'}),
        )

        for coords,tags in data:
            w.build_way(coords, tags)
        print w.xml()
        print w._nodes
        
        ways = w.tree.findall('/create/way')
        self.assertEqual(len(w.tree.findall('//way')), 4)

        nodes = w.tree.findall('/create/node') 
        self.assertEqual(len(nodes), 6)
    
    def test_way_circular(self):
        w = osm.OSMWriter()

        l = ((0,0), (1,1), (2,0), (0,0),)

        id = w.build_way(l, {})
        print w.xml()
        
        wn = w.tree.find('/create/way')
        nodes = w.tree.findall('/create/node') 
        self.assertEqual(len(nodes), 3) # not 4!
        node_map = dict([(nn.get('id'), nn) for nn in nodes])
        
        self.assertEqual(len(wn.getchildren()), 4)
        for i,nc in enumerate(wn.getchildren()):
            node_ref = nc.get('ref')
            node_el = node_map.get(node_ref)
            self.assert_(node_el is not None)
        
        self.assertEqual(wn.getchildren()[0].get('ref'), wn.getchildren()[3].get('ref'))

    def test_polygon(self):
        w = osm.OSMWriter()

        g = geos.Polygon([(0,0), (10,10), (20,0), (0,0)], [(8,2), (10,4), (12,2), (8,2)])

        id = w.build_geom(g, {'mytag':'myvalue'})
        print w.xml()
        
        rels = w.tree.findall('/create/relation')
        self.assertEqual(len(rels), 1)
        ways = w.tree.findall('/create/way')
        self.assertEqual(len(ways), 2)
        way_map = dict([(ww.get('id'), ww) for ww in ways])
        nodes = w.tree.findall('/create/node') 
        self.assertEqual(len(nodes), 6)
        node_map = dict([(nn.get('id'), nn) for nn in nodes])
        
        rel = w.tree.find('/create/relation')
        rel_members = rel.findall('member')
        self.assertEqual(len(rel_members), 2)
        for i,mn in enumerate(rel_members):
            mw = way_map.get(mn.get('ref'))
            self.assert_(mw)
            self.assertEqual(mn.get('role'), 'outer' if i==0 else 'inner')
            self.assertEqual(mn.get('type'), 'way')
            self.assertEqual(len(mw.findall('tag')), 1 if mn.get('role') == 'outer' else 0)
        
        self.assertEqual(len(rel.findall('tag')), 1+1)
    
    def test_ring_clockwise(self):
        cw = [(0,0), (10,10), (20,0), (0,0)]
        ccw = cw[:]
        ccw.reverse()
        
        w = osm.OSMWriter()
        self.assertEqual(True, w.ring_is_clockwise(cw))
        self.assertEqual(False, w.ring_is_clockwise(ccw))
        
        w = osm.OSMWriter(wind_polygons_ccw=False)
        self.assertEqual(True, w.ring_is_clockwise(w.wind_ring(cw, is_outer=True)))
        self.assertEqual(True, w.ring_is_clockwise(w.wind_ring(ccw, is_outer=True)))
        self.assertEqual(False, w.ring_is_clockwise(w.wind_ring(cw, is_outer=False)))
        self.assertEqual(False, w.ring_is_clockwise(w.wind_ring(ccw, is_outer=False)))

        w = osm.OSMWriter(wind_polygons_ccw=True)
        self.assertEqual(False, w.ring_is_clockwise(w.wind_ring(cw, is_outer=True)))
        self.assertEqual(False, w.ring_is_clockwise(w.wind_ring(ccw, is_outer=True)))
        self.assertEqual(True, w.ring_is_clockwise(w.wind_ring(cw, is_outer=False)))
        self.assertEqual(True, w.ring_is_clockwise(w.wind_ring(ccw, is_outer=False)))

    def test_polygon_orientation_simple(self):
        geoms = {
            "cw" : [(0,0), (10,10), (20,0), (0,0)],
            "ccw" : [(0,0), (20,0), (10,10), (0,0)],
        }

        for dir in ('cw', 'ccw'):
            for name, ring in geoms.items():
                print "layer=%s, data=%s" % (dir, name)
                w = osm.OSMWriter(wind_polygons_ccw=(dir == 'ccw'))
                w.build_geom(geos.Polygon(ring), {})
                print w.xml()
            
                way = w.tree.find('/create/way')
                nodes = w.tree.findall('/create/node') 
                node_map = dict([(nn.get('id'), nn) for nn in nodes])
                
                coords = []
                for j,nd in enumerate(way.findall('nd')):
                    n = node_map.get(nd.get('ref'))
                    self.assert_(n is not None, "Node %s" % nd.get('ref'))
                    
                    c = (float(n.get('lon')), float(n.get('lat')))
                    coords.append(c)
                
                if dir == 'cw':
                    self.assert_(w.ring_is_clockwise(coords), "Outer-ring coords are anticlockwise (expecting cw)!")
                else:
                    self.assert_(not w.ring_is_clockwise(coords), "Outer-ring coords are clockwise (expecting ccw)!")
    
    def test_polygon_orientation_multipolygon(self):
        geoms = {
            "cw+ccw": ([(0,0), (10,10), (20,0), (0,0)], [(8,2), (12,2), (10,4), (8,2)]),
            "cw+cw": ([(0,0), (10,10), (20,0), (0,0)], [(8,2), (10,4), (12,2), (8,2)]),
            "ccw+cw": ([(0,0), (20,0), (10,10), (0,0)], [(8,2), (10,4), (12,2), (8,2)]),
            "ccw+ccw": ([(0,0), (20,0), (10,10), (0,0)], [(8,2), (12,2), (10,4), (8,2)]),
        }

        for dir in ('cw', 'ccw'):
            for name, rings in geoms.items():
                print "layer=%s, data=%s" % (dir, name)
                w = osm.OSMWriter(wind_polygons_ccw=(dir == 'ccw'))
                w.build_geom(geos.Polygon(*rings), {})
                print w.xml()
            
                rel = w.tree.find('/create/relation')
                ways = w.tree.findall('/create/way')
                way_map = dict([(ww.get('id'), ww) for ww in ways])
                nodes = w.tree.findall('/create/node') 
                node_map = dict([(nn.get('id'), nn) for nn in nodes])
                
                rel_members = rel.findall('member')
                for i,mn in enumerate(rel_members):
                    mw = way_map.get(mn.get('ref'))
                    self.assert_(mw is not None, "Way %s" % mn.get('ref'))
                    
                    coords = []
                    for j,nd in enumerate(mw.findall('nd')):
                        n = node_map.get(nd.get('ref'))
                        self.assert_(n is not None, "Node %s" % nd.get('ref'))
                        
                        c = (float(n.get('lon')), float(n.get('lat')))
                        coords.append(c)
                        
                    if mn.get('role') == 'outer':
                        if dir == 'cw':
                            self.assert_(w.ring_is_clockwise(coords), "Outer-ring coords are anticlockwise!")
                        else:
                            self.assert_(not w.ring_is_clockwise(coords), "Outer-ring coords are clockwise!")
                    else:
                        if dir == 'cw':
                            self.assert_(not w.ring_is_clockwise(coords), "Inner-ring coords are clockwise!")
                        else:
                            self.assert_(w.ring_is_clockwise(coords), "Inner-ring coords are anticlockwise!")

    def test_way_crossover(self):
        w = osm.OSMWriter()

        l = ((0,0), (1,1), (2,0), (0,0), (-1,-1),)

        id = w.build_way(l, {})
        print w.xml()
        
        wn = w.tree.find('/create/way')
        nodes = w.tree.findall('/create/node') 
        self.assertEqual(len(nodes), 4) # not 4!
        node_map = dict([(nn.get('id'), nn) for nn in nodes])
        
        self.assertEqual(len(wn.getchildren()), 5)
        for i,nc in enumerate(wn.getchildren()):
            node_ref = nc.get('ref')
            node_el = node_map.get(node_ref)
            self.assert_(node_el is not None)
        
        self.assertEqual(wn.getchildren()[0].get('ref'), wn.getchildren()[3].get('ref'))
    
    def test_way_split(self):
        w = osm.OSMWriter()
        w.WAY_SPLIT_SIZE = 10
        
        l = [(x, -x) for x in range(31)]
        
        ids = w.build_way(l, {'mytag':'myvalue'})
        print w.xml()
        
        self.assert_(len(ids) > 0, "Expected >1 ID returned")
        ways = w.tree.findall('/create/way')
        self.assertEqual(len(ways), len(ids))
        way_map = dict([(ww.get('id'), ww) for ww in ways])

        # <node>'s shouldn't be repeated
        nodes = w.tree.findall('/create/node')
        self.assertEqual(len(nodes), 31)
        node_map = dict([(nn.get('id'), nn) for nn in nodes])

        self.assertEqual(len(w.tree.findall('/create/relation')), 0)
        rel = w.tree.find('/create/relation')
    
        prev_way = None
        total_nodes = 0
        for i,way in enumerate(ways):
            way_nd = way.findall('nd')
            if prev_way:
                self.assertEqual(way_nd[0].get('ref'), prev_way.findall('nd')[-1].get('ref'))

            total_nodes += len(way_nd) - (1 if prev_way else 0)

            self.assertEqual(len(way.findall('tag')), 1)
            self.assertEqual(way.find('tag').get('k'), 'mytag')
            prev_way = way
        
        self.assertEqual(total_nodes, 31)

        # test we don't get any empty ways with multiple of WAY_SPLIT_SIZE -1
        w = osm.OSMWriter()
        w.WAY_SPLIT_SIZE = 10
        l = [(x, -x) for x in range(19)] # one node is repeated between 2x ways
        ids = w.build_way(l, {})
        print w.xml()
        ways = w.tree.findall('/create/way')
        self.assertEqual(len(ways), 2)
        
    def test_way_split_polygon(self):
        w = osm.OSMWriter()
        w.WAY_SPLIT_SIZE = 10
        
        g = geos.Polygon([(x, -x) for x in range(15)] + [(0,0)])
        
        ids = w.build_geom(g, {'mytag':'myval'})
        print w.xml()

        # should have done at least 1x split
        ways = w.tree.findall('/create/way')
        self.assertEqual(len(ways), math.ceil(15/10.0))
        
        # way should have tags too
        for way in ways:
            way_tags = way.findall('tag')
            self.assertEqual(len(way_tags), 1)
            self.assertEqual(way_tags[0].get('k'), 'mytag')
            self.assertEqual(way_tags[0].get('v'), 'myval')
        
        # <node>'s shouldn't be repeated
        nodes = w.tree.findall('/create/node')
        self.assertEqual(len(nodes), 15)
        node_map = dict([(nn.get('id'), nn) for nn in nodes])

        # Should be 1x Relation:MultiPolygon and no Relation:Collections
        self.assertEqual(len(w.tree.findall('/create/relation')), 1)
        rel = w.tree.find('/create/relation')
    
        rel_tags = rel.findall('tag')
        self.assertEqual(len(rel_tags), 2)
        self.assertEqual(rel_tags[0].get('k'), 'type')
        self.assertEqual(rel_tags[0].get('v'), 'multipolygon')
        self.assertEqual(rel_tags[1].get('k'), 'mytag')
        self.assertEqual(rel_tags[1].get('v'), 'myval')
    
    def test_split_polygon(self):
        w = osm.OSMWriter()
        w.WAY_SPLIT_SIZE = 10
        
        g = geos.Polygon([(x, -x**2) for x in range(15)] + [(0,0)], ((1,-2), (4,-2), (4,-3), (1,-2))) 
        
        ids = w.build_geom(g, {'mytag':'myval'})
        print w.xml()

        # should have done at least 1x split
        ways = w.tree.findall('/create/way')
        self.assertEqual(len(ways), math.ceil(15/10.0)+1)
        way_map = dict([(ww.get('id'), ww) for ww in ways])
        
        # <node>'s shouldn't be repeated
        nodes = w.tree.findall('/create/node')
        self.assertEqual(len(nodes), 15+3)
        node_map = dict([(nn.get('id'), nn) for nn in nodes])

        # Should be 1x Relation:MultiPolygon and no Relation:Collections
        self.assertEqual(len(w.tree.findall('/create/relation')), 1)
        rel = w.tree.find('/create/relation')
    
        rel_tags = rel.findall('tag')
        self.assertEqual(len(rel_tags), 2)
        self.assertEqual(rel_tags[0].get('k'), 'type')
        self.assertEqual(rel_tags[0].get('v'), 'multipolygon')
        self.assertEqual(rel_tags[1].get('k'), 'mytag')
        self.assertEqual(rel_tags[1].get('v'), 'myval')
        
        rel_members = rel.findall('member')
        self.assertEqual(len(rel_members), math.ceil(15/10.0)+1)
        counts = [0,0]
        for rm in rel_members:
            way = way_map.get(rm.get('ref'))
            self.assert_(way, "Couldn't find way for relation member %s" % rm.get('ref'))
            way_tags = way.findall('tag')
            if rm.get('role') == 'outer':
                counts[0] += 1
                self.assertEqual(len(way_tags), 1)
                self.assertEqual(way_tags[0].get('k'), 'mytag')
                self.assertEqual(way_tags[0].get('v'), 'myval')
            elif rm.get('role') == 'inner':
                counts[1] += 1
                self.assertEqual(len(way_tags), 0)
            else:
                self.assert_('unknown multipolygon role: %s' % rm.get('role'))
    
    def test_geom(self):
        geoms = (
        #   #nodes, #ways, #relations, #tags, geom
            (1, 0, 0, 1, geos.Point(0,0) ),
            (2, 1, 0, 1, geos.LineString([(0,0), (1,1)]) ),
            # polygons with a single ring are written as circular ways
            (3, 1, 0, 1, geos.Polygon([(0,0), (1,1), (2,0), (0,0)]) ),
            # otherwise they're written as relations
            # multipolygon relations have an extra tag
            # outer ways are tagged as well as the relation
            (6, 2, 1, 1*2+1, geos.Polygon([(0,0), (10,10), (20,0), (0,0)], [(8,2), (10,4), (12,2), (8,2)]) ),
            (2, 0, 0, 2, geos.MultiPoint(geos.Point(0,0), geos.Point(10,10)) ),
            (4, 2, 0, 2, geos.MultiLineString(
                geos.LineString([(0, 0), (1, 1)]), 
                geos.LineString([(10,10), (11,11)]) )),
            (8, 3, 1, 1*3+1, geos.MultiPolygon(
                geos.Polygon([(0,0), (1,1), (2,0), (0,0)]),
                geos.Polygon([(0,0), (10,10), (20,0), (0,0)], [(8,2), (10,4), (12,2), (8,2)]) )),
            # hmmm, should these share the same node? Currently not, because the node has different
            # tags from the node-within-a-way
            (3, 1, 0, 2, geos.GeometryCollection(
                geos.Point(0,0),
                geos.LineString([(0,0), (1,1)]) )),
        )
        
        for i, (node_count, way_count, relation_count, tag_count, geom) in enumerate(geoms):
            w = osm.OSMWriter()
            
            print "#%d: %s" % (i, geom.wkt)
            w.build_geom(geom, {'mytag':'myvalue'})
            print w.xml()
            
            self.assertEqual(len(w.tree.findall('/create/node')), node_count)
            self.assertEqual(len(w.tree.findall('/create/way')), way_count)
            self.assertEqual(len(w.tree.findall('/create/relation')), relation_count)
            self.assertEqual(len(w.tree.findall('//tag')), tag_count)
    
    def test_lake_regression(self):
        """ Somehow this polygon ended up anti-clockwise despite our code saying it was clockwise """
        wkt = "POLYGON((-176.590500983097 -44.1032059985506,-176.590826157482 -44.1032057400584,-176.590975034849 -44.1030982292722,-176.591110295501 -44.1029516776353,-176.591326959544 -44.1028734009898,-176.591543841875 -44.1029415675233,-176.591503422544 -44.1030880437545,-176.591449514585 -44.1032735877672,-176.591463410066 -44.1034981290891,-176.591829504537 -44.1036735674001,-176.592073419481 -44.1036928965764,-176.592317437321 -44.1037805710041,-176.592534404121 -44.1038975500978,-176.592683245869 -44.1037705113734,-176.592886450178 -44.1037508202332,-176.592900198064 -44.1038777269525,-176.592724258895 -44.1040047933522,-176.592697390605 -44.1041512589796,-176.592778882439 -44.1042781159401,-176.592995989965 -44.1044829603218,-176.592806500383 -44.1046100379534,-176.592820523658 -44.1049126822257,-176.592780197773 -44.1051177416111,-176.59271281941 -44.1053521116894,-176.592848727465 -44.1056156051798,-176.593269497402 -44.1060838924468,-176.593283369608 -44.1062889022197,-176.593053533611 -44.1066112767251,-176.592904976582 -44.1069238163687,-176.592918955045 -44.1071971718834,-176.593339413514 -44.1074604324769,-176.593651246823 -44.1075773344402,-176.593791339324 -44.107776187881,-176.593850338941 -44.1078091883573,-176.593915339135 -44.1078991880272,-176.593933339333 -44.1079681878048,-176.593920339477 -44.1081281876288,-176.593858339004 -44.1081861877062,-176.593637339038 -44.1082571882469,-176.593511339195 -44.10832718781,-176.593433339796 -44.1083841882781,-176.593436339444 -44.1085331882519,-176.59351733888 -44.1086121883531,-176.59353433914 -44.1086691878553,-176.593630339473 -44.1087371875448,-176.593887338959 -44.1088601877938,-176.593951339169 -44.1089171877473,-176.594031339738 -44.1089621874789,-176.594018338963 -44.109076188109,-176.594035339137 -44.1091221881454,-176.593956339269 -44.1091801881267,-176.59378233888 -44.1092041877662,-176.593623338969 -44.1091721880361,-176.593400339658 -44.1091511879705,-176.593338339482 -44.1092091877552,-176.593263339334 -44.1094041879459,-176.593296339067 -44.1094841879059,-176.593258014131 -44.109530666557,-176.593229827901 -44.1095394299233,-176.593027339674 -44.1095211879101,-176.592868339529 -44.1095221875389,-176.592804339387 -44.1095001880334,-176.592677339554 -44.1094901882015,-176.592420674955 -44.1091599629205,-176.592094860436 -44.1087697021081,-176.591823431204 -44.1084965527827,-176.591525229413 -44.1084284507613,-176.591199906061 -44.1083506081393,-176.59088825328 -44.1083508568506,-176.590787339433 -44.1085821880138,-176.590758339644 -44.1087311879172,-176.590577332307 -44.1088294960934,-176.590469156734 -44.1089760282044,-176.590418339771 -44.1091581881609,-176.590373339361 -44.109295188037,-176.590407339348 -44.1094321879536,-176.590300339101 -44.1096051877191,-176.590190339783 -44.1096861878909,-176.590032339462 -44.109722187881,-176.58992133941 -44.1097231880515,-176.589808339789 -44.10963318752,-176.589743339334 -44.109519187388,-176.58963033926 -44.1094401875936,-176.589615901866 -44.1092500686253,-176.589412563378 -44.1091916494729,-176.589223017958 -44.1092991925757,-176.588993339092 -44.1093321874459,-176.589054339926 -44.1091941874724,-176.589052339513 -44.1090911878697,-176.588969339624 -44.1089211881295,-176.588855339153 -44.1087621883362,-176.588977804385 -44.1084304665134,-176.588923106678 -44.1080985649662,-176.588733102971 -44.107893686528,-176.588286108278 -44.1080014281204,-176.587947771435 -44.1082750562594,-176.587826272354 -44.1085778068135,-176.587763339945 -44.1089101875273,-176.58767034001 -44.1090141876972,-176.587561340082 -44.1091061881962,-176.587515340146 -44.1091981881377,-176.587358339781 -44.1092911883499,-176.587312339923 -44.1093491881075,-176.587055021409 -44.1093301573422,-176.586797613228 -44.1093694058301,-176.586567262669 -44.1093695809592,-176.586215032281 -44.1094284265769,-176.585903239635 -44.1093310307797,-176.585591475289 -44.1092629227573,-176.585509695871 -44.1089310385588,-176.585509258659 -44.1086283820835,-176.585116214437 -44.1085603343697,-176.584750423588 -44.108609422758,-176.584384633104 -44.1086487469707,-176.584018428074 -44.1084049378895,-176.583841824359 -44.1080828865851,-176.583800594657 -44.1076728666556,-176.583325710129 -44.1072241100458,-176.58317640457 -44.1070387209977,-176.583270921437 -44.1068043368343,-176.583270221196 -44.1063064208137,-176.58347324087 -44.106150060486,-176.584109878663 -44.1060129065078,-176.58455674049 -44.1058173178377,-176.584583364739 -44.1054853483538,-176.584325388672 -44.1051047804156,-176.583918445391 -44.1047828989981,-176.583335631779 -44.1046466402072,-176.582942548054 -44.1045297718307,-176.58296942694 -44.104373540267,-176.583199607249 -44.1042659805623,-176.583768646929 -44.1042460327059,-176.584161355669 -44.104099299913,-176.584310268862 -44.1040015607231,-176.584743830561 -44.104001239417,-176.585082369247 -44.1038643011415,-176.585461523572 -44.1037175684734,-176.585773244379 -44.1037759173586,-176.586193426246 -44.1038927555711,-176.586464288452 -44.1038046842461,-176.586504906287 -44.1037851276551,-176.586708180441 -44.1038142620616,-176.586979585812 -44.1041069481881,-176.587481008457 -44.1041749050828,-176.587805978001 -44.1040379745302,-176.588253016456 -44.1039790466185,-176.588632214917 -44.1038615975633,-176.588997936603 -44.103792972357,-176.589255179051 -44.1036658481134,-176.58958028213 -44.1036167786107,-176.590067969235 -44.1035675799471,-176.590230323069 -44.1034112395896,-176.590365631014 -44.103293977484,-176.590500983097 -44.1032059985506))"
        poly = geos.GEOSGeometry(wkt)
        
        self.assert_(poly.simple)
        self.assert_(poly.valid)
        
        ring1 = poly[0]
        w = osm.OSMWriter(wind_polygons_ccw=False)
        w.WAY_SPLIT_SIZE = 10000
        print "Original orientation: ", ('cw' if w.ring_is_clockwise(ring1) else 'ccw')
        ring2 = w.wind_ring(ring1, True)
        print "Wound orientation: ", ('cw' if w.ring_is_clockwise(ring2) else 'ccw')
        
        self.assert_(w.ring_is_clockwise(ring2))
        
        w.build_geom(poly, {})
        print w.xml()
        way = w.tree.find('/create/way')
        node_map = dict([(nn.get('id'), nn) for nn in w.tree.findall('/create/node')])
        
        coords = []
        max_node_id = sys.maxint
        way_nodes = way.findall('nd')
        for i,nd in enumerate(way_nodes):
            node = node_map[nd.get('ref')]
            coords.append((float(node.get('lon')), float(node.get('lat'))))
            print i, nd.get('ref'), coords[-1]
            
            cur_node_id = int(node.get('id'))
            if i < len(way_nodes)-1: 
                self.assert_(max_node_id > cur_node_id, "seen an earlier node? %s/%s" % (max_node_id,cur_node_id))
            max_node_id = cur_node_id
        
        print coords
        print "Output orientation: ", ('cw' if w.ring_is_clockwise(coords) else 'ccw')
        self.assert_(w.ring_is_clockwise(coords))

    def test_reverse_line_coords(self):
        geom = geos.LineString([(0,0), (10,10), (20,20)])

        for do_reverse in (False,True):
            print "do_reverse=%s" % do_reverse
            w = osm.OSMWriter(reverse_line_coords=do_reverse)
            w.build_geom(geom, {})
            print w.xml()
        
            way = w.tree.find('/create/way')
            nodes = w.tree.findall('/create/node') 
            node_map = dict([(nn.get('id'), nn) for nn in nodes])
            
            coords = []
            for j,nd in enumerate(way.findall('nd')):
                n = node_map.get(nd.get('ref'))
                self.assert_(n is not None, "Node %s" % nd.get('ref'))
                
                c = (float(n.get('lon')), float(n.get('lat')))
                coords.append(c)
            
            if do_reverse:
                self.assertEqual(coords[0], (20,20))
                self.assertEqual(coords[-1], (0,0))
            else:
                self.assertEqual(coords[0], (0,0))
                self.assertEqual(coords[-1], (20,20))
            
