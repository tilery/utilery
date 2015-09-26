import atexit
import logging
import time

import psycopg2
import psycopg2.extras
import yaml
from pathlib import Path

from .models import Recipe
from . import config

logger = logging.getLogger(__name__)


if config.DEBUG:
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())


RECIPES = {}


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


def close_connections():
    logger.debug('Closing DB connections')
    for conn in DB._.values():
        conn.close()
atexit.register(close_connections)


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
