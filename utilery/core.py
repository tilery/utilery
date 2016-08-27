import asyncio
import logging
import os
from pathlib import Path
import time
from urllib.parse import parse_qs

import asyncpg
import psycopg2.extras
import yaml
from httptools import parse_url, HttpRequestParser

from . import config
from .plugins import Plugins
from .models import Recipe

logger = logging.getLogger(__name__)


if config.DEBUG:
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())


RECIPES = {}
STATUSES = {
    200: b'200 OK',
    301: b'301 Moved Permanently',
    302: b'302 Found',
    304: b'304 Not Modified',
    400: b'400 Bad Request',
    404: b'404 Not Found',
    405: b'405 Method Not Allowed',
    500: b'500 Internal Server Error',
}


class HttpError(Exception):
    ...


class Request:

    __slots__ = (
        'EOF',
        'path',
        'query_string',
        'query',
        'method',
        'kwargs',
    )

    def __init__(self):
        self.EOF = False
        self.kwargs = {}

    def on_url(self, url: bytes):
        parsed = parse_url(url)
        self.path = parsed.path.decode()
        self.query_string = (parsed.query or b'').decode()
        self.query = parse_qs(self.query_string)

    def on_message_complete(self):
        self.EOF = True


class Response:

    __slots__ = (
        '_status',
        'headers',
        'body',
    )

    def __init__(self, body=b'', status=200, headers=None):
        self._status = None
        self.body = body
        self.status = status
        self.headers = headers or {}

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, code):
        self._status = STATUSES[code]


class Application:

    requests_count = 0  # Needed by Gunicorn worker.
    endpoints = {}

    async def startup(self):
        self.connections = {}  # Used by Gunicorn worker.
        await DB.startup()

    async def shutdown(self):
        pass

    async def __call__(self, reader, writer):
        chunks = 2 ** 16
        req = Request()
        parser = HttpRequestParser(req)
        while True:
            data = await reader.read(chunks)
            parser.feed_data(data)
            if not data or req.EOF:
                break
        req.method = parser.get_method().decode().upper()
        resp = await self.respond(req)
        self.write(writer, resp)
        print("Served request…", req.method, req.path)

    async def respond(self, req):
        resp = Plugins.hook('request', request=req)
        if not resp:
            if req.method == 'GET':
                try:
                    # Both can return an HttpError.
                    kwargs, handler = self.dispatch(req)
                    resp = await handler()(req, **kwargs)
                except HttpError as e:
                    resp = e.args[::-1]  # Allow to raise HttpError(status)
            elif req.method == 'OPTIONS':
                resp = b'', 200
            else:
                resp = b'', 405
            resp = Response(*resp)
        resp = Plugins.hook('response', response=resp, request=req) or resp
        if not isinstance(resp, Response):
            resp = Response(*resp)
        return resp

    def serve(self, port=3579, host='0.0.0.0'):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.startup())
        print('Serving on %s:%d' % (host, port))
        loop.create_task(asyncio.start_server(self, host, port))
        loop.run_forever()
        loop.close()

    def write(self, writer, resp):
        writer.write(b'HTTP/1.1 %b\r\n' % resp.status)
        if not isinstance(resp.body, bytes):
            resp.body = resp.body.encode()
        if 'Content-Length' not in resp.headers:
            length = len(resp.body)
            resp.headers['Content-Length'] = str(length)
        for key, value in resp.headers.items():
            writer.write(b'%b: %b\r\n' % (key.encode(), str(value).encode()))
        writer.write(b'\r\n')
        writer.write(resp.body)
        writer.write_eof()

    def register_handler(self, handler):
        for endpoint in handler.endpoints:
            self.register_endpoint(endpoint, handler)

    def register_endpoint(self, endpoint, handler):
        path, ext = os.path.splitext(endpoint)
        fragments = path.split('/')
        fragments_len = len(fragments)
        self.endpoints.setdefault(fragments_len, {})
        self.endpoints[fragments_len].setdefault(ext, [])
        self.endpoints[fragments_len][ext] = path, ext, handler

    def dispatch(self, req):
        path, ext = os.path.splitext(req.path)
        fragments = path.split('/')
        fragments_len = len(fragments)
        try:
            path, ext, handler = self.endpoints[fragments_len][ext]
        except:
            raise HttpError(404, req.path)
        else:
            for name, value in zip(path.split('/'), fragments):
                if name.startswith('{'):
                    req.kwargs[name[1:-1]] = value
            return req.kwargs, handler


application = Application()


class HandlerBase(type):

    def __new__(mcs, name, bases, attrs, **kwargs):
        cls = super().__new__(mcs, name, bases, attrs)
        if hasattr(cls, 'endpoints'):
            application.register_handler(cls)
        return cls


class Handler(metaclass=HandlerBase):
    ...


class DB(object):

    DEFAULT = "default"
    _ = {}

    @classmethod
    async def startup(cls):
        for name, kwargs in config.DATABASES.items():
            cls._[name] = await asyncpg.create_pool(**kwargs)

    @classmethod
    async def fetchall(cls, query, args=None, dbname=None):
        dbname = dbname or cls.DEFAULT  # Be sure not to use an empty string.
        async with cls._[dbname].acquire() as connection:
            # Open a transaction.
            async with connection.transaction():
                before = time.time()
                rv = await connection.fetch(query)
                after = time.time()
        logger.debug('%s => %s\n%s', query, (after - before) * 1000, '*' * 40)
        return rv


Plugins.load()
Plugins.hook('before_load', config=config)


def load_recipe(data):
    name = data.get('name', 'default')
    if name in RECIPES:
        raise ValueError('Recipe with name {} already exist'.format(name))
    data['name'] = name
    RECIPES[name] = Recipe(data)
    if len(RECIPES) == 1 and name != 'default':
        RECIPES['default'] = RECIPES[data['name']]


recipes = config.RECIPES
if isinstance(recipes, str):
    recipes = [recipes]
for recipe in recipes:
    with Path(recipe).open() as f:
        load_recipe(yaml.load(f.read()))

Plugins.hook('load', config=config, recipes=RECIPES)
