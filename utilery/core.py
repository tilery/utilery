import asyncio
import atexit
import logging
import os
from pathlib import Path
import time
from urllib.parse import parse_qs

import asyncpg
import psycopg2.extras
import uvloop
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


class Request:

    EOF = False

    # HTTPRequestParser protocol methods
    def on_url(self, url: bytes):
        parsed = parse_url(url)
        self.path = parsed.path.decode()
        self.query_string = (parsed.query or b'').decode()
        self.query = parse_qs(self.query_string)

    def on_message_complete(self):
        self.EOF = True
        self.payload = {}


class Application:

    chunks = 2 ** 16
    requests_count = 0
    endpoints = {}

    async def startup(self):
        self.connections = {}
        self.pool = await asyncpg.create_pool(database='utilery', user='ybon')

    async def shutdown(self):
        pass

    async def finish_connections(self, timeout=None):
        coros = [conn.shutdown(timeout) for conn in self.connections]
        await asyncio.gather(*coros, loop=self.loop)
        self.connections.clear()

    async def __call__(self, reader, writer):
        req = Request()
        parser = HttpRequestParser(req)
        while True:
            data = await reader.read(self.chunks)
            parser.feed_data(data)
            if not data or req.EOF:
                break
        kwargs, handler = self.dispatch(req)
        self._write(writer, *await handler()(req, **kwargs))
        print("Served request…", req.path)

    def serve(self, port=3579, host='0.0.0.0'):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.startup())
        print('Serving on %s:%d' % (host, port))
        loop.create_task(asyncio.start_server(self, host, port))
        loop.run_forever()
        loop.close()

    def _write(self, writer, body, status, headers):
        writer.write(b'HTTP/1.1 200 OK\r\n')
        # if 'Content-Length' not in res.headers:
        #     length = sum(len(x) for x in res._chunks)
        #     res.headers['Content-Length'] = str(length)
        # for key, value in res.headers.items():
        #     writer.write(key.encode() + b': ' + str(value).encode() + b'\r\n')
        # for key, value in res.cookies.items():
        #     write_cookie(writer, key, value)
        writer.write(b'\r\n')
        if not isinstance(body, bytes):
            body = body.encode()
        writer.write(body)
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
        req.kwargs = {}
        try:
            path, ext, handler = self.endpoints[fragments_len][ext]
        except:
            raise ValueError  # TODO custom error
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
    def connect(cls, dbname=None):
        dbname = dbname or cls.DEFAULT
        if dbname not in cls._:
            cls._[dbname] = psycopg2.connect(config.DATABASES[dbname])
        return cls._[dbname]

    @classmethod
    async def fetchall(cls, query, args=None, dbname=None):
        # Take a connection from the pool.
        async with application.pool.acquire() as connection:
            # Open a transaction.
            async with connection.transaction():
                before = time.time()
                rv = await connection.fetch(query)
                after = time.time()
        logger.debug('%s => %s\n%s', query, (after - before) * 1000, '*' * 40)
        return rv


def close_connections():
    logger.debug('Closing DB connections')
    for conn in DB._.values():
        conn.close()
atexit.register(close_connections)


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
