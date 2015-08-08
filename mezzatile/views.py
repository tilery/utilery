# -*- coding: utf-8 -*-

import json
# from pathlib import Path

from flask.views import View

from . import app, DB, LAYERS

import mercantile
import mapbox_vector_tile


class ServeTile(View):

    SQL_TEMPLATE = "SELECT {geometry}, * FROM ({sql}) AS data WHERE way && {bbox}"  # noqa
    GEOMETRY = "way"  # noqa
    methods = ['GET']

    def dispatch_request(self, layers, z, x, y):
        self.zoom = z
        self.names = layers
        self.x = x
        self.y = y
        return self.serve()

    def serve(self):
        bounds = mercantile.bounds(self.x, self.y, self.zoom)
        self.west, self.south = mercantile.xy(bounds.west, bounds.south)
        self.east, self.north = mercantile.xy(bounds.east, bounds.north)
        self.layers = []
        for layer in LAYERS['layers']:
            layer_data = self.query_layer(layer)
            self.add_layer_data(layer_data)
        self.post_process()

        return self.content, 200, {"Content-Type": self.CONTENT_TYPE}

    def query_layer(self, layer):
        features = []
        srid = '900913'
        bbox = 'ST_SetSRID(ST_MakeBox2D(ST_MakePoint({west}, {south}), ST_MakePoint({east}, {north})), {srid})'  # noqa
        bbox = bbox.format(west=self.west, south=self.south, east=self.east,
                           north=self.north, srid=srid)
        for query in layer['queries']:
            if self.zoom < query['minzoom'] or self.zoom > query['maxzoom']:
                continue
            sql = query['sql'].replace('!bbox!', bbox)
            sql = sql.replace('!zoom!', str(self.zoom))
            sql = self.SQL_TEMPLATE.format(
                geometry=self.geometry,
                sql=sql,
                bbox=bbox)
            features += [self.to_feature(r, layer) for r in DB.fetchall(sql)]
        return self.to_layer(layer, features)

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
            "properties": dict(row.items())
        }

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
app.add_url_rule('/<layers>/<int:z>/<int:x>/<int:y>.pbf',
                 view_func=serve_pbf)
app.add_url_rule('/<layers>/<int:z>/<int:x>/<int:y>.mvt',
                 view_func=serve_pbf)


class ServeJSON(ServeTile):

    GEOMETRY = "ST_AsGeoJSON(ST_Transform(way, 4326)) as _way"  # noqa
    CONTENT_TYPE = 'application/json'

    def post_process(self):
        self.content = json.dumps(self.layers)

    def process_geometry(self, geometry):
        return json.loads(geometry)

app.add_url_rule('/<layers>/<int:z>/<int:x>/<int:y>.json',
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

app.add_url_rule('/<layers>/<int:z>/<int:x>/<int:y>.geojson',
                 view_func=ServeGeoJSON.as_view('servegeojson'))
