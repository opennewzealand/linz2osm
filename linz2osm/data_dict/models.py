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

import datetime
import decimal
import pydermonkey
import subprocess
import urllib
import sys

from functools import total_ordering

from django.db import models, connections, transaction
from django.db.models import Sum
from django.utils import text
from django.conf import settings
from django.contrib.gis.db import models as geomodels
from django.contrib.gis import geos
from django.contrib.auth.models import User

from linz2osm.utils.db_fields import JSONField
from linz2osm.convert import processing, osm

processor_list_html = '<ul class="help">' + ''.join(['<li><strong>%s</strong>: %s</li>' % p for p in sorted(processing.get_available().items())]) + '</ul>'

class Group(models.Model):
    name = models.CharField(max_length=255, unique=True, primary_key=True)
    description = models.TextField()

    def __str__(self):
        return self.name

class DatasetManager(models.Manager):
    def clear_datasets(self):
        # cascades and also drops LayerInDatasets
        Dataset.objects.all().delete()

    def generate_datasets(self):
        for name, details in settings.DATABASES.items():
            if name != 'default':
                if Dataset.objects.filter(name=name).exists():
                    dataset = Dataset.objects.get(name=name)
                else:
                    dataset = self.create(name = name,
                                          database_name = details['NAME'],
                                          description = details['_description'],
                                          srid = int(details['_srid']),
                                          version = details['_version'])

                for layer in Layer.objects.all():
                    if dataset.has_layer_in_schema(layer.name):
                        LayerInDataset.objects.create_layer_in_dataset(layer, dataset)


class Dataset(models.Model):
    UPDATE_METHOD_CHOICES = [
        ('manual', 'Manual'),
        ('lds', 'LINZ Data Service'),
        # ('wfs', 'WFS'),
        ]

    name = models.CharField(max_length=255, unique=True, primary_key=True)
    database_name = models.CharField(max_length=255)
    description = models.TextField()
    version = models.TextField(blank=True)
    srid = models.IntegerField()
    group = models.ForeignKey(Group, blank=True, null=True)
    update_method = models.CharField(max_length=255, choices=UPDATE_METHOD_CHOICES, default='manual')
    generating_deletions_osm = models.BooleanField(default=False, editable=False)

    def has_layer_in_schema(self, layer_name):
        cursor = connections[self.name].cursor()
        cursor.execute("SELECT true FROM pg_catalog.pg_tables WHERE schemaname='public' AND tablename=%s;", [layer_name])
        return (cursor.fetchone() is not None)

    def __unicode__(self):
        return unicode(self.description)

    @models.permalink
    def get_absolute_url(self):
        return ('linz2osm.data_dict.views.show_dataset', (), {'dataset_id': self.name})

    def get_max_update_version(self):
        yesterday = datetime.datetime.utcnow().date() - datetime.timedelta(1)
        return yesterday.strftime("%Y-%m-%d")

    def get_last_update_seq_no(self):
        return (self.datasetupdate_set.all().aggregate(models.Max('seq'))['seq__max'] or 0)

    def get_last_update(self):
        latest = self.datasetupdate_set.order_by('-seq')[:1]
        if latest:
            return latest[0]
        else:
            return None

    objects = DatasetManager()

class DatasetUpdateError(Exception):
    pass

class DatasetUpdate(models.Model):
    dataset = models.ForeignKey(Dataset)
    from_version = models.CharField(max_length=255, blank=True)
    to_version = models.CharField(max_length=255)
    seq = models.IntegerField()
    owner = models.ForeignKey(User)
    complete = models.BooleanField(default=False)
    error = models.TextField(blank=True, editable=False)

    def run(self):
        # FIXME: tests for changeset retrieval, etc.
        try:
            for lid in self.dataset.layerindataset_set.all():
                layer = lid.layer
                table_name = "%s_update_%s" % (layer.name, self.to_version.replace("-", "_"))
                import_proc = subprocess.Popen([
                        settings.LINZ2OSM_SCRIPT_ROOT + '/load_lds_dataset.sh',
                        'update',
                        self.dataset.database_name,
                        layer.wfs_type_name,
                        table_name,
                        settings.LINZ_DATA_SERVICE_API_KEY,
                        'from:%s;to:%s' % (self.from_version, self.to_version),
                        urllib.quote(layer.wfs_cql_filter)
                        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                import_proc.wait()
                import_output = import_proc.stdout.read()
                print import_output
                if import_proc.returncode != 0:
                    raise DatasetUpdateError("Import of %s failed with return code %d and output:\n%s" % (layer.name, import_proc.returncode, import_output))

                with transaction.commit_manually():
                    with transaction.commit_manually(using=self.dataset.name):
                        try:
                            osm.apply_changeset_to_dataset(self, table_name, lid)
                        except:
                            print "ERROR - ROLLBACK"
                            transaction.rollback(using=self.dataset.name)
                            transaction.rollback()
                            raise
                        else:
                            transaction.commit(using=self.dataset.name)
                            transaction.commit()
        except DatasetUpdateError as e:
            self.error = unicode(e)
        except Exception as e:
            print "Unexpected other exception:", sys.exc_info()[0]
            self.error = unicode(e)
            raise
        else:
            self.complete = True
            self.dataset.version = self.to_version
            self.dataset.save()
        finally:
            self.save()

class Layer(models.Model):
    GEOTYPE_CHOICES = [
        ('POINT', 'Point'),
        ('LINESTRING', 'Linestring'),
        ('POLYGON', 'Polygon'),
        ]
    PKEY_CHOICES = [
        ('ogc_fid', 'ogc_fid'),
        ('linz2osm_id', 'linz2osm_id'),
        ('id', 'id')
        ]

    name = models.CharField(max_length=100, primary_key=True)
    entity = models.CharField(max_length=200, blank=True, db_index=True)
    notes = models.TextField(blank=True)
    processors = JSONField(blank=True, null=True, help_text=('What geometry processors to apply. In the format [ ["name",{"arg":"value", ...}], ...]. Available processors:<br/>' + processor_list_html))
    datasets = models.ManyToManyField(Dataset, through='LayerInDataset')
    geometry_type = models.CharField(max_length=255, blank=True, choices=GEOTYPE_CHOICES)
    group = models.ForeignKey(Group, blank=True, null=True)
    pkey_name = models.CharField(max_length=255, default='ogc_fid', choices=PKEY_CHOICES, help_text='Changing this on an existing dataset requires an update to existing workslice features in database')
    tags_ql = models.TextField(blank=True, null=True, help_text=('What tags to include in the OSM search. Separated with whitespace. In OSM Overpass API format ["name"="value"] ["name"~"valueish"] ["name"="this|that"] ["name"!="not-this"] etc.'), verbose_name='tags for overpass QL')
    # FIXME: do this with a flag on the relevant tags?
    special_node_reuse_logic = models.BooleanField(default=False)
    special_start_node_field_name = models.CharField(max_length=255, blank=True, editable=False)
    special_end_node_field_name = models.CharField(max_length=255, blank=True, editable=False)
    special_node_tag_name = models.CharField(max_length=255, blank=True, editable=False)
    special_dataset_name_tag = models.CharField(max_length=255, blank=True, editable=False)
    special_dataset_version_tag = models.CharField(max_length=255, blank=True, editable=False)
    wfs_type_name = models.CharField(max_length=255, blank=True, verbose_name='WFS typeName', help_text='Used for LDS or WFS updates')
    wfs_cql_filter = models.TextField(max_length=255, blank=True, verbose_name='WFS cql_filter', help_text='Used for LDS or WFS updates')

    def __unicode__(self):
        return unicode(self.name)

    # This should only be needed for data_dict migration 0011:
    # the authoritative version is the geometry_type field.
    def deduce_geometry_type(self):
        end = self.name.rsplit('_', 1)[-1]
        if end in ('pnt', 'pnt2', 'name', 'text', 'feat'):
            return 'POINT'
        elif end in ('cl', 'edge', 'edg', 'coastline', 'contour'):
            return 'LINESTRING'
        elif end in ('poly',):
            return 'POLYGON'
        else:
            # unknown
            return None

    @property
    def feature_limit(self):
        if self.geometry_type == 'POINT':
            return 1000
        else:
            return 300

    @property
    def linz_dictionary_url(self):
        BASE_URL = "http://apps.linz.govt.nz/topo-data-dictionary/index.aspx?page=class-%s"
        return BASE_URL % self.name

    def layerindatasets_ordered(self):
        return self.layerindataset_set.order_by('dataset__description')

    def potential_tags(self):
        own_tags = self.tags.order_by('tag').all()
        groups = [lid.dataset.group for lid in self.layerindataset_set.all()] + [self.group]
        groupset = set([g for g in groups if g is not None])
        group_tags = [("Tags for group " + group.name, group.tags.order_by('tag').all()) for group in groupset]
        group_tags.sort(key=lambda group: group[0])
        default_tags = [t for t in Tag.objects.default() if t not in own_tags]
        default_tags.sort(key=lambda t: t.tag)

        return [("Tags specific to this layer", own_tags)] + group_tags + [("Default tags", default_tags)]

    def get_statistics(self, dataset_id=None):
        from linz2osm.convert.osm import get_layer_stats
        if dataset_id:
            return get_layer_stats(dataset_id, self)
        else:
            r = {}
            for ds in self.datasets.all():
                r[(ds.name, ds.description)] = get_layer_stats(ds.name, self)
            return r

    def get_processors(self):
        from linz2osm.convert.processing import get_class
        p_list = []
        if self.processors:
            for p_id,p_opts in self.processors:
                p_cls = get_class(p_id)
                p = p_cls(**p_opts)
                p_list.append(p)
        return p_list


class LayerInDatasetManager(geomodels.GeoManager):
    def create_layer_in_dataset(self, layer, dataset):
        stats = osm.get_layer_stats(dataset.name, layer)
        if LayerInDataset.objects.filter(layer=layer, dataset=dataset).exists():
            lid = LayerInDataset.objects.get(layer=layer, dataset=dataset)
            lid.features_total=stats['feature_count']
            lid.extent=stats['extent']
            lid.save()
        else:
            lid = self.create(layer=layer,
                              dataset=dataset,
                              features_total=stats['feature_count'],
                              extent=stats['extent']
                              )
        return lid

class LayerInDataset(geomodels.Model):
    objects = LayerInDatasetManager()

    dataset = geomodels.ForeignKey(Dataset)
    layer = geomodels.ForeignKey(Layer)
    features_total = geomodels.IntegerField()
    extent = geomodels.GeometryField(null=True)
    tagging_approved = geomodels.BooleanField(default=False)
    completed = geomodels.BooleanField(default=False)
    last_deletions_dump_filename = models.CharField(max_length=255, blank=True)

    def __unicode__(self):
        return "%s / %s" % (self.dataset.description, self.layer.name,)

    @property
    def translated_extent(self):
        extent_left, extent_right = [geos.Polygon(geos.LinearRing([(x + offset, y) for (x, y) in self.extent.coords[0]])) for offset in [-360, 360]]
        return geos.MultiPolygon(self.extent, extent_left, extent_right)

    @property
    def row_class(self):
        if self.completed:
            return "success"
        elif self.tagging_approved:
            return ""
        else:
            return "error"

    @property
    def hide_filters(self):
        for tag in self.layer.tags.all():
            if tag.is_conflict_search_tag:
                return False
        return True

    @property
    def filter_tag_names(self):
        return [tag.tag for tag in self.layer.tags.all() if tag.is_conflict_search_tag]

    @models.permalink
    def get_absolute_url(self):
        return ('linz2osm.workslices.views.create_workslice', (), {'layer_in_dataset_id': self.id})

    def get_conflict_tags(self):
        return [t for t in self.get_all_tags() if t.is_conflict_search_tag]

    def get_match_tags(self):
        return [t for t in self.get_all_tags() if t.match_search_tag]

    def get_all_tags(self):
        # if we override a default one, use the specific one
        # count tags with different apply_to values separately
        tags = dict([((t.tag, t.apply_to), t) for t in Tag.objects.default()])
        if self.dataset.group:
            for t in self.dataset.group.tags.all():
                tags[(t.tag, t.apply_to)] = t
        if self.layer.group:
            for t in self.layer.group.tags.all():
                tags[(t.tag, t.apply_to)] = t
        if self.layer:
            for t in self.layer.tags.all():
                tags[(t.tag, t.apply_to)] = t
        return sorted(tags.values(), key=lambda t: t.tag)

    def get_statistics_for(self, field_name):
        return osm.get_field_stats(self.dataset.name, self.layer, field_name)

    def js_display_bounds_array(self):
        min_x, min_y, max_x, max_y = [f for f in self.extent.extent]
        x_margin = (max_x - min_x) * 0.1
        y_margin = (max_y - min_y) * 0.1
        return unicode([min_x - x_margin, min_y - y_margin, max_x + x_margin, max_y + y_margin])

    def js_extent_geojson(self):
        return """ {
            "geometry": %s,
            "type": "Feature",
            "properties": {
                "model": "LayerInDataset"
            }
        } """ % self.extent.geojson

    def js_workslice_geojson(self):
        shown_workslices = self.workslice_set.filter(state__in=('processing','out','complete','blocked',))

        return """
            { "type": "FeatureCollection",
              "features": [%s],
              "crs": {
                  "type" : "name",
                  "properties" : {
                      "name" : "EPSG:4326"
                  }
              }
            }
        """ % ",".join([self.js_extent_geojson(), ",".join(ws.js_feature_geojson() for ws in shown_workslices)])

    def features_complete(self):
        return self.workslice_set.filter(state__in=('complete',)).aggregate(Sum('feature_count'))['feature_count__sum'] or 0

    def features_complete_pct(self):
        return (100.0 * self.features_complete() / self.features_total)

    def features_in_progress(self):
        return self.workslice_set.filter(state__in=('processing','out','blocked',)).aggregate(Sum('feature_count'))['feature_count__sum'] or 0

    def features_in_progress_pct(self):
        return (100.0 * self.features_in_progress() / self.features_total)

    def features_todo(self):
        return (self.features_total - self.features_complete() - self.features_in_progress()) or 0

    def features_todo_pct(self):
        return (100.0 * self.features_todo() / self.features_total)

    def deleted_features_count(self):
        return self.workslicefeature_set.filter(dirty=1).count()

    def export_deletes_name(self):
        return "deletes-%s-%s-%s" % (self.layer.name, self.dataset.name, datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S"))

class TagManager(models.Manager):
    def eval(self, code, fields):
        eval_fields = {}
        for fk,fv in fields.items():
            if isinstance(fv, decimal.Decimal):
                fv = float(fv)
            elif isinstance(fv, datetime.date):
                fv = str(fv)
            eval_fields[fk] = fv

        js = pydermonkey.Runtime().new_context()
        try:
            script = js.compile_script(code, '<Tag Code>', 1)

            context = js.new_object()
            js.init_standard_classes(context)

            js.define_property(context, 'value', None);
            context_fields = js.new_object()
            for fk,fv in eval_fields.items():
                js.define_property(context_fields, fk, fv)
            js.define_property(context, 'fields', context_fields)

            js.execute_script(context, script)

            value = js.get_property(context, 'value')
            if value is pydermonkey.undefined:
                value = None
            return value
        except (Exception,), e:
            e_msg = js.get_property(e.args[0], 'message')
            e_lineno = js.get_property(e.args[0], 'lineNumber')
            en = Tag.ScriptError("%s (line %d)" % (e_msg, e_lineno))
            en.data = eval_fields
            raise en

    def default(self):
        return self.get_query_set().filter(layer__isnull=True, group__isnull=True)

APPLY_TO_CHOICES = [
    (0, 'Geometries and relations'),
    (1, 'Geometries only'),
    (2, 'Relations only'),
    (3, 'First node only'),
    (4, 'Last node only'),
    (5, 'First and last nodes'),
]

CONFLICT_SEARCH_CHOICES = [
    (0, 'No'),
    (1, 'Filter exact matches'),
    (2, 'Filter partial match'),
    (3, 'Filter tag name only'),
]

@total_ordering
class Tag(models.Model):
    objects = TagManager()

    layer = models.ForeignKey(Layer, null=True, blank=True, related_name='tags')
    group = models.ForeignKey(Group, null=True, blank=True, related_name='tags')
    tag = models.CharField(max_length=100, help_text="OSM tag name")
    code = models.TextField(blank=True, help_text="Javascript code that sets the 'value' paramter to a non-null value to set the tag. 'fields' is an object with all available attributes for the current record")
    apply_to = models.IntegerField(default=0, choices=APPLY_TO_CHOICES)
    conflict_search_tag = models.IntegerField(default=0, choices=CONFLICT_SEARCH_CHOICES, verbose_name='Use this tag to search for conflicts in OSM')
    match_search_tag = models.BooleanField(default=False, verbose_name='Use this tag to track uploaded features in OSM')

    class Meta:
        unique_together = ('layer', 'apply_to', 'tag',)
        verbose_name = 'Default Tag'
        verbose_name_plural = 'Default Tags'

    class ScriptError(Exception):
        data = None

    def __unicode__(self):
        return self.tag

    def apply_for(self, cand):
        if cand == "first":
            return self.apply_to in [3, 5]
        elif cand == "last":
            return self.apply_to in [4, 5]
        elif cand == "geometry":
            return self.apply_to in [0, 1]
        elif cand == "relation":
            return self.apply_to in [0, 2]
        else:
            return True

    def eval(self, fields):
        return Tag.objects.eval(self.code, fields)

    def eval_for_match_filter(self, fields):
        v = Tag.objects.eval(self.code, fields)
        return '["%s"="%s"]' % (self.tag, v)

    def eval_for_conflict_filter(self, fields):
        if self.conflict_search_tag == 0:
            return None
        elif self.conflict_search_tag == 3:
            return '["%s"]' % self.tag
        else:
            v = Tag.objects.eval(self.code, fields)
            if self.conflict_search_tag == 1:
                return '["%s"="%s"]' % (self.tag, v)
            elif self.conflict_search_tag == 2:
                return '["%s"~"%s"]' % (self.tag, v)
            else:
                return None

    @property
    def is_conflict_search_tag(self):
        return self.conflict_search_tag != 0

    def __lt__(self, other):
        if other.layer_id:
            if not self.layer_id:
                return False
        else:
            if self.layer_id:
                return True
        if other.tag.startswith("LINZ:"):
            if not self.tag.startswith("LINZ:"):
                return True
        else:
            if self.tag.startswith("LINZ:"):
                return False
        return self.tag.__lt__(other.tag)

