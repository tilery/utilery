import logging
import time

import psycopg2
import psycopg2.extras
import yaml
from pathlib import Path

from flask import Flask, g

from .models import Recipe

app = Flask(__name__)
app.config.from_object('utilery.default')
app.config.from_envvar('UTILERY_SETTINGS', silent=True)

logger = logging.getLogger(__name__)


if app.debug:
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = 'xxxxx'
    app.config['TESTING'] = True
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())


RECIPES = {}


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
        before = time.time()
        cur = DB.connect(dbname).cursor(
                                cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(query, args)
        rv = cur.fetchall()
        cur.close()
        after = time.time()
        logger.debug('%s => %s\n%s', query, (after - before) * 1000, '*' * 40)
        return rv


@app.teardown_appcontext
def close_connection(exception):
    c = getattr(g, '_connexions', None)
    if c is not None:
        for db in c.values():
            db.close()


def load_recipe(data):
    name = data.get('name', 'default')
    if name in RECIPES:
        raise ValueError('Recipe with name {} already exist'.format(name))
    RECIPES[name] = Recipe(data)
    if len(RECIPES) == 1 and name != 'default':
        RECIPES['default'] = RECIPES[data['name']]


with app.app_context():
    recipes = app.config['RECIPES']
    if isinstance(recipes, str):
        recipes = [recipes]
    for recipe in recipes:
        with Path(recipe).open() as f:
            load_recipe(yaml.load(f.read()))

# Import views to make Flask know about them
import utilery.views  # noqa
