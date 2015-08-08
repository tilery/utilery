# -*- coding: utf-8 -*-

import psycopg2
import psycopg2.extras
import yaml
# from pathlib import Path

from flask import Flask, g, _app_ctx_stack as stack

app = Flask(__name__)
app.config.from_object('mezzatile.default')
app.config.from_envvar('MEZZATILE_SETTINGS', silent=True)

if app.debug:
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = 'xxxxx'
    app.config['TESTING'] = True


class DB(object):

    @classmethod
    def connect(cls):
        db = getattr(g, '_database', None)
        if db is None:
            db = g._database = psycopg2.connect(app.config['DATABASE'])
        return db

    @classmethod
    def fetchall(cls, query, args=None):
        cur = DB.connect().cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(query, args)
        rv = cur.fetchall()
        cur.close()
        return rv


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


with open('example.yml') as f:
    LAYERS = yaml.load(f.read())


# Import views to make Flask know about them
import mezzatile.views  # noqa
