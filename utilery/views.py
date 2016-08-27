import json
import math

from . import config
from .core import DB, RECIPES, Handler, application
from .plugins import Plugins

import mercantile
import mapbox_vector_tile
from mapbox_vector_tile.encoder import on_invalid_geometry_make_valid


class Tile(Handler):

    SQL_TEMPLATE = "SELECT {way}, * FROM ({sql}) AS data WHERE ST_IsValid(way) AND ST_Intersects(way, {bbox})"  # noqa
    GEOMETRY = "{way}"
    methods = ['GET']
    RADIUS = 6378137
    CIRCUM = 2 * math.pi * RADIUS
    SIZE = 256

    async def __call__(self, req,  names, z, x, y, namespace='default'):
        self.zoom = int(z)
        self.x = int(x)
        self.y = int(y)
        self.ALL = names == 'all'
        self.names = names.split('+')
        bounds = mercantile.bounds(self.x, self.y, self.zoom)
        self.west, self.south = mercantile.xy(bounds.west, bounds.south)
        self.east, self.north = mercantile.xy(bounds.east, bounds.north)
        self.layers = []
        if namespace not in RECIPES:
            msg = 'Recipe "{}" not found. Available recipes are: {}'
            abort(400, msg.format(namespace, list(RECIPES.keys())))
        self.recipe = RECIPES[namespace]
        names = self.recipe.layers.keys() if self.ALL else self.names
        for name in names:
            if name not in self.recipe.layers:
                abort(400, u'Layer "{}" not found in recipe {}'.format(
                    name, namespace))
            await self.process_layer(self.recipe.layers[name])
        self.post_process()

        return self.content, 200, {"Content-Type": self.CONTENT_TYPE}

    async def process_layer(self, layer):
        layer_data = await self.query_layer(layer)
        self.add_layer_data(layer_data)

    async def query_layer(self, layer):
        features = []
        for query in layer.queries:
            if self.zoom < query.get('minzoom', 0) \
               or self.zoom > query.get('maxzoom', 22):
                continue
            sql = self.sql(query)
            try:
                rows = await DB.fetchall(sql, dbname=query.dbname)
            except Exception as e:
                msg = str(e)
                if config.DEBUG:
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


class PBF(Tile):

    endpoints = [
        '/{namespace}/{names}/{z}/{x}/{y}.pbf',
        '/{names}/{z}/{x}/{y}.pbf',
        '/{namespace}/{names}/{z}/{x}/{y}.mvt',
        '/{names}/{z}/{x}/{y}.mvt',
    ]
    SCALE = 4096
    CONTENT_TYPE = 'application/x-protobuf'

    @property
    def geometry(self):
        return ('ST_AsText(ST_TransScale(%s, %.12f, %.12f, %.12f, %.12f)) as _way'  # noqa
                % (self.GEOMETRY, -self.west, -self.south,
                self.SCALE / (self.east - self.west),
                self.SCALE / (self.north - self.south)))

    def post_process(self):
        self.content = mapbox_vector_tile.encode(
            self.layers,
            round_fn=round,
            on_invalid_geometry=on_invalid_geometry_make_valid)


class JSON(Tile):

    endpoints = [
        '/{namespace}/{names}/{z}/{x}/{y}.json',
        '/{names}/{z}/{x}/{y}.json',
    ]
    GEOMETRY = "ST_AsGeoJSON(ST_Transform({way}, 4326)) as _way"  # noqa
    CONTENT_TYPE = 'application/json'

    def post_process(self):
        self.content = json.dumps(self.layers)

    def process_geometry(self, geometry):
        return json.loads(geometry)


class GeoJSON(JSON):

    endpoints = [
        '/{namespace}/{names}/{z}/{x}/{y}.geojson',
        '/{names}/{z}/{x}/{y}.geojson',
    ]

    def to_layer(self, layer, features):
        return features

    def add_layer_data(self, data):
        self.layers.extend(data)

    def to_feature(self, row, layer):
        feature = super().to_feature(row, layer)
        feature["type"] = "Feature"
        feature['properties']['layer'] = layer['name']
        return feature

    def post_process(self):
        self.content = json.dumps({
            "type": "FeatureCollection",
            "features": self.layers
        })


class TileJson(Handler):

    endpoints = ['/tilejson/mvt.json']

    async def __call__(self, req):
        base = config.TILEJSON
        base['vector_layers'] = []
        for recipe in RECIPES.values():
            for layer in recipe.layers.values():
                base['vector_layers'].append({
                    "description": layer.description,
                    "id": layer.id
                })
        return json.dumps(base), 200, {}
