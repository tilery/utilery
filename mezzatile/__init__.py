# -*- coding: utf-8 -*-

import psycopg2
import psycopg2.extras
import yaml
# from pathlib import Path

from flask import Flask, g

app = Flask(__name__)
app.config.from_object('mezzatile.default')
app.config.from_envvar('MEZZATILE_SETTINGS', silent=True)

if app.debug:
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = 'xxxxx'
    app.config['TESTING'] = True


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


with open('example.yml') as f:
    LAYERS = yaml.load(f.read())


# Import views to make Flask know about them
import mezzatile.views  # noqa
