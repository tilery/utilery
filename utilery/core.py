import logging
import time
from http import HTTPStatus
from pathlib import Path

import asyncpg
import yaml
from roll import Roll
from roll.extensions import cors, traceback

from . import config

logger = logging.getLogger(__name__)


if config.DEBUG:
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())


RECIPES = {}


app = application = Roll()
traceback(app)


class DB:

    DEFAULT = "default"
    _ = {}

    @classmethod
    async def startup(cls):
        for name, kwargs in config.DATABASES.items():
            cls._[name] = await asyncpg.create_pool(**kwargs)

    @classmethod
    async def shutdown(cls):
        for pool in cls._.values():
            await pool.close()

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


@app.listen('startup')
async def startup():
    if config.CORS:
        cors(app, value=config.CORS)
    if config.MAX_AGE:
        cache(app, max_age=config.MAX_AGE)
    await DB.startup()
    await application.hook('before_load', config=config)
    recipes = config.RECIPES
    if isinstance(recipes, str):
        recipes = [recipes]
    for recipe in recipes:
        with Path(recipe).open() as f:
            load_recipe(yaml.load(f.read()))
    await application.hook('load', config=config, recipes=RECIPES)


@app.listen('shutdown')
async def shutdown():
    await DB.shutdown()


def cache(app, max_age=3600):

    @app.listen('response')
    async def add_cors_headers(response, request):
        if response.status == HTTPStatus.OK:
            response.headers['Cache-Control'] = \
                'public,max-age={}'.format(max_age)


def load_recipe(data):
    from .models import Recipe
    name = data.get('name', 'default')
    if name in RECIPES:
        raise ValueError('Recipe with name {} already exist'.format(name))
    data['name'] = name
    RECIPES[name] = Recipe(data)
    if len(RECIPES) == 1 and name != 'default':
        RECIPES['default'] = RECIPES[data['name']]
