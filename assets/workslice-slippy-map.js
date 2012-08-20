/**
 *  LINZ-2-OSM
 *  Copyright (C) 2010-2012 Koordinates Ltd.
 * 
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.
**/

function WorksliceSlippyMap(map_id, bounds_ary, checkouts_geojson, highlight_id) {
    var self = this;
    this.map = null;
    var wgs84 = new OpenLayers.Projection("EPSG:4326");
    var smp = new OpenLayers.Projection("EPSG:900913");

    function loadMap(bounds_ary) {
        var osm = new OpenLayers.Layer.OSM("Mapnik");
        var extent = new OpenLayers.Bounds(bounds_ary).transform(wgs84, smp);

        var options = {
            restrictedExtent: extent,
            extent: extent,
            displayProjection: wgs84,
            projection: smp,
            controls: [
                new OpenLayers.Control.Navigation(),
                new OpenLayers.Control.PanZoomBar(),
                new OpenLayers.Control.Attribution(),
                new OpenLayers.Control.ScaleLine(),
                new OpenLayers.Control.MousePosition(),
                new OpenLayers.Control.KeyboardDefaults(),
            ]
        };
    
        self.map = new OpenLayers.Map(map_id, options);

        self.map.addLayer(osm);
        self.map.zoomToMaxExtent({restricted: true});
    };

    loadMap(bounds_ary);

    var highlightColouringRules = [
        new OpenLayers.Rule({
            filter: new OpenLayers.Filter.Comparison({
                type: OpenLayers.Filter.Comparison.EQUAL_TO,
                property: "model",
                value: "LayerInDataset"
            }),
            symbolizer: {
                strokeOpacity: 0,
                fillOpacity: 0
            }
        }),
        new OpenLayers.Rule({
            filter: new OpenLayers.Filter.Comparison({
                type: OpenLayers.Filter.Comparison.EQUAL_TO,
                property: "id",
                value: highlight_id
            }),
            symbolizer: {
                strokeColor: '#ff0000',
                fillColor: '#ff0000'
            }
        }),
        new OpenLayers.Rule({
            elseFilter: true,
            symbolizer: {
                strokeColor: '#777777',
                fillColor: '#777777'
            }
        })
    ];
    
    var CHECKOUT_COLOURING_RULES = [
        new OpenLayers.Rule({
            filter: new OpenLayers.Filter.Comparison({
                type: OpenLayers.Filter.Comparison.EQUAL_TO,
                property: "model",
                value: "LayerInDataset"
            }),
            symbolizer: {
                strokeColor: '#777777',
                fillColor: '#777777'
            }
        }),
        new OpenLayers.Rule({
            filter: new OpenLayers.Filter.Comparison({
                type: OpenLayers.Filter.Comparison.EQUAL_TO,
                property: "state",
                value: "complete"
            }),
            symbolizer: {
                strokeColor: '#00ff00',
                fillColor: '#00ff00'
            }
        }),
        new OpenLayers.Rule({
            filter: new OpenLayers.Filter.Comparison({
                type: OpenLayers.Filter.Comparison.EQUAL_TO,
                property: "state",
                value: "out"
            }),
            symbolizer: {
                strokeColor: '#0000ff',
                fillColor: '#0000ff'
            }
        }),
        new OpenLayers.Rule({
            filter: new OpenLayers.Filter.Comparison({
                type: OpenLayers.Filter.Comparison.EQUAL_TO,
                property: "state",
                value: "processing"
            }),
            symbolizer: {
                strokeColor: '#0000ff',
                fillColor: '#0000ff'
            }
        }),
        new OpenLayers.Rule({
            filter: new OpenLayers.Filter.Comparison({
                type: OpenLayers.Filter.Comparison.EQUAL_TO,
                property: "state",
                value: "blocked"
            }),
            symbolizer: {
                strokeColor: '#ff0000',
                fillColor: '#ff0000'
            }
        }),
        new OpenLayers.Rule({
            elseFilter: true,
            symbolizer: {
                strokeColor: '#aa5566',
                fillColor: '#aa5566'
            }
        })
    ];

    function addFeatures(geojson) {
        var featureRules;
        if(highlight_id !== undefined) {
            featureRules = highlightColouringRules;
        } else {
            featureRules = CHECKOUT_COLOURING_RULES;
        }
        
        var geojson_format = new OpenLayers.Format.GeoJSON({
            internalProjection: smp,
            externalProjection: wgs84
        });
        var style = new OpenLayers.Style(
            {
                strokeOpacity: 0.8,
                strokeWidth: 2,
                fillOpacity: 0.3
            },{
                rules: featureRules
            }
        );
        var checkouts_layer = new OpenLayers.Layer.Vector('Checkouts', {
            /* projection: wgs84, */
            styleMap: new OpenLayers.StyleMap(style),
        });
        checkouts_layer.addFeatures(geojson_format.read(geojson));
        self.map.addLayer(checkouts_layer);
    }

    addFeatures(checkouts_geojson);

    /* Cell Selection and hovering */
    
    var clickControl;
    var selecting_cells = false;
    var cells = new CellCollection();
    var highlighted_cell;
    var currentCellDensity = 128;
    var selection;
    var hover;
    var selection_layer;
    var hover_layer;
        
    function Cell(test_lon, test_lat, cpd) {
        var self = this;

        this.x = Math.floor(test_lon * cpd)
        this.y = Math.floor(test_lat * cpd)
        this.cpd = cpd;
        
        this.lon = self.x / self.cpd;
        this.lat = self.y / self.cpd;
        this.size = 1.0 / cpd;
        
        this.toString = function() {
            return "X" + self.x + "Y" + self.y + "C" + self.cpd;
        }

        this.description = function() {
            return self.lon + ", " + self.lat + ", " + self.size + " (" + self.cpd + ").";
        }

        function boundsWGS84() {
            return [
                new OpenLayers.Geometry.Point(self.lon, self.lat),
                new OpenLayers.Geometry.Point(self.lon, self.lat + self.size),
                new OpenLayers.Geometry.Point(self.lon + self.size, self.lat + self.size),
                new OpenLayers.Geometry.Point(self.lon + self.size, self.lat)
            ];
        }

        this.displayGeometry = function() {
            return new OpenLayers.Geometry.Polygon([
                new OpenLayers.Geometry.LinearRing(boundsWGS84())
            ]).transform(wgs84, smp);
        }

        this.equals = function(other) {
            return self.x === other.x && self.y === other.y && self.cpd === other.cpd;
        }
    }

    this.getCells = function() {
        return cells;
    }
    
    function CellCollection() {
        var self = this;
        var contents = new Array();

        this.contains = function(cell) {
            var len = contents.length;
            for(var i = 0; i < len; ++i) {
                if(contents[i].equals(cell)) {
                    return i;
                }
            }
            return false;
        }

        this.clear = function() {
            contents = new Array();
            selection_layer.destroyFeatures();
            updateCellSelectionInformation();
            $("input#id_cells").val(cells.toString());
        }

        this.updateFeatureCount = function() {
            if(contents.length > 0) {
                $("#feature-selection-ajax-indicator").show();
                $.post(
                    $("#feature-count-form").attr('action'),
                    $("#grab-some-data-form").serialize(),
                    function(data, textStatus, jqXHR) {
                        $("#feature-selection-information").html(data.info);
                        $("#feature-selection-ajax-indicator").hide();
                    },
                    'json'
                )
            }
        };
        
        function updateCellSelectionInformation() {
            var len = contents.length;
            var msg = "";
            
            if(len <= 0) {
                msg = "Select at least one cell from the map. ";
            } else if(len === 1) {
                msg = "1 cell selected. ";
            } else {
                msg = contents.length + " cells selected. ";
            }
            $("#cell-selection-information").html(msg);
            $("#feature-selection-information").html('');
        }
        
        /* FIXME: speed up adding cell */
        var add = function(cell) {
            cell.feature = new OpenLayers.Feature.Vector(cell.displayGeometry());
            selection_layer.addFeatures([cell.feature]);
            return contents.push(cell);
        };

        var remove = function(idx) {
            var cell = contents.splice(idx, 1)[0];
            selection_layer.destroyFeatures([cell.feature]);
        };

        /* TODO: restrict ability to add non-contiguous cells */
        this.addOrRemove = function(cell) {
            var retval;
            var idx = self.contains(cell);
            if(idx === false) {
                retval = add(cell);
            } else {
                retval = remove(idx);
            }
            updateCellSelectionInformation();
            $("input#id_cells").val(cells.toString());
            self.updateFeatureCount();
            return retval;
        };

        this.toString = function() {
            return $.map(contents, function(cell, idx) {
                return cell.toString();
            }).join("_");
        };
    }
    
    OpenLayers.Control.Click = OpenLayers.Class(OpenLayers.Control, {
        defaultHandlerOptions: {
            'single': true,
            'double': false,
            'pixelTolerance': 0,
            'stopSingle': false,
            'stopDouble': false
        },

        initialize: function(options) {
            this.handlerOptions = OpenLayers.Util.extend(
                {},
                this.defaultHandlerOptions
            );
            OpenLayers.Control.prototype.initialize.apply(this, arguments);
            this.handler = new OpenLayers.Handler.Click(
                this, {
                    'click': this.trigger
                },
                this.handlerOptions
            );
        },

        trigger: function(e) {
            var lonlat = self.map.getLonLatFromPixel(e.xy).transform(smp, wgs84);
            var cell = new Cell(lonlat.lon, lonlat.lat, currentCellDensity);
            cells.addOrRemove(cell);
        }
    });
    
    selection = new OpenLayers.Control.Click({
        'pixelTolerance': 2
    });
    selection.key = 'cell-selection';
    this.map.addControl(selection);
    
    selection_layer = new OpenLayers.Layer.Vector('Selected Cells', {
        style: {
            strokeOpacity: 0,
            strokeWidth: 0,
            fillOpacity: 0.5,
            fillColor: '#ff7700'
        }
    });
    this.map.addLayer(selection_layer);

    OpenLayers.Control.Hover = OpenLayers.Class(OpenLayers.Control, {                
        defaultHandlerOptions: {
            'delay': 2,
            'pixelTolerance': null,
            'stopMove': false
        },
        
        initialize: function(options) {
            this.handlerOptions = OpenLayers.Util.extend(
                {}, this.defaultHandlerOptions
            );
            OpenLayers.Control.prototype.initialize.apply(
                this, arguments
            ); 
            this.handler = new OpenLayers.Handler.Hover(
                this,
                {'pause': this.onPause, 'move': this.onMove},
                this.handlerOptions
            );
        }, 

        onPause: function(e) {
            var lonlat = self.map.getLonLatFromPixel(e.xy).transform(smp, wgs84);
            var cell = new Cell(lonlat.lon, lonlat.lat, currentCellDensity);
            highlightCell(cell);
        },
        
        onMove: function(evt) {
            // if this control sent an Ajax request (e.g. GetFeatureInfo) when
            // the mouse pauses the onMove callback could be used to abort that
            // request.
        }
    });

    hover = new OpenLayers.Control.Hover({
        handlerOptions: {
            'delay': 2
        }
    });
    hover.key = 'cell-hoverer';
    this.map.addControl(hover);

    hover_layer = new OpenLayers.Layer.Vector('Highlighted Cell', {
        style: {
            strokeOpacity: 1,
            strokeWidth: 2,
            strokeColor: '#ff7700',
            fillOpacity: 0,
        }
    });
    this.map.addLayer(hover_layer);

    this.map.events.register('zoomend', self, function() {
        if(selecting_cells) {
            updateCellDensityAndSelection();
        }
        generateOSMLink();
    });

    this.map.events.register('moveend', self, function() {
        generateOSMLink();
    });

    function generateOSMLink() {
        extent = self.map.getExtent().transform(smp, wgs84);
        link = 'http://www.openstreetmap.org/index.html?minlon=' + extent.left +
            '&maxlon=' + extent.right +
            '&minlat=' + extent.bottom +
            '&maxlat=' + extent.top +
            '&box=yes';
        $("a#osm-link").attr('href', link);
    }
    
    /* TODO: highlight red when about to delete a cell */
    function highlightCell(cell) {
        if (!highlighted_cell || cell.toString() != highlighted_cell.toString()) {
            hover_layer.destroyFeatures();
            hover_layer.addFeatures([new OpenLayers.Feature.Vector(cell.displayGeometry())]);
        }
        highlighted_cell = cell;
    }
    
    function getWGSExtent() {
        return self.map.getExtent().transform(smp, wgs84);
    }

    function getMinimumSizeDegrees() {
        var extent = getWGSExtent();
        var height = extent.top - extent.bottom;
        var width = extent.right - extent.left;
        return Math.min(height, width);
    }

    function roundup(val, next) {
        return Math.ceil(val / next) * next;
    }
    
    function calculateCellDensity() {
        var target = 4.0 / getMinimumSizeDegrees(); // have at least 4 cells
        var power = Math.log(target) / Math.log(2);
        // Next highest even power of 2.
        return Math.max(Math.pow(2, roundup(power, 2)), 1);
    }
    
    function updateCellDensityAndSelection() {
        var newCellDensity = calculateCellDensity();
        if (newCellDensity > currentCellDensity) {
            cells.clear();
            // FIXME: resize 
        } else if (newCellDensity < currentCellDensity) {
            cells.clear();
        }
        currentCellDensity = newCellDensity;
    }

    this.startGrabbingData = function() {
        selecting_cells = true;
        /* FIXME: initialize cells from cells input field populated by server */
        cells.clear();
        updateCellDensityAndSelection();
        selection.activate();
        hover.activate();
                
        $("#grab-some-data-view-mode").hide();
        $("#grab-some-data-select-mode").show();
    };

    this.stopGrabbingData = function() {
        selecting_cells = false;
        selection.activate();
        hover.deactivate();
        hover_layer.destroyFeatures();
        cells.clear();
        
        $("#grab-some-data-select-mode").hide();
        $("#grab-some-data-view-mode").show();
    };
        
    $("#grab-some-data-start").click(function(event) {
        event.preventDefault();
        self.startGrabbingData();
    });
    
    $("#grab-some-data-cancel").click(function(event) {
        event.preventDefault();
        self.stopGrabbingData();
    });

    $("#grab-some-data-reset").click(function(event) {
        event.preventDefault();
        cells.clear();
    });
    generateOSMLink();
}

