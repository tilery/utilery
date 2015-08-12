# -*- coding: utf-8 -*-

import psycopg2
import psycopg2.extras
import yaml
# from pathlib import Path

from flask import Flask, g

app = Flask(__name__)
app.config.from_object('utilery.default')
app.config.from_envvar('UTILERY_SETTINGS', silent=True)

if app.debug:
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = 'xxxxx'
    app.config['TESTING'] = True


LAYERS = {}


class DB(object):

    DEFAULT = "default"

    @classmethod
    def connect(cls, dbname=None):
        db = getattr(g, '_connexions', None)
        if db is None:
            db = g._connexions = {}
        dbname = dbname or cls.DEFAULT
        if dbname not in db:
            db[dbname] = psycopg2.connect(app.config['DATABASES'][dbname])
        return db[dbname]

    @classmethod
    def fetchall(cls, query, args=None, dbname=None):
        cur = DB.connect(dbname).cursor(
                                cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(query, args)
        rv = cur.fetchall()
        cur.close()
        return rv


@app.teardown_appcontext
def close_connection(exception):
    c = getattr(g, '_connexions', None)
    if c is not None:
        for db in c.values():
            db.close()


def load_source(source):
    metadata = dict(source)
    del metadata['layers']  # Avoid recursion.
    for original in source['layers']:
        layer = metadata  # Add source values as default to layer.
        layer.update(original)
        LAYERS[layer['name']] = dict(layer)


with app.app_context():
    sources = app.config['LAYERS_SOURCES']
    if isinstance(sources, basestring):
        sources = [sources]
    for path in sources:
        with open(path) as f:
            load_source(yaml.load(f.read()))

# Import views to make Flask know about them
import utilery.views  # noqa
