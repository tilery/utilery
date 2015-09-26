import json
import math

import psycopg2

from werkzeug.exceptions import BadRequest, HTTPException, abort
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request, Response

from . import config
from .core import DB, RECIPES
from .plugins import Plugins

import mercantile
import mapbox_vector_tile


url_map = Map([
    Rule('/<recipe>/<names>/<int:z>/<int:x>/<int:y>.pbf', endpoint='pbf'),
    Rule('/<names>/<int:z>/<int:x>/<int:y>.pbf', endpoint='pbf'),
    Rule('/<recipe>/<names>/<int:z>/<int:x>/<int:y>.mvt', endpoint='pbf'),
    Rule('/<names>/<int:z>/<int:x>/<int:y>.mvt', endpoint='pbf'),
    Rule('/<recipe>/<names>/<int:z>/<int:x>/<int:y>.json', endpoint='json'),
    Rule('/<names>/<int:z>/<int:x>/<int:y>.json', endpoint='json'),
    Rule('/<recipe>/<names>/<int:z>/<int:x>/<int:y>.geojson', endpoint='geojson'),  # noqa
    Rule('/<names>/<int:z>/<int:x>/<int:y>.geojson', endpoint='geojson'),
    Rule('/tilejson/mvt.json', endpoint='tilejson'),
])


def app(environ, start_response):
    urls = url_map.bind_to_environ(environ)
    try:
        endpoint, kwargs = urls.match()
        request = Request(environ)
        response = Plugins.hook('request', endpoint=endpoint, request=request,
                                **kwargs)
        if not response:
            response = View.serve(endpoint, request, **kwargs)
        if isinstance(response, tuple):
            response = Response(*response)
        elif isinstance(response, str):
            response = Response(response)
    except HTTPException as e:
        return e(environ, start_response)
    else:
        response = Plugins.hook('response', response=response, request=request) or response  # noqa
        return response(environ, start_response)


class WithEndPoint(type):

    endpoints = {}

    def __new__(mcs, name, bases, attrs, **kwargs):
        cls = super().__new__(mcs, name, bases, attrs)
        if hasattr(cls, 'endpoint'):
            mcs.endpoints[cls.endpoint] = cls
        return cls


class View(object, metaclass=WithEndPoint):

    def __init__(self, request):
        self.request = request

    @classmethod
    def serve(cls, endpoint, request, **kwargs):
        Class = WithEndPoint.endpoints.get(endpoint)
        if not Class:
            raise BadRequest()
        view = Class(request)
        if view.request.method == 'GET' and hasattr(view, 'get'):
            response = view.get(**kwargs)
        elif view.request.method == 'OPTIONS':
            response = view.options(**kwargs)
        else:
            raise BadRequest()
        return response

    def options(self, **kwargs):
        return Response('')


class ServeTile(View):

    SQL_TEMPLATE = "SELECT {way}, * FROM ({sql}) AS data WHERE ST_IsValid(way) AND ST_Intersects(way, {bbox})"  # noqa
    GEOMETRY = "{way}"
    methods = ['GET']
    RADIUS = 6378137
    CIRCUM = 2 * math.pi * RADIUS
    SIZE = 256

    def get(self, names, z, x, y, recipe=None):
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


class ServePBF(ServeTile):

    endpoint = 'pbf'

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


class ServeJSON(ServeTile):

    endpoint = 'json'

    GEOMETRY = "ST_AsGeoJSON(ST_Transform({way}, 4326)) as _way"  # noqa
    CONTENT_TYPE = 'application/json'

    def post_process(self):
        self.content = json.dumps(self.layers)

    def process_geometry(self, geometry):
        return json.loads(geometry)


class ServeGeoJSON(ServeJSON):

    endpoint = 'geojson'

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


class TileJson(View):

    endpoint = 'tilejson'

    def get(self):
        base = config.TILEJSON
        base['vector_layers'] = []
        for recipe in RECIPES.values():
            for layer in recipe.layers.values():
                base['vector_layers'].append({
                    "description": layer.description,
                    "id": layer.id
                })
        return json.dumps(base)
