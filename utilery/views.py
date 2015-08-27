# -*- coding: utf-8 -*-

import json
import math
# from pathlib import Path

from flask import abort
from flask.views import View

from .core import app, DB, LAYERS

import mercantile
import mapbox_vector_tile


class ServeTile(View):

    SQL_TEMPLATE = "SELECT {way}, * FROM ({sql}) AS data WHERE ST_IsValid(way) AND ST_Intersects(way, {bbox})"  # noqa
    GEOMETRY = "{way}"
    methods = ['GET']
    RADIUS = 6378137
    CIRCUM = 2 * math.pi * RADIUS
    SIZE = 256

    def dispatch_request(self, names, z, x, y):
        self.zoom = z
        self.ALL = names == 'all'
        self.names = names.split('+')
        self.x = x
        self.y = y
        return self.serve()

    def serve(self):
        bounds = mercantile.bounds(self.x, self.y, self.zoom)
        self.west, self.south = mercantile.xy(bounds.west, bounds.south)
        self.east, self.north = mercantile.xy(bounds.east, bounds.north)
        self.layers = []
        names = LAYERS.keys() if self.ALL else self.names
        for name in names:
            if ':' not in name:
                name = 'default:%s' % name
            if name not in LAYERS:
                abort(400, u'Layer "{}" not found'.format(name))
            layer_data = self.query_layer(LAYERS[name])
            self.add_layer_data(layer_data)
        self.post_process()

        return self.content, 200, {"Content-Type": self.CONTENT_TYPE}

    def query_layer(self, layer):
        features = []
        for query in layer['queries']:
            if self.zoom < query.get('minzoom', 0) \
               or self.zoom > query.get('maxzoom', 22):
                continue
            rows = DB.fetchall(self.sql(query, layer),
                               dbname=query.get('dbname'))
            features += [self.to_feature(row, layer) for row in rows]
        return self.to_layer(layer, features)

    def key(self, name, default, query, layer):
        return query.get(name, layer.get(name, default))

    def sql(self, query, layer):
        srid = self.key('srid', '900913', query, layer)
        bbox = 'ST_SetSRID(ST_MakeBox2D(ST_MakePoint({west}, {south}), ST_MakePoint({east}, {north})), {srid})'  # noqa
        bbox = bbox.format(west=self.west, south=self.south, east=self.east,
                           north=self.north, srid=srid)
        scale = self.key('scale', 1, query, layer)
        pixel_width = self.CIRCUM / (self.SIZE * scale) / 2 ** self.zoom
        buffer = self.key('buffer', 0, query, layer)
        if buffer:
            units = buffer * pixel_width
            bbox = 'ST_Expand({bbox}, {units})'.format(bbox=bbox, units=units)
        geometry = self.geometry
        clip = self.key('clip', False, query, layer)
        if clip:
            geometry = geometry.format(way='ST_Intersection({way}, {bbox})')
        geometry = geometry.format(way='way', bbox=bbox)
        sql = query['sql'].replace('!bbox!', bbox)
        sql = sql.replace('!zoom!', str(self.zoom))
        sql = sql.replace('!pixel_width!', str(pixel_width))
        return self.SQL_TEMPLATE.format(way=geometry, sql=sql, bbox=bbox)

    def to_layer(self, layer, features):
        return {
            "name": layer['name'],
            "features": features
        }

    def add_layer_data(self, data):
        self.layers.append(data)

    def to_feature(self, row, layer):
        return {
            "geometry": self.process_geometry(row['_way']),
            "properties": self.row_to_dict(row)
        }

    def row_to_dict(self, row):
        def f(item):
            return not item[0].startswith('_') and item[0] != 'way'
        return dict(i for i in row.items() if f(i))

    def process_geometry(self, geometry):
        return geometry

    @property
    def geometry(self):
        return self.GEOMETRY


class ServePBF(ServeTile):

    SCALE = 4096
    CONTENT_TYPE = 'application/x-protobuf'

    @property
    def geometry(self):
        return ('ST_AsText(ST_TransScale(%s, %.12f, %.12f, %.12f, %.12f)) as _way'  # noqa
                % (self.GEOMETRY, -self.west, -self.south,
                self.SCALE / (self.east - self.west),
                self.SCALE / (self.north - self.south)))

    def post_process(self):
        self.content = mapbox_vector_tile.encode(self.layers)

serve_pbf = ServePBF.as_view('serve_pbf')
app.add_url_rule('/<names>/<int:z>/<int:x>/<int:y>.pbf',
                 view_func=serve_pbf)
app.add_url_rule('/<names>/<int:z>/<int:x>/<int:y>.mvt',
                 view_func=serve_pbf)


class ServeJSON(ServeTile):

    GEOMETRY = "ST_AsGeoJSON(ST_Transform({way}, 4326)) as _way"  # noqa
    CONTENT_TYPE = 'application/json'

    def post_process(self):
        self.content = json.dumps(self.layers)

    def process_geometry(self, geometry):
        return json.loads(geometry)

app.add_url_rule('/<names>/<int:z>/<int:x>/<int:y>.json',
                 view_func=ServeJSON.as_view('servejson'))


class ServeGeoJSON(ServeJSON):

    def to_layer(self, layer, features):
        return features

    def add_layer_data(self, data):
        self.layers.extend(data)

    def to_feature(self, row, layer):
        feature = super(ServeGeoJSON, self).to_feature(row, layer)
        feature["type"] = "Feature"
        feature['properties']['layer'] = layer['name']
        return feature

    def post_process(self):
        self.content = json.dumps({
            "type": "FeatureCollection",
            "features": self.layers
        })

app.add_url_rule('/<names>/<int:z>/<int:x>/<int:y>.geojson',
                 view_func=ServeGeoJSON.as_view('servegeojson'))
