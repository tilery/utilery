import json
import math

import psycopg2

from flask import abort
from flask.views import View

from .core import app, DB, RECIPES

import mercantile
import mapbox_vector_tile


class ServeTile(View):

    SQL_TEMPLATE = "SELECT {way}, * FROM ({sql}) AS data WHERE ST_IsValid(way) AND ST_Intersects(way, {bbox})"  # noqa
    GEOMETRY = "{way}"
    methods = ['GET']
    RADIUS = 6378137
    CIRCUM = 2 * math.pi * RADIUS
    SIZE = 256

    def dispatch_request(self, recipe, names, z, x, y):
        self.namespace = recipe or "default"
        self.zoom = z
        self.ALL = names == "all"
        self.names = names.split('+')
        self.x = x
        self.y = y
        return self.serve()

    def serve(self):
        bounds = mercantile.bounds(self.x, self.y, self.zoom)
        self.west, self.south = mercantile.xy(bounds.west, bounds.south)
        self.east, self.north = mercantile.xy(bounds.east, bounds.north)
        self.layers = []
        if self.namespace not in RECIPES:
            msg = 'Recipe "{}" not found. Available recipes are: {}'
            abort(400, msg.format(self.namespace, list(RECIPES.keys())))
        self.recipe = RECIPES[self.namespace]
        names = self.recipe.layers.keys() if self.ALL else self.names
        for name in names:
            if name not in self.recipe.layers:
                abort(400, u'Layer "{}" not found in recipe {}'.format(
                    name, self.namespace))
            self.process_layer(self.recipe.layers[name])
        self.post_process()

        return self.content, 200, {"Content-Type": self.CONTENT_TYPE}

    def process_layer(self, layer):
        layer_data = self.query_layer(layer)
        self.add_layer_data(layer_data)

    def query_layer(self, layer):
        features = []
        for query in layer.queries:
            if self.zoom < query.get('minzoom', 0) \
               or self.zoom > query.get('maxzoom', 22):
                continue
            sql = self.sql(query)
            try:
                rows = DB.fetchall(sql, dbname=query.dbname)
            except (psycopg2.ProgrammingError, psycopg2.InternalError) as e:
                msg = str(e)
                if app.debug:
                    msg = "{} ** Query was: {}".format(msg, sql)
                abort(500, msg)
            features += [self.to_feature(row, layer) for row in rows]
        return self.to_layer(layer, features)

    def sql(self, query):
        srid = query.srid
        bbox = 'ST_SetSRID(ST_MakeBox2D(ST_MakePoint({west}, {south}), ST_MakePoint({east}, {north})), {srid})'  # noqa
        bbox = bbox.format(west=self.west, south=self.south, east=self.east,
                           north=self.north, srid=srid)
        pixel_width = self.CIRCUM / (self.SIZE * query.scale) / 2 ** self.zoom
        if query.buffer:
            units = query.buffer * pixel_width
            bbox = 'ST_Expand({bbox}, {units})'.format(bbox=bbox, units=units)
        geometry = self.geometry
        if query.clip:
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
app.add_url_rule('/<recipe>/<names>/<int:z>/<int:x>/<int:y>.pbf',
                 view_func=serve_pbf)
app.add_url_rule('/<recipe>/<names>/<int:z>/<int:x>/<int:y>.mvt',
                 view_func=serve_pbf)
app.add_url_rule('/<names>/<int:z>/<int:x>/<int:y>.pbf',
                 view_func=serve_pbf, defaults={"recipe": None})
app.add_url_rule('/<names>/<int:z>/<int:x>/<int:y>.mvt',
                 view_func=serve_pbf, defaults={"recipe": None})


class ServeJSON(ServeTile):

    GEOMETRY = "ST_AsGeoJSON(ST_Transform({way}, 4326)) as _way"  # noqa
    CONTENT_TYPE = 'application/json'

    def post_process(self):
        self.content = json.dumps(self.layers)

    def process_geometry(self, geometry):
        return json.loads(geometry)

serve_json = ServeJSON.as_view('serve_json')
app.add_url_rule('/<recipe>/<names>/<int:z>/<int:x>/<int:y>.json',
                 view_func=serve_json)
app.add_url_rule('/<names>/<int:z>/<int:x>/<int:y>.json',
                 view_func=serve_json,
                 defaults={"recipe": None})


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

serve_geojson = ServeGeoJSON.as_view('serve_geojson')
app.add_url_rule('/<recipe>/<names>/<int:z>/<int:x>/<int:y>.geojson',
                 view_func=serve_geojson)
app.add_url_rule('/<names>/<int:z>/<int:x>/<int:y>.geojson',
                 view_func=serve_geojson,
                 defaults={"recipe": None})


@app.route('/tilejson/mvt.json')
def tilejson():
    base = app.config['TILEJSON']
    base['vector_layers'] = []
    for recipe in RECIPES.values():
        for layer in recipe.layers.values():
            base['vector_layers'].append({
                "description": layer.description,
                "id": layer.id
            })
    return json.dumps(base)
